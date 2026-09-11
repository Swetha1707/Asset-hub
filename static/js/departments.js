let currentDeptId = null;

document.addEventListener('DOMContentLoaded', loadDepartments);

async function loadDepartments() {
  const container = document.getElementById('deptCards');
  try {
    const res = await apiGet('/api/departments');
    if (!res.data.length) { container.innerHTML = `<div class="empty-state"><div class="icon">🏢</div>No departments found.</div>`; return; }
    container.innerHTML = res.data.map(d => `
      <div class="card" style="cursor:pointer;" onclick="viewDepartment(${d.id}, '${escapeHtml(d.name)}')">
        <div class="card-title">🏢 ${escapeHtml(d.name)}</div>
        <div style="font-size:13px; color:var(--text-muted); margin-bottom:10px;">Head: ${escapeHtml(d.head_name || '-')}</div>
        <div class="grid grid-cols-2" style="gap:8px;">
          <div><div class="stat-label">Total Assets</div><div class="stat-value" style="font-size:20px;">${d.total_assets}</div></div>
          <div><div class="stat-label">Total Value</div><div class="stat-value" style="font-size:20px;">${formatMoney(d.total_value)}</div></div>
        </div>
        <div style="margin-top:10px; font-size:12.5px; color:var(--text-muted);">
          ✅ ${d.available_assets} available &nbsp; 👤 ${d.assigned_assets} assigned &nbsp; 🔧 ${d.maintenance_assets} maintenance
        </div>
      </div>`).join('');
  } catch (e) { container.innerHTML = `Error: ${escapeHtml(e.message)}`; }
}

async function viewDepartment(id, name) {
  currentDeptId = id;
  document.getElementById('deptDetailsTitle').textContent = `${name} — Assets`;
  openModal('deptDetailsModal');
  const body = document.getElementById('deptAssetsBody');
  body.innerHTML = `<tr><td colspan="5"><div class="skeleton"></div></td></tr>`;
  try {
    const res = await apiGet(`/api/departments/${id}/assets`);
    document.getElementById('deptSummary').innerHTML = `<strong>${res.assets.length}</strong> asset(s) in this department`;
    if (!res.assets.length) { body.innerHTML = `<tr><td colspan="5"><div class="empty-state">No assets in this department.</div></td></tr>`; return; }
    body.innerHTML = res.assets.map(a => `
      <tr>
        <td data-label="Asset">${escapeHtml(a.name)}</td>
        <td data-label="Asset ID">${escapeHtml(a.asset_code)}</td>
        <td data-label="Assigned To">${escapeHtml(a.assigned_employee_name || '-')}</td>
        <td data-label="Status">${statusBadge(a.status)}</td>
        <td data-label="Value">${formatMoney(a.current_value)}</td>
      </tr>`).join('');
  } catch (e) { body.innerHTML = `<tr><td colspan="5">Error: ${escapeHtml(e.message)}</td></tr>`; }
}

function exportDept(fmt) {
  if (!currentDeptId) return;
  downloadFile(`/api/departments/${currentDeptId}/export/${fmt}`);
}
