/**
 * Layout Component - Renders sidebar and header
 */
import { logout, getStoredTeacher } from '../assets/js/auth.js';
import { toggleDarkMode, initSidebar } from '../assets/js/ui.js';

const NAV_ITEMS = [
  { href: 'dashboard.html', icon: '⊞', label: 'Dashboard' },
  { href: 'subjects.html', icon: '📚', label: 'Subjects' },
  { href: 'classes.html', icon: '🏫', label: 'Classes' },
  { href: 'students.html', icon: '👥', label: 'Students' },
  { href: 'exams.html', icon: '📝', label: 'Exams' },
  { href: 'scanner.html', icon: '📷', label: 'Scanner', highlight: true },
  { href: 'scan-history.html', icon: '🕐', label: 'Scan History' },
  { href: 'analytics.html', icon: '📊', label: 'Analytics' },
  { href: 'reports.html', icon: '📄', label: 'Reports' },
  { href: 'settings.html', icon: '⚙', label: 'Settings' },
];

export function renderLayout(pageTitle = 'Dashboard') {
  const teacher = getStoredTeacher();
  const name = teacher?.display_name || 'Teacher';
  const school = teacher?.school_name || 'My School';

  const navHtml = NAV_ITEMS.map(item => `
    <a href="${item.href}" class="nav-link${item.highlight ? ' font-semibold' : ''}">
      <span style="font-size:16px">${item.icon}</span>
      <span>${item.label}</span>
      ${item.highlight ? '<span class="badge badge-blue" style="margin-left:auto;font-size:10px">SCAN</span>' : ''}
    </a>`).join('');

  document.body.insertAdjacentHTML('afterbegin', `
    <div id="page-loader">
      <div style="width:40px;height:40px;border:3px solid #EFF6FF;border-top-color:#2563EB;border-radius:50%;animation:spin 0.7s linear infinite"></div>
      <p style="color:#64748B;font-size:14px">Loading...</p>
    </div>

    <div id="sidebar-overlay" style="position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:49;display:none" class="md:hidden"></div>

    <aside id="sidebar">
      <div style="padding:20px 16px;border-bottom:1px solid #E2E8F0" class="dark:border-slate-700">
        <div style="display:flex;align-items:center;gap:10px">
          <div style="width:36px;height:36px;background:linear-gradient(135deg,#2563EB,#7C3AED);border-radius:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:14px">AI</div>
          <div>
            <div style="font-size:13px;font-weight:700;color:#1E293B" class="dark:text-white">AI Exam Checker</div>
            <div style="font-size:11px;color:#64748B" class="dark:text-slate-400">${school}</div>
          </div>
        </div>
      </div>

      <nav style="padding:12px 0;flex:1">
        <div style="padding:0 8px 8px;font-size:11px;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:0.05em;padding-left:16px">Menu</div>
        ${navHtml}
      </nav>

      <div style="padding:16px;border-top:1px solid #E2E8F0" class="dark:border-slate-700">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
          <div style="width:32px;height:32px;background:#EFF6FF;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;color:#2563EB;font-weight:600">${name[0]?.toUpperCase()}</div>
          <div style="flex:1;min-width:0">
            <div style="font-size:13px;font-weight:600;color:#1E293B;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" class="dark:text-white">${name}</div>
            <div style="font-size:11px;color:#64748B">Teacher</div>
          </div>
        </div>
        <button id="logout-btn" class="btn btn-secondary" style="width:100%;justify-content:center;font-size:13px">
          <span>⎋</span> Sign Out
        </button>
      </div>
    </aside>

    <div id="main-content">
      <header id="top-header">
        <button id="sidebar-toggle" class="btn btn-secondary btn-sm" style="margin-right:12px;display:none" aria-label="Toggle sidebar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>
        <h1 style="font-size:18px;font-weight:600;flex:1">${pageTitle}</h1>
        <div style="display:flex;align-items:center;gap:8px">
          <button id="dark-mode-toggle" class="btn btn-secondary btn-sm" aria-label="Toggle dark mode">🌙</button>
          <a href="scanner.html" class="btn btn-primary btn-sm">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 7h3v3H7zM14 7h3v3h-3zM7 14h3v3H7z"/></svg>
            Scan
          </a>
        </div>
      </header>
      <main id="page-content" style="padding:24px">
  `);

  // Close the main-content div at end of body
  document.body.insertAdjacentHTML('beforeend', `
      </main>
    </div>
    <div id="toast-container"></div>
  `);

  // Show sidebar toggle on mobile
  if (window.innerWidth < 768) {
    document.getElementById('sidebar-toggle').style.display = 'flex';
  }

  // Event listeners
  document.getElementById('logout-btn')?.addEventListener('click', logout);
  document.getElementById('dark-mode-toggle')?.addEventListener('click', () => {
    const isDark = toggleDarkMode();
    document.getElementById('dark-mode-toggle').textContent = isDark ? '☀️' : '🌙';
  });

  initSidebar();
}
