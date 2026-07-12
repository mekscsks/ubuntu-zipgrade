/**
 * API Client - Centralized HTTP client for backend communication
 */

const API_BASE = window.APP_CONFIG?.apiBase || 'https://ai-exam-checker-production.up.railway.app/api/v1';

class ApiClient {
  constructor() {
    this._token = localStorage.getItem('auth_token');
  }

  setToken(token) {
    this._token = token;
    if (token) localStorage.setItem('auth_token', token);
    else localStorage.removeItem('auth_token');
  }

  getToken() { return this._token; }

  _headers(extra = {}) {
    const h = { 'Content-Type': 'application/json', ...extra };
    if (this._token) h['Authorization'] = `Bearer ${this._token}`;
    return h;
  }

  async _request(method, path, body = null, isFormData = false) {
    const opts = { method, headers: isFormData ? { Authorization: `Bearer ${this._token}` } : this._headers() };
    if (body) opts.body = isFormData ? body : JSON.stringify(body);

    try {
      const res = await fetch(`${API_BASE}${path}`, opts);

      if (res.status === 401) {
        this.setToken(null);
        window.location.href = '/pages/login.html';
        return null;
      }

      const contentType = res.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || data.error || 'Request failed');
        return data;
      }

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res; // Return raw response for file downloads
    } catch (err) {
      if (err.name === 'TypeError') throw new Error('Network error - check your connection');
      throw err;
    }
  }

  get(path) { return this._request('GET', path); }
  post(path, body) { return this._request('POST', path, body); }
  put(path, body) { return this._request('PUT', path, body); }
  delete(path) { return this._request('DELETE', path); }
  upload(path, formData) { return this._request('POST', path, formData, true); }

  async download(path, filename) {
    const res = await this._request('GET', path);
    if (!res) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }
}

export const api = new ApiClient();

// Auth endpoints
export const authApi = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  register: (data) => api.post('/auth/register', data),
  verifyToken: (idToken) => api.post(`/auth/verify-token?id_token=${encodeURIComponent(idToken)}`),
  registerWithToken: (idToken, displayName, schoolName) => api.post(`/auth/register-with-token?id_token=${encodeURIComponent(idToken)}&display_name=${encodeURIComponent(displayName || '')}&school_name=${encodeURIComponent(schoolName || '')}`),
  me: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout'),
  forgotPassword: (email) => api.post('/auth/forgot-password', { email }),
  changePassword: (current, next) => api.post('/auth/change-password', { current_password: current, new_password: next }),
};

// Dashboard
export const dashboardApi = {
  stats: () => api.get('/dashboard/stats'),
  scoreDistribution: (examId, days) => api.get(`/dashboard/charts/score-distribution${examId ? `?exam_id=${examId}` : ''}${days ? `&days=${days}` : ''}`),
  scoreTrend: (days) => api.get(`/dashboard/charts/score-trend?days=${days || 30}`),
  passingRate: (days) => api.get(`/dashboard/charts/passing-rate?days=${days || 30}`),
  classPerformance: () => api.get('/dashboard/charts/class-performance'),
  subjectPerformance: () => api.get('/dashboard/charts/subject-performance'),
};

// Subjects
export const subjectsApi = {
  list: (page = 1, search = '') => api.get(`/subjects?page=${page}&search=${encodeURIComponent(search)}`),
  get: (id) => api.get(`/subjects/${id}`),
  create: (data) => api.post('/subjects', data),
  update: (id, data) => api.put(`/subjects/${id}`, data),
  delete: (id) => api.delete(`/subjects/${id}`),
};

// Classes
export const classesApi = {
  list: (page = 1, search = '', subjectId = '') => api.get(`/classes?page=${page}&search=${encodeURIComponent(search)}${subjectId ? `&subject_id=${subjectId}` : ''}`),
  get: (id) => api.get(`/classes/${id}`),
  create: (data) => api.post('/classes', data),
  update: (id, data) => api.put(`/classes/${id}`, data),
  delete: (id) => api.delete(`/classes/${id}`),
  students: (id, page = 1, search = '') => api.get(`/classes/${id}/students?page=${page}&search=${encodeURIComponent(search)}`),
  importStudents: (id, file) => { const fd = new FormData(); fd.append('file', file); return api.upload(`/students/import?class_id=${id}`, fd); },
  exportStudents: (id) => api.download(`/students/export/excel?class_id=${id}`, `students_${id}.xlsx`),
};

