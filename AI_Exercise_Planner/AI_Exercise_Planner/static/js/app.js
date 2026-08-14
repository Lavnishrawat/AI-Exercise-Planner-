/**
 * app.js – Shared utilities used by every page.
 * Sidebar toggle, modal helpers, toast notifications, API wrapper.
 */

'use strict';

/* --------------------------------------------------------------------------
   Sidebar toggle (mobile)
   -------------------------------------------------------------------------- */
const sidebar        = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');
const menuToggle     = document.getElementById('menuToggle');
const sidebarClose   = document.getElementById('sidebarClose');

function openSidebar() {
  sidebar.classList.add('open');
  sidebarOverlay.classList.add('active');
  document.body.style.overflow = 'hidden';
}
function closeSidebar() {
  sidebar.classList.remove('open');
  sidebarOverlay.classList.remove('active');
  document.body.style.overflow = '';
}

if (menuToggle)     menuToggle.addEventListener('click', openSidebar);
if (sidebarClose)   sidebarClose.addEventListener('click', closeSidebar);
if (sidebarOverlay) sidebarOverlay.addEventListener('click', closeSidebar);

/* --------------------------------------------------------------------------
   Toast notifications
   -------------------------------------------------------------------------- */
/**
 * showToast(message, type, duration)
 * type: 'success' | 'error' | 'warning' | '' (default dark)
 */
window.showToast = function(message, type = '', duration = 3500) {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icons = { success: '✔', error: '✖', warning: '⚠️' };
  toast.textContent = (icons[type] ? icons[type] + '  ' : '') + message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'opacity .3s, transform .3s';
    setTimeout(() => toast.remove(), 320);
  }, duration);
};

/* --------------------------------------------------------------------------
   Modal helpers
   -------------------------------------------------------------------------- */
const modalBackdrop = document.getElementById('modalBackdrop');

/**
 * openModal(modalEl) – show a .modal element and the backdrop.
 */
window.openModal = function(modalEl) {
  if (!modalEl) return;
  modalEl.classList.add('active');
  if (modalBackdrop) modalBackdrop.classList.add('active');
  document.body.style.overflow = 'hidden';
};

/**
 * closeModal(modalEl) – hide a .modal element.
 */
window.closeModal = function(modalEl) {
  if (!modalEl) return;
  modalEl.classList.remove('active');
  // Only remove backdrop if no other modals are open.
  const anyOpen = document.querySelectorAll('.modal.active').length > 0;
  if (!anyOpen && modalBackdrop) modalBackdrop.classList.remove('active');
  document.body.style.overflow = '';
};

// Close on backdrop click.
if (modalBackdrop) {
  modalBackdrop.addEventListener('click', () => {
    document.querySelectorAll('.modal.active').forEach(m => closeModal(m));
  });
}

// Close on Escape key.
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal.active').forEach(m => closeModal(m));
    closeSidebar();
  }
});

/* --------------------------------------------------------------------------
   API helper
   -------------------------------------------------------------------------- */
/**
 * api(path, options) – thin wrapper around fetch().
 * Always parses JSON. Rejects with { error: string } on failure.
 */
window.api = async function(path, options = {}) {
  const defaults = {
    headers: { 'Content-Type': 'application/json' },
  };
  const merged = { ...defaults, ...options };
  if (merged.body && typeof merged.body === 'object') {
    merged.body = JSON.stringify(merged.body);
  }
  const resp = await fetch(path, merged);
  let data;
  try { data = await resp.json(); } catch { data = {}; }
  if (!resp.ok) {
    throw Object.assign(new Error(data.error || `HTTP ${resp.status}`), { data, status: resp.status });
  }
  return data;
};

/* --------------------------------------------------------------------------
   Utility: format duration minutes → "Xh Ymin" / "Y min"
   -------------------------------------------------------------------------- */
window.formatDuration = function(minutes) {
  if (!minutes || minutes <= 0) return '—';
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h > 0) return m > 0 ? `${h}h ${m}min` : `${h}h`;
  return `${m} min`;
};

/* --------------------------------------------------------------------------
   Utility: difficulty badge colour
   -------------------------------------------------------------------------- */
window.difficultyBadge = function(difficulty) {
  const map = { Beginner: 'badge--green', Intermediate: 'badge--amber', Advanced: 'badge--red' };
  const cls = map[difficulty] || 'badge--gray';
  return `<span class="badge ${cls}">${difficulty || '—'}</span>`;
};

/* --------------------------------------------------------------------------
   Utility: sanitise plain text for insertion into innerHTML
   -------------------------------------------------------------------------- */
window.esc = function(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
};
