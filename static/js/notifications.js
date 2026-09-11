document.addEventListener('DOMContentLoaded', loadNotifications);

const NOTIF_ICONS = { LICENSE_EXPIRY: '⚠️', MAINTENANCE: '🔧', REQUEST: '📝', ASSET: '💻', WARRANTY: '📦' };

async function loadNotifications() {
  const container = document.getElementById('notificationsList');
  try {
    const res = await apiGet('/api/notifications');
    if (!res.data.length) { container.innerHTML = `<div class="empty-state"><div class="icon">🔔</div>No notifications yet.</div>`; return; }
    container.innerHTML = res.data.map(n => `
      <div class="insight-card" style="margin-bottom:8px; ${n.is_read ? 'opacity:.6;' : ''}" onclick="markRead(${n.id})">
        <div class="insight-icon">${NOTIF_ICONS[n.type] || '🔔'}</div>
        <div>
          <strong>${escapeHtml(n.title)}</strong>
          <div style="font-size:13px; color:var(--text-muted);">${escapeHtml(n.message || '')}</div>
          <div style="font-size:11.5px; color:var(--text-muted); margin-top:4px;">${formatDate(n.created_at)}</div>
        </div>
      </div>`).join('');
  } catch (e) { container.innerHTML = `Error: ${escapeHtml(e.message)}`; }
}

async function markRead(id) {
  try { await apiPost(`/api/notifications/${id}/read`, {}); loadNotifications(); refreshNotifBadge(); } catch (e) {}
}
async function markAllRead() {
  try { await apiPost('/api/notifications/read-all', {}); showToast('All notifications marked as read.', 'success'); loadNotifications(); refreshNotifBadge(); }
  catch (e) { showToast(e.message, 'error'); }
}
