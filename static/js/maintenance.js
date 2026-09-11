document.addEventListener('DOMContentLoaded', () => {
  loadMaintenance();
  ['mSearch', 'mStatus'].forEach(id => document.getElementById(id).addEventListener(id === 'mSearch' ? 'input' : 'change', debounce(loadMaintenance, 300)));
});
function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
function buildQuery(params) { const q = new URLSearchParams(); Object.entries(params).forEach(([k, v]) => { if (v) q.set(k, v); }); return q.toString(); }
function mFilters() { return { q: document.getElementById('mSearch').value, status: document.getElementById('mStatus').value }; }

async function loadMaintenance() {
  const tbody = document.getElementById('maintenanceBody');
  tbody.innerHTML = `<tr><td colspan="9"><div class="skeleton"></div></td></tr>`;
  try {
    const res = await apiGet('/api/maintenance?' + buildQuery(mFilters()));
    document.getElementById('mUpcoming').textContent = res.upcoming_count;
    document.getElementById('mOverdue').textContent = res.overdue_count;
    document.getElementById('mCost').textContent = formatMoney(res.total_cost);
    if (!res.data.length) { tbody.innerHTML = `<tr><td colspan="9"><div class="empty-state"><div class="icon">🔧</div>No maintenance records found.</div></td></tr>`; return; }
    tbody.innerHTML = res.data.map(m => `
      <tr>
        <td data-label="Asset">${escapeHtml(m.asset_code)} - ${escapeHtml(m.asset_name)}</td>
        <td data-label="Type">${escapeHtml(m.maintenance_type || '-')}</td>
        <td data-label="Problem">${escapeHtml(m.problem || '-')}</td>
        <td data-label="Vendor">${escapeHtml(m.vendor || '-')}</td>
        <td data-label="Start">${formatDate(m.start_date)}</td>
        <td data-label="Expected">${formatDate(m.expected_completion)}</td>
        <td data-label="Cost">${formatMoney(m.cost)}</td>
        <td data-label="Status">${statusBadge(m.status)}</td>
        <td data-label="Actions"><button class="btn btn-sm btn-outline" onclick='editMaintenance(${JSON.stringify(m)})'>Edit</button></td>
      </tr>`).join('');
  } catch (e) { tbody.innerHTML = `<tr><td colspan="9">Error: ${escapeHtml(e.message)}</td></tr>`; }
}

function openMaintenanceForm() {
  document.getElementById('maintenanceId').value = '';
  document.getElementById('maintFormTitle').textContent = 'Schedule Maintenance';
  ['mf_asset_search', 'mf_type', 'mf_vendor', 'mf_problem', 'mf_description', 'mf_technician', 'mf_cost', 'mf_start_date', 'mf_expected_completion', 'mf_remarks'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('mf_asset_id').value = '';
  document.getElementById('mf_status').value = 'SCHEDULED';
  openModal('maintenanceFormModal');
}

function editMaintenance(m) {
  document.getElementById('maintenanceId').value = m.id;
  document.getElementById('maintFormTitle').textContent = 'Edit Maintenance';
  document.getElementById('mf_asset_search').value = `${m.asset_code} - ${m.asset_name}`;
  document.getElementById('mf_asset_id').value = m.asset_id;
  document.getElementById('mf_type').value = m.maintenance_type || '';
  document.getElementById('mf_vendor').value = m.vendor || '';
  document.getElementById('mf_problem').value = m.problem || '';
  document.getElementById('mf_description').value = m.description || '';
  document.getElementById('mf_technician').value = m.technician || '';
  document.getElementById('mf_cost').value = m.cost || '';
  document.getElementById('mf_start_date').value = m.start_date || '';
  document.getElementById('mf_expected_completion').value = m.expected_completion || '';
  document.getElementById('mf_status').value = m.status;
  document.getElementById('mf_remarks').value = m.remarks || '';
  openModal('maintenanceFormModal');
}

let assetSearchTimeout;
function searchAssetForMaintenance(term) {
  clearTimeout(assetSearchTimeout);
  const results = document.getElementById('mf_asset_results');
  if (!term) { results.innerHTML = ''; return; }
  assetSearchTimeout = setTimeout(async () => {
    try {
      const res = await apiGet('/api/assets?q=' + encodeURIComponent(term) + '&per_page=6');
      if (!res.data.length) { results.innerHTML = 'No matching assets.'; return; }
      results.innerHTML = res.data.map(a => `<div style="cursor:pointer; padding:4px 0;" onclick="selectMaintAsset(${a.id}, '${escapeHtml(a.asset_code)} - ${escapeHtml(a.name)}')">${escapeHtml(a.asset_code)} - ${escapeHtml(a.name)}</div>`).join('');
    } catch (e) { results.innerHTML = 'Error searching assets.'; }
  }, 250);
}
function selectMaintAsset(id, label) {
  document.getElementById('mf_asset_id').value = id;
  document.getElementById('mf_asset_search').value = label;
  document.getElementById('mf_asset_results').innerHTML = '';
}

async function submitMaintenanceForm() {
  const id = document.getElementById('maintenanceId').value;
  const payload = {
    asset_id: document.getElementById('mf_asset_id').value,
    maintenance_type: document.getElementById('mf_type').value,
    vendor: document.getElementById('mf_vendor').value,
    problem: document.getElementById('mf_problem').value,
    description: document.getElementById('mf_description').value,
    technician: document.getElementById('mf_technician').value,
    cost: document.getElementById('mf_cost').value,
    start_date: document.getElementById('mf_start_date').value,
    expected_completion: document.getElementById('mf_expected_completion').value,
    status: document.getElementById('mf_status').value,
    remarks: document.getElementById('mf_remarks').value,
  };
  if (!payload.asset_id) { showToast('Please select an asset.', 'error'); return; }
  try {
    if (id) { await apiPut(`/api/maintenance/${id}`, payload); showToast('Maintenance record updated successfully.', 'success'); }
    else { await apiPost('/api/maintenance', payload); showToast('Maintenance record created successfully.', 'success'); }
    closeModal('maintenanceFormModal');
    loadMaintenance();
  } catch (e) { showToast(e.message, 'error'); }
}

function exportMaintenance(fmt) { downloadFile(`/api/maintenance/export/${fmt}?` + buildQuery(mFilters())); }
