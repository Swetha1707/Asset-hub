document.addEventListener('DOMContentLoaded', () => {
  loadActivityLogs();
  document.getElementById('alSearch').addEventListener('input', debounce(loadActivityLogs, 350));
  document.getElementById('alUser').addEventListener('input', debounce(loadActivityLogs, 350));
  document.getElementById('alModule').addEventListener('change', loadActivityLogs);
});
function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
function buildQuery(params) { const q = new URLSearchParams(); Object.entries(params).forEach(([k, v]) => { if (v) q.set(k, v); }); return q.toString(); }

async function loadActivityLogs() {
  const tbody = document.getElementById('activityLogsBody');
  tbody.innerHTML = `<tr><td colspan="6"><div class="skeleton"></div></td></tr>`;
  const params = {
    q: document.getElementById('alSearch').value,
    username: document.getElementById('alUser').value,
    module: document.getElementById('alModule').value,
    date_from: document.getElementById('alDateFrom').value,
    date_to: document.getElementById('alDateTo').value,
  };
  try {
    const res = await apiGet('/api/activity-logs?' + buildQuery(params));
    if (!res.data.length) { tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><div class="icon">📜</div>No activity found.</div></td></tr>`; return; }
    tbody.innerHTML = res.data.map(l => `
      <tr>
        <td data-label="User">${escapeHtml(l.username)}</td>
        <td data-label="Action">${escapeHtml(l.action)}</td>
        <td data-label="Module">${escapeHtml(l.module || '-')}</td>
        <td data-label="Description">${escapeHtml(l.description || '-')}</td>
        <td data-label="Status">${statusBadge(l.status)}</td>
        <td data-label="Timestamp">${formatDate(l.created_at)}</td>
      </tr>`).join('');
  } catch (e) { tbody.innerHTML = `<tr><td colspan="6">Error: ${escapeHtml(e.message)}</td></tr>`; }
}
