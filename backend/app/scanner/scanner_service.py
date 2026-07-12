"""
Scanner Service - Core Image Processing Engine
Handles answer sheet scanning, bubble detection, and answer recognition using OpenCV
"""
import cv2
import numpy as np
import logging
import base64
import io
import time
import qrcode
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from PIL import Image

from app.config import settings
from app.schemas import QuestionResult, ScanStatus, QRCodeData

logger = logging.getLogger(__name__)


@dataclass
class BubbleInfo:
    """Information about a detected bubble"""
    x: int
    y: int
    w: int
    h: int
    center_x: int
    center_y: int
    area: float
    filled_ratio: float
    question_num: int
    option: str


@dataclass
class ScanResult:
    """Result of scanning an answer sheet"""
    student_id: Optional[str] = None
    exam_id: Optional[str] = None
    sheet_id: Optional[str] = None
    class_id: Optional[str] = None
    teacher_id: Optional[str] = None
    question_results: List[QuestionResult] = field(default_factory=list)
    total_questions: int = 0
    correct_count: int = 0
    wrong_count: int = 0
    blank_count: int = 0
    multiple_marks_count: int = 0
    percentage: float = 0.0
    passed: bool = False
    scan_confidence: float = 1.0
    processing_time_ms: int = 0
    status: ScanStatus = ScanStatus.COMPLETED
    error_message: Optional[str] = None
    image_url: Optional[str] = None


