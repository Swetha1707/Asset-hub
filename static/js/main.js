// ================= Theme =================
(function initTheme() {
  const saved = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
  document.addEventListener('DOMContentLoaded', () => {
    updateThemeIcon(saved);
    const btn = document.getElementById('themeToggle');
    if (btn) btn.addEventListener('click', toggleTheme);
  });
})();

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
  updateThemeIcon(next);
}
function updateThemeIcon(theme) {
  const btn = document.getElementById('themeToggle');
  if (btn) btn.textContent = theme === 'dark' ? '☀️' : '🌙';
}

// ================= Sidebar (mobile) =================
document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('sidebar');
  const hamburger = document.getElementById('hamburgerBtn');
  const closeBtn = document.getElementById('sidebarClose');
  if (hamburger) hamburger.addEventListener('click', () => sidebar.classList.add('open'));
  if (closeBtn) closeBtn.addEventListener('click', () => sidebar.classList.remove('open'));
  document.addEventListener('click', (e) => {
    if (sidebar && sidebar.classList.contains('open') && !sidebar.contains(e.target) && e.target !== hamburger) {
      sidebar.classList.remove('open');
    }
  });
});

// ================= Toast =================
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) { alert(message); return; }
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ================= API helper =================
async function apiFetch(url, options = {}) {
  const opts = Object.assign({ headers: {} }, options);
  if (opts.body && !(opts.body instanceof FormData)) {
    opts.headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(url, opts);
  let data = null;
  try { data = await res.json(); } catch (e) { /* non-json (file download) */ }
  if (!res.ok) {
    const msg = (data && data.error) ? data.error : `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

function apiGet(url) { return apiFetch(url); }
function apiPost(url, body) { return apiFetch(url, { method: 'POST', body: JSON.stringify(body) }); }
function apiPut(url, body) { return apiFetch(url, { method: 'PUT', body: JSON.stringify(body) }); }
function apiDelete(url) { return apiFetch(url, { method: 'DELETE' }); }

function downloadFile(url) {
  window.open(url, '_blank');
}

// ================= Modal helpers =================
function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }
document.addEventListener('click', (e) => {
  if (e.target.classList && e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
  }
});

// ================= Badge helper =================
const STATUS_BADGE_MAP = {
  AVAILABLE: 'success', ASSIGNED: 'info', RESERVED: 'warning', UNDER_MAINTENANCE: 'warning',
  LOST: 'danger', DAMAGED: 'danger', RETIRED: 'muted', DISPOSED: 'muted',
  PENDING: 'warning', APPROVED: 'success', REJECTED: 'danger', ISSUED: 'info',
  RETURNED: 'muted', CANCELLED: 'muted', SCHEDULED: 'info', IN_PROGRESS: 'warning',
  COMPLETED: 'success', OK: 'success', DUE_SOON: 'warning', EXPIRED: 'danger',
  ACTIVE: 'success', INACTIVE: 'muted', SUCCESS: 'success', FAILED: 'danger', DENIED: 'danger',
};
function statusBadge(status) {
  const cls = STATUS_BADGE_MAP[status] || 'muted';
  const label = (status || '').replace(/_/g, ' ');
  return `<span class="badge badge-${cls}">${label}</span>`;
}
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str).replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
}
function formatMoney(v) {
  if (v === null || v === undefined || v === '') return '-';
  return '₹' + Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 });
}
function formatDate(v) {
  if (!v) return '-';
  try { return new Date(v).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }); }
  catch (e) { return v; }
}

// ================= Password visibility toggle =================
function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  if (input.type === 'password') { input.type = 'text'; btn.textContent = '🙈'; }
  else { input.type = 'password'; btn.textContent = '👁️'; }
}

// ================= AI Assistant floating panel =================
document.addEventListener('DOMContentLoaded', () => {
  const fab = document.getElementById('aiFab');
  const panel = document.getElementById('aiPanel');
  const closeBtn = document.getElementById('aiPanelClose');
  const form = document.getElementById('aiPanelForm');
  const input = document.getElementById('aiPanelInput');
  const body = document.getElementById('aiPanelBody');

  if (fab && panel) {
    fab.addEventListener('click', () => panel.classList.toggle('open'));
    closeBtn.addEventListener('click', () => panel.classList.remove('open'));
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const q = input.value.trim();
      if (!q) return;
      appendAiMessage(body, q, 'user');
      input.value = '';
      try {
  const thinking = appendAiMessage(body, 'Thinking...', 'bot');

  const res = await apiPost('/api/ai/ask', { question: q });

  thinking.textContent = res.answer;
} catch (err) {
        appendAiMessage(body, 'Sorry, something went wrong: ' + err.message, 'bot');
      }
    });
  }

  // Notification badge polling (admin-only; endpoint returns 403 for employees so skip if absent)
  const badge = document.getElementById('notifBadge');
  if (badge) {
    refreshNotifBadge();
    setInterval(refreshNotifBadge, 30000);
  }
});

function appendAiMessage(body, text, who) {
  const el = document.createElement('div');
  el.className = `ai-msg ai-msg-${who}`;
  el.textContent = text;
  body.appendChild(el);
  body.scrollTop = body.scrollHeight;
  return el;
}

async function refreshNotifBadge() {
  try {
    const res = await apiGet('/api/notifications');
    const badge = document.getElementById('notifBadge');
    if (!badge) return;
    if (res.unread_count > 0) {
      badge.style.display = 'inline-block';
      badge.textContent = res.unread_count;
    } else {
      badge.style.display = 'none';
    }
  } catch (e) { /* silently ignore, e.g. not permitted */ }
}