// Students
export const studentsApi = {
  list: (classId = '', page = 1, search = '') => api.get(`/students?${classId ? `class_id=${classId}&` : ''}page=${page}&search=${encodeURIComponent(search)}`),
  get: (id) => api.get(`/students/${id}`),
  create: (data) => api.post('/students', data),
  update: (id, data) => api.put(`/students/${id}`, data),
  delete: (id) => api.delete(`/students/${id}`),
  search: (q, classId) => api.get(`/students/search?q=${encodeURIComponent(q)}${classId ? `&class_id=${classId}` : ''}`),
};

// Exams
export const examsApi = {
  list: (page = 1, search = '', status = '', subjectId = '', classId = '') =>
    api.get(`/exams?page=${page}&search=${encodeURIComponent(search)}${status ? `&status=${status}` : ''}${subjectId ? `&subject_id=${subjectId}` : ''}${classId ? `&class_id=${classId}` : ''}`),
  get: (id) => api.get(`/exams/${id}`),
  create: (data) => api.post('/exams', data),
  update: (id, data) => api.put(`/exams/${id}`, data),
  delete: (id) => api.delete(`/exams/${id}`),
  publish: (id) => api.post(`/exams/${id}/publish`),
  archive: (id) => api.post(`/exams/${id}/archive`),
  duplicate: (id, title) => api.post(`/exams/${id}/duplicate?new_title=${encodeURIComponent(title)}`),
  answerSheet: (examId, studentId) => api.download(`/exams/${examId}/answer-sheet?student_id=${studentId}`, `answer_sheet_${examId}_${studentId}.pdf`),
  batchAnswerSheets: (examId, classId) => api.download(`/exams/${examId}/answer-sheets/batch?class_id=${classId}`, `answer_sheets_${examId}.pdf`),
};

// Scanner
export const scannerApi = {
  processBase64: (examId, imageBase64) => api.post('/scan/process-base64', { exam_id: examId, image_base64: imageBase64 }),
  processFile: (examId, file) => { const fd = new FormData(); fd.append('file', file); fd.append('exam_id', examId); return api.upload('/scan/process', fd); },
  history: (page = 1, status = '', examId = '') => api.get(`/scan/history?page=${page}${status ? `&status=${status}` : ''}${examId ? `&exam_id=${examId}` : ''}`),
  historyDetail: (id) => api.get(`/scan/history/${id}`),
  deleteHistory: (id) => api.delete(`/scan/history/${id}`),
};

// Results
export const resultsApi = {
  byExam: (examId, page = 1) => api.get(`/results/exam/${examId}?page=${page}`),
  byStudent: (studentId) => api.get(`/results/student/${studentId}`),
  studentExamResult: (studentId, examId) => api.get(`/results/student/${studentId}/exam/${examId}`),
  statistics: (examId) => api.get(`/results/exam/${examId}/statistics`),
  pendingReview: () => api.get('/results/pending-review'),
  review: (id, questionResults, notes) => api.put(`/results/${id}/review`, { question_results: questionResults, review_notes: notes }),
};

// Reports
export const reportsApi = {
  examExcel: (examId) => api.download(`/reports/exam/${examId}/excel`, `exam_${examId}_results.xlsx`),
  examCsv: (examId) => api.download(`/reports/exam/${examId}/csv`, `exam_${examId}_results.csv`),
  examPdf: (examId) => api.download(`/reports/exam/${examId}/pdf`, `exam_${examId}_report.pdf`),
  studentExcel: (studentId) => api.download(`/reports/student/${studentId}/excel`, `student_${studentId}_report.xlsx`),
  classExcel: (classId) => api.download(`/reports/class/${classId}/excel`, `class_${classId}_report.xlsx`),
  questionAnalysis: (examId) => api.download(`/reports/exam/${examId}/question-analysis/excel`, `exam_${examId}_questions.xlsx`),
};

// Settings
export const settingsApi = {
  get: () => api.get('/settings'),
  update: (data) => api.put('/settings', data),
  reset: () => api.post('/settings/reset'),
  uploadLogo: (file) => { const fd = new FormData(); fd.append('file', file); return api.upload('/settings/logo', fd); },
};

// Teacher
export const teacherApi = {
  me: () => api.get('/teachers/me'),
  update: (data) => api.put('/teachers/me', data),
};