class AnswerSheetScanner:
    """Main scanner class for processing answer sheets"""

    def __init__(self):
        self.confidence_threshold = settings.scanner_confidence_threshold
        self.bubble_min_area = settings.scanner_bubble_min_area
        self.bubble_max_area = settings.scanner_bubble_max_area
        self.perspective_width = settings.scanner_perspective_width
        self.perspective_height = settings.scanner_perspective_height

    def process_image(
        self,
        image_data: bytes,
        answer_key: List[str],
        num_questions: int,
        passing_score: float = 60.0,
        options_per_question: int = 4
    ) -> ScanResult:
        """
        Process an answer sheet image and return results

        Args:
            image_data: Raw image bytes
            answer_key: List of correct answers (e.g., ['A', 'B', 'C', 'D'])
            num_questions: Total number of questions
            passing_score: Minimum percentage to pass
            options_per_question: Number of options per question (4 or 5)

        Returns:
            ScanResult with all grading information
        """
        start_time = time.time()

        try:
            # Decode image
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return self._create_error_result("Failed to decode image", start_time)

            # Step 1: Detect and correct perspective
            warped = self._detect_and_warp_paper(image)
            if warped is None:
                return self._create_error_result("Could not detect answer sheet paper", start_time)

            # Step 2: Decode QR code
            qr_data = self._decode_qr_code(warped)

            # Step 3: Detect bubbles
            bubbles = self._detect_bubbles(warped, num_questions, options_per_question)
            if not bubbles:
                return self._create_error_result("Could not detect answer bubbles", start_time)

            # Step 4: Grade answers with warped image for accurate fill detection
            question_results = self._grade_answers(bubbles, answer_key, num_questions, options_per_question, warped)

            # Step 5: Calculate scores
            correct = sum(1 for q in question_results if q.is_correct)
            wrong = sum(1 for q in question_results if not q.is_correct and not q.is_blank)
            blank = sum(1 for q in question_results if q.is_blank)
            multiple = sum(1 for q in question_results if q.has_multiple_marks)

            percentage = round((correct / num_questions) * 100, 2) if num_questions > 0 else 0
            passed = percentage >= passing_score

            # Calculate overall confidence
            confidences = [q.confidence for q in question_results if q.confidence > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 1.0

            processing_time = int((time.time() - start_time) * 1000)

            return ScanResult(
                student_id=qr_data.student_id if qr_data else None,
                exam_id=qr_data.exam_id if qr_data else None,
                sheet_id=qr_data.sheet_id if qr_data else None,
                class_id=qr_data.class_id if qr_data else None,
                teacher_id=qr_data.teacher_id if qr_data else None,
                question_results=question_results,
                total_questions=num_questions,
                correct_count=correct,
                wrong_count=wrong,
                blank_count=blank,
                multiple_marks_count=multiple,
                percentage=percentage,
                passed=passed,
                scan_confidence=avg_confidence,
                processing_time_ms=processing_time,
                status=ScanStatus.COMPLETED if avg_confidence >= self.confidence_threshold else ScanStatus.MANUAL_REVIEW
            )

        except Exception as e:
            logger.error(f"Scanning error: {e}", exc_info=True)
            return self._create_error_result(f"Scanning failed: {str(e)}", start_time)

    def _detect_and_warp_paper(self, image: np.ndarray) -> Optional[np.ndarray]:
        """Detect anchor markers and apply precise perspective transform.
        Falls back to paper edge detection if anchors not found."""
        warped = self._warp_by_anchors(image)
        if warped is not None:
            return warped
        return self._warp_by_paper_edge(image)

    def _warp_by_anchors(self, image: np.ndarray) -> Optional[np.ndarray]:
        """Detect 3 filled + 1 hollow square anchors and warp to canonical size."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        img_area = image.shape[0] * image.shape[1]
        candidates = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Anchors are small squares: filter by relative area
            if img_area * 0.0001 < area < img_area * 0.005:
                peri = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
                if len(approx) == 4:
                    x, y, w, h = cv2.boundingRect(approx)
                    aspect = w / h if h > 0 else 0
                    if 0.6 < aspect < 1.6:
                        cx, cy = x + w // 2, y + h // 2
                        candidates.append((cx, cy, area))

        if len(candidates) < 4:
            return None

        # Pick 4 candidates closest to the 4 corners
        h_img, w_img = image.shape[:2]
        corners = [
            (0, 0),           # TL
            (w_img, 0),       # TR
            (0, h_img),       # BL
            (w_img, h_img),   # BR
        ]
        chosen = []
        used = set()
        for cx_ref, cy_ref in corners:
            best = min(
                (i for i in range(len(candidates)) if i not in used),
                key=lambda i: (candidates[i][0] - cx_ref) ** 2 + (candidates[i][1] - cy_ref) ** 2
            )
            chosen.append(candidates[best][:2])
            used.add(best)

        if len(chosen) != 4:
            return None

        src = np.array(chosen, dtype="float32")  # TL, TR, BL, BR
        # Reorder to TL, TR, BR, BL for getPerspectiveTransform
        tl, tr, bl, br = src[0], src[1], src[2], src[3]
        src_ordered = np.array([tl, tr, br, bl], dtype="float32")
        dst = np.array([
            [0, 0],
            [self.perspective_width - 1, 0],
            [self.perspective_width - 1, self.perspective_height - 1],
            [0, self.perspective_height - 1],
        ], dtype="float32")

        M = cv2.getPerspectiveTransform(src_ordered, dst)
        return cv2.warpPerspective(image, M, (self.perspective_width, self.perspective_height))

    def _warp_by_paper_edge(self, image: np.ndarray) -> Optional[np.ndarray]:
        """Fallback: detect paper outline and warp."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)
        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

        paper_contour = None
        for contour in contours:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            if len(approx) == 4:
                area = cv2.contourArea(approx)
                img_area = image.shape[0] * image.shape[1]
                if area > img_area * 0.1:
                    paper_contour = approx
                    break

        if paper_contour is None:
            return None

        pts = paper_contour.reshape(4, 2)
        rect = self._order_points(pts)
        dst = np.array([
            [0, 0],
            [self.perspective_width - 1, 0],
            [self.perspective_width - 1, self.perspective_height - 1],
            [0, self.perspective_height - 1]
        ], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(image, M, (self.perspective_width, self.perspective_height))

    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """Order points: top-left, top-right, bottom-right, bottom-left"""
        rect = np.zeros((4, 2), dtype="float32")

        # Sum of coordinates - top-left has smallest sum, bottom-right largest
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        # Difference - top-right has smallest diff, bottom-left largest
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        return rect

    def _decode_qr_code(self, image: np.ndarray) -> Optional[QRCodeData]:
        """Decode QR code — crops top-right region first for speed, falls back to full image."""
        h, w = image.shape[:2]
        qr_detector = cv2.QRCodeDetector()

        # Fast path: scan only the top-right corner where QR is placed
        crop_x = int(w * 0.6)
        crop = image[0:int(h * 0.35), crop_x:w]
        try:
            data, bbox, _ = qr_detector.detectAndDecode(crop)
            if data:
                return self._parse_qr_data(data)
        except Exception:
            pass

        # Fallback: scan the full page
        try:
            data, bbox, _ = qr_detector.detectAndDecode(image)
            if data:
                return self._parse_qr_data(data)
        except Exception as e:
            logger.warning(f"QR code detection failed: {e}")

        return None


    def _parse_qr_data(self, data: str) -> Optional[QRCodeData]:
        """Parse QR code JSON data"""
        try:
            import json
            parsed = json.loads(data)
            return QRCodeData(
                student_id=parsed.get('student_id', ''),
                exam_id=parsed.get('exam_id', ''),
                sheet_id=parsed.get('sheet_id', ''),
                class_id=parsed.get('class_id', ''),
                teacher_id=parsed.get('teacher_id', ''),
                version=parsed.get('version', '1')
            )
        except Exception as e:
            logger.warning(f"Failed to parse QR data: {e}")
            return None

    def _detect_bubbles(
        self,
        image: np.ndarray,
        num_questions: int,
        options_per_question: int
    ) -> List[List[BubbleInfo]]:
        """
        Detect answer bubbles in the warped image
        Returns list of lists: questions x options
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Adaptive threshold for bubble detection
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )

        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter contours by area and circularity
        bubbles = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.bubble_min_area < area < self.bubble_max_area:
                # Check circularity
                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                    if circularity > 0.5:  # Reasonably circular
                        x, y, w, h = cv2.boundingRect(contour)
                        # Aspect ratio should be close to 1
                        aspect_ratio = w / h if h > 0 else 0
                        if 0.7 < aspect_ratio < 1.3:
                            bubbles.append({
                                'contour': contour,
                                'x': x, 'y': y, 'w': w, 'h': h,
                                'center_x': x + w // 2,
                                'center_y': y + h // 2,
                                'area': area
                            })

        # Sort bubbles by position (top to bottom, left to right)
        bubbles.sort(key=lambda b: (b['center_y'], b['center_x']))

        # Organize into grid: questions x options
        return self._organize_bubbles_into_grid(bubbles, num_questions, options_per_question)

    def _organize_bubbles_into_grid(
        self,
        bubbles: List[Dict],
        num_questions: int,
        options_per_question: int
    ) -> List[List[BubbleInfo]]:
        """Organize detected bubbles into question-option grid"""
        if not bubbles:
            return []

        # Group bubbles by row (question)
        # Use y-coordinate clustering
        rows = []
        current_row = [bubbles[0]]
        y_threshold = 30  # pixels

        for bubble in bubbles[1:]:
            if abs(bubble['center_y'] - current_row[-1]['center_y']) < y_threshold:
                current_row.append(bubble)
            else:
                rows.append(current_row)
                current_row = [bubble]
        rows.append(current_row)

        # Sort each row by x-coordinate
        for row in rows:
            row.sort(key=lambda b: b['center_x'])

        # Take only the first options_per_question bubbles per row
        # And only first num_questions rows
        grid = []
        for i, row in enumerate(rows[:num_questions]):
            question_bubbles = []
            for j, bubble in enumerate(row[:options_per_question]):
                option_char = chr(ord('A') + j)
                question_bubbles.append(BubbleInfo(
                    x=bubble['x'],
                    y=bubble['y'],
                    w=bubble['w'],
                    h=bubble['h'],
                    center_x=bubble['center_x'],
                    center_y=bubble['center_y'],
                    area=bubble['area'],
                    filled_ratio=0.0,  # Will be calculated later
                    question_num=i + 1,
                    option=option_char
                ))
            # Pad if fewer options detected
            while len(question_bubbles) < options_per_question:
                option_char = chr(ord('A') + len(question_bubbles))
                question_bubbles.append(BubbleInfo(
                    x=0, y=0, w=0, h=0,
                    center_x=0, center_y=0,
                    area=0, filled_ratio=0.0,
                    question_num=i + 1, option=option_char
                ))
            grid.append(question_bubbles)

        # Pad rows if fewer questions detected
        while len(grid) < num_questions:
            question_bubbles = []
            for j in range(options_per_question):
                option_char = chr(ord('A') + j)
                question_bubbles.append(BubbleInfo(
                    x=0, y=0, w=0, h=0,
                    center_x=0, center_y=0,
                    area=0, filled_ratio=0.0,
                    question_num=len(grid) + 1, option=option_char
                ))
            grid.append(question_bubbles)

        return grid

    def _grade_answers(
        self,
        bubble_grid: List[List[BubbleInfo]],
        answer_key: List[str],
        num_questions: int,
        options_per_question: int,
        warped_image: Optional[np.ndarray] = None
    ) -> List[QuestionResult]:
        """Grade answers by analyzing bubble fill levels against answer key"""
        results = []

        for q_idx in range(min(num_questions, len(bubble_grid))):
            question_bubbles = bubble_grid[q_idx]
            correct_answer = answer_key[q_idx] if q_idx < len(answer_key) else 'A'

            filled_bubbles = []
            for bubble in question_bubbles:
                if bubble.area > 0:
                    filled_ratio = self._calculate_fill_ratio(bubble, warped_image)
                    bubble.filled_ratio = filled_ratio
                    if filled_ratio > 0.3:
                        filled_bubbles.append(bubble)

            # Determine student answer
            if len(filled_bubbles) == 1:
                student_answer = filled_bubbles[0].option
                has_multiple = False
                confidence = filled_bubbles[0].filled_ratio
            elif len(filled_bubbles) > 1:
                student_answer = filled_bubbles[0].option  # First one
                has_multiple = True
                confidence = max(b.filled_ratio for b in filled_bubbles)
            else:
                student_answer = None
                has_multiple = False
                confidence = 0.0

            is_correct = student_answer == correct_answer
            is_blank = student_answer is None

            results.append(QuestionResult(
                question_number=q_idx + 1,
                student_answer=student_answer,
                correct_answer=correct_answer,
                is_correct=is_correct,
                is_blank=is_blank,
                has_multiple_marks=has_multiple,
                confidence=confidence
            ))

        return results

    def _calculate_fill_ratio(self, bubble: BubbleInfo, image: Optional[np.ndarray] = None) -> float:
        """Calculate how filled a bubble is using actual pixel analysis when image is available"""
        if image is not None and bubble.w > 0 and bubble.h > 0:
            try:
                # Extract bubble region with small padding
                pad = 2
                y1 = max(0, bubble.y + pad)
                y2 = min(image.shape[0], bubble.y + bubble.h - pad)
                x1 = max(0, bubble.x + pad)
                x2 = min(image.shape[1], bubble.x + bubble.w - pad)
                if y2 > y1 and x2 > x1:
                    roi = image[y1:y2, x1:x2]
                    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
                    # Dark pixels (filled) have low values after threshold
                    _, thresh = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                    fill_ratio = np.sum(thresh > 0) / thresh.size
                    return float(fill_ratio)
            except Exception:
                pass
        # Fallback: area-based estimate
        if bubble.area > 0:
            return min(bubble.area / self.bubble_max_area, 1.0)
        return 0.0

    def _create_error_result(self, error_msg: str, start_time: float) -> ScanResult:
        """Create error result"""
        return ScanResult(
            status=ScanStatus.FAILED,
            error_message=error_msg,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )


class AnswerSheetGenerator:
    """Generate printable answer sheets with QR codes"""

    def __init__(self):
        self.page_width = 2480  # A4 at 300 DPI
        self.page_height = 3508
        self.margin = 100

    def generate_answer_sheet(
        self,
        exam_title: str,
        student_name: str,
        student_id: str,
        qr_data: QRCodeData,
        num_questions: int,
        options_per_question: int = 4,
        school_name: str = "School Name",
        school_logo: Optional[bytes] = None,
        paper_size: str = "A4"
    ) -> bytes:
        """
        Generate a printable answer sheet as PDF bytes
        """
        from reportlab.lib.pagesizes import A4, LEGAL, LETTER
        from reportlab.lib.units import mm, cm
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        import io

        # Page size
        if paper_size == "A4":
            pagesize = A4
        elif paper_size == "Legal":
            pagesize = LEGAL    
        else:
            pagesize = LETTER

        width, height = pagesize
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=pagesize)

        # Draw header
        self._draw_header(c, width, height, school_name, school_logo, exam_title, student_name, student_id)

        # Draw QR code
        self._draw_qr_code(c, width, height, qr_data)

        # Draw bubbles
        self._draw_bubbles(c, width, height, num_questions, options_per_question)

        # Draw footer
        self._draw_footer(c, width, height, qr_data.sheet_id)

        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    def _draw_header(self, c, width, height, school_name, logo, exam_title, student_name, student_id):
        """Draw answer sheet header"""
        # Reserve right side for QR code (100pt wide + margins)
        qr_size = 100
        qr_margin = 50
        text_right_bound = width - qr_size - qr_margin - 10

        y = height - 50

        # School name
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(text_right_bound / 2, y, school_name or "School Name")
        y -= 30

        # Exam title
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(text_right_bound / 2, y, exam_title)
        y -= 25

        # Student info
        c.setFont("Helvetica", 11)
        c.drawString(50, y, f"Student: {student_name}")
        y -= 18
        c.drawString(50, y, f"ID: {student_id}")
        y -= 20

        # Instructions
        c.setFont("Helvetica", 9)
        c.drawString(50, y, "Fill bubbles completely • Use black/blue pen • Erase changes completely")

        # Separator line
        y -= 15
        c.line(50, y, width - 50, y)

    def _draw_qr_code(self, c, width, height, qr_data: QRCodeData):
        """Draw QR code on sheet"""
        import qrcode as qrcode_lib
        import io
        from reportlab.lib.utils import ImageReader

        qr = qrcode_lib.QRCode(version=1, box_size=5, border=2)
        qr.add_data(qr_data.model_dump_json())
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, 'PNG')
        buffer.seek(0)

        qr_size = 100
        qr_margin = 50
        x = width - qr_size - qr_margin
        y = height - qr_size - 40
        c.drawImage(ImageReader(buffer), x, y, qr_size, qr_size)

    # Anchor marker size in points — must match ANCHOR_SIZE in scanner
    ANCHOR_SIZE = 20
    ANCHOR_MARGIN = 20

    def _draw_anchors(self, c, width, height):
        """Draw 3 filled square anchors (TL, TR, BL) + hollow orientation marker (BR)"""
        s = self.ANCHOR_SIZE
        m = self.ANCHOR_MARGIN
        # Top-left, Top-right, Bottom-left: filled black squares
        for x, y in [
            (m, height - m - s),
            (width - m - s, height - m - s),
            (m, m),
        ]:
            c.setFillColorRGB(0, 0, 0)
            c.rect(x, y, s, s, fill=1, stroke=0)
        # Bottom-right: hollow square (orientation marker)
        c.setFillColorRGB(1, 1, 1)
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(2)
        c.rect(width - m - s, m, s, s, fill=1, stroke=1)
        c.setLineWidth(1)
        c.setFillColorRGB(0, 0, 0)

    def _draw_bubbles(self, c, width, height, num_questions, options_per_question):
        """Draw answer bubbles"""
        self._draw_anchors(c, width, height)

        start_y = height - 200
        bubble_radius = 4
        bubble_spacing = 18
        question_spacing = 22
        left_margin = 80
        options_labels = ['A', 'B', 'C', 'D', 'E'][:options_per_question]

        questions_per_column = 25
        num_columns = (num_questions + questions_per_column - 1) // questions_per_column
        column_width = (width - 160) / num_columns

        for col in range(num_columns):
            col_start = left_margin + col * column_width
            col_questions = min(questions_per_column, num_questions - col * questions_per_column)

            for q in range(col_questions):
                q_num = col * questions_per_column + q + 1
                y = start_y - q * question_spacing

                c.setFont("Helvetica", 8)
                c.drawRightString(col_start - 5, y + 2, f"{q_num:2d}.")

                for opt_idx, opt in enumerate(options_labels):
                    x = col_start + opt_idx * bubble_spacing
                    c.circle(x, y, bubble_radius, fill=0, stroke=1)
                    c.setFont("Helvetica", 6)
                    c.drawCentredString(x, y - 12, opt)

    def _draw_footer(self, c, width, height, sheet_id):
        """Draw footer with sheet ID"""
        c.setFont("Helvetica", 8)
        c.drawCentredString(width / 2, 30, f"Sheet ID: {sheet_id} | AI Exam Checker")


# Global scanner instance
scanner = AnswerSheetScanner()
generator = AnswerSheetGenerator()