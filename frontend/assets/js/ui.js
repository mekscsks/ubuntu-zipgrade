/**
 * UI Utilities - Shared UI components and helpers
 */

// Toast notifications
export function showToast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container') || createToastContainer();
  const toast = document.createElement('div');
  const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || icons.info}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = 'slideOut 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function createToastContainer() {
  const el = document.createElement('div');
  el.id = 'toast-container';
  document.body.appendChild(el);
  return el;
}

// Modal management
export function openModal(id) {
  const el = document.getElementById(id);
  if (el) { el.classList.add('open'); document.body.style.overflow = 'hidden'; }
}

export function closeModal(id) {
  const el = document.getElementById(id);
  if (el) { el.classList.remove('open'); document.body.style.overflow = ''; }
}

export function createConfirmModal(title, message, onConfirm, danger = true) {
  const id = 'confirm-modal-' + Date.now();
  const modal = document.createElement('div');
  modal.className = 'modal-overlay open';
  modal.id = id;
  modal.innerHTML = `
    <div class="modal" style="max-width:400px">
      <div class="modal-header">
        <h3 style="font-size:16px;font-weight:600">${title}</h3>
        <button onclick="document.getElementById('${id}').remove()" class="btn btn-secondary btn-sm">✕</button>
      </div>
      <div class="modal-body"><p style="color:#64748B;font-size:14px">${message}</p></div>
      <div class="modal-footer">
        <button onclick="document.getElementById('${id}').remove()" class="btn btn-secondary">Cancel</button>
        <button id="${id}-confirm" class="btn ${danger ? 'btn-danger' : 'btn-primary'}">Confirm</button>
      </div>
    </div>`;
  document.body.appendChild(modal);
  document.getElementById(`${id}-confirm`).onclick = () => {
    modal.remove();
    onConfirm();
  };
  modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
}

// Loading state helpers
export function setLoading(btn, loading, text = '') {
  if (!btn) return;
  if (loading) {
    btn._originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span>${text || 'Loading...'}`;
  } else {
    btn.disabled = false;
    btn.innerHTML = btn._originalText || text;
  }
}

// Pagination renderer
export function renderPagination(container, currentPage, totalPages, onPageChange) {
  if (!container) return;
  container.innerHTML = '';
  if (totalPages <= 1) return;

  const pages = getPaginationPages(currentPage, totalPages);
  pages.forEach(p => {
    const btn = document.createElement('button');
    btn.className = `page-btn${p === currentPage ? ' active' : ''}${p === '...' ? ' cursor-default' : ''}`;
    btn.textContent = p;
    if (p !== '...' && p !== currentPage) btn.onclick = () => onPageChange(p);
    container.appendChild(btn);
  });
}

function getPaginationPages(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages = [1];
  if (current > 3) pages.push('...');
  for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) pages.push(i);
  if (current < total - 2) pages.push('...');
  pages.push(total);
  return pages;
}

// Format helpers
export function formatDate(dateStr) {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function formatDateTime(dateStr) {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function formatScore(score) {
  return typeof score === 'number' ? `${score.toFixed(1)}%` : '-';
}

export function getScoreBadge(score, passingScore = 60) {
  const cls = score >= passingScore ? 'badge-green' : 'badge-red';
  return `<span class="badge ${cls}">${formatScore(score)}</span>`;
}

export function getStatusBadge(status) {
  const map = {
    draft: 'badge-gray', published: 'badge-blue', archived: 'badge-yellow',
    completed: 'badge-green', failed: 'badge-red', manual_review: 'badge-yellow',
    processing: 'badge-blue', pending: 'badge-gray',
  };
  return `<span class="badge ${map[status] || 'badge-gray'}">${status?.replace('_', ' ') || '-'}</span>`;
}

// Debounce
export function debounce(fn, delay = 300) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
}

// Empty state
export function renderEmptyState(container, message = 'No data found', icon = '📋') {
  container.innerHTML = `
    <div class="empty-state">
      <div style="font-size:48px;margin-bottom:12px">${icon}</div>
      <p style="font-size:15px;font-weight:500;color:#64748B">${message}</p>
    </div>`;
}

// Dark mode
export function initDarkMode() {
  const stored = localStorage.getItem('dark_mode');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const isDark = stored !== null ? stored === 'true' : prefersDark;
  document.documentElement.classList.toggle('dark', isDark);
  return isDark;
}

export function toggleDarkMode() {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('dark_mode', isDark);
  return isDark;
}

// Sidebar toggle for mobile
export function initSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  const toggleBtn = document.getElementById('sidebar-toggle');

  if (toggleBtn) {
    toggleBtn.onclick = () => {
      sidebar?.classList.toggle('open');
      overlay?.classList.toggle('open');
    };
  }
  if (overlay) {
    overlay.onclick = () => {
      sidebar?.classList.remove('open');
      overlay.classList.remove('open');
    };
  }

  // Mark active nav link
  const path = window.location.pathname;
  document.querySelectorAll('#sidebar .nav-link').forEach(link => {
    if (link.getAttribute('href') && path.includes(link.getAttribute('href').replace('../', '').replace('.html', ''))) {
      link.classList.add('active');
    }
  });
}

// Page loader
export function hideLoader() {
  const loader = document.getElementById('page-loader');
  if (loader) { loader.style.opacity = '0'; setTimeout(() => loader.remove(), 300); }
}

// Form validation helper
export function validateForm(formEl) {
  let valid = true;
  formEl.querySelectorAll('[required]').forEach(input => {
    const err = input.parentElement.querySelector('.field-error');
    if (!input.value.trim()) {
      valid = false;
      input.style.borderColor = '#EF4444';
      if (err) err.textContent = 'This field is required';
    } else {
      input.style.borderColor = '';
      if (err) err.textContent = '';
    }
  });
  return valid;
}

// Number formatting
export function formatNumber(n) {
  if (n === null || n === undefined) return '0';
  return new Intl.NumberFormat().format(n);
}

// Copy to clipboard
export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    showToast('Copied to clipboard', 'success', 2000);
  } catch {
    showToast('Failed to copy', 'error');
  }
}
