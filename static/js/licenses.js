document.addEventListener('DOMContentLoaded', () => {
  loadLicenses();
  ['lSearch', 'lRenewal', 'lDepartment'].forEach(id => document.getElementById(id).addEventListener(id === 'lSearch' ? 'input' : 'change', debounce(loadLicenses, 300)));
});
function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
function buildQuery(params) { const q = new URLSearchParams(); Object.entries(params).forEach(([k, v]) => { if (v) q.set(k, v); }); return q.toString(); }
function lFilters() { return { q: document.getElementById('lSearch').value, renewal_status: document.getElementById('lRenewal').value, department_id: document.getElementById('lDepartment').value }; }

async function loadLicenses() {
  const tbody = document.getElementById('licensesBody');
  tbody.innerHTML = `<tr><td colspan="7"><div class="skeleton"></div></td></tr>`;
  try {
    const res = await apiGet('/api/licenses?' + buildQuery(lFilters()));
    document.getElementById('lActive').textContent = res.active;
    document.getElementById('lExpiring').textContent = res.expiring;
    document.getElementById('lExpired').textContent = res.expired;
    if (!res.data.length) { tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="icon">🔑</div>No licenses found.</div></td></tr>`; return; }
    tbody.innerHTML = res.data.map(l => `
      <tr>
        <td data-label="Software"><strong>${escapeHtml(l.software_name)}</strong></td>
        <td data-label="Vendor">${escapeHtml(l.vendor || '-')}</td>
        <td data-label="Expiry">${formatDate(l.expiry_date)}</td>
        <td data-label="Seats">
          ${l.seats_used}/${l.seats_total}
          <div class="progress-bar" style="width:80px; margin-top:4px;"><div class="progress-bar-fill" style="width:${Math.min(100, (l.seats_used / (l.seats_total || 1)) * 100)}%;"></div></div>
        </td>
        <td data-label="Renewal">${statusBadge(l.renewal_status)}</td>
        <td data-label="Cost">${formatMoney(l.cost)}</td>
        <td data-label="Actions"><button class="btn btn-sm btn-outline" onclick='editLicense(${JSON.stringify(l)})'>Edit</button></td>
      </tr>`).join('');
  } catch (e) { tbody.innerHTML = `<tr><td colspan="7">Error: ${escapeHtml(e.message)}</td></tr>`; }
}

function openLicenseForm() {
  document.getElementById('licenseId').value = '';
  document.getElementById('licFormTitle').textContent = 'Add License';
  ['lf_software_name', 'lf_license_type', 'lf_vendor', 'lf_license_key', 'lf_start_date', 'lf_expiry_date', 'lf_cost', 'lf_notes'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('lf_seats_total').value = 1;
  document.getElementById('lf_seats_used').value = 0;
  document.getElementById('lf_department_id').value = '';
  document.getElementById('lf_renewal_status').value = 'OK';
  document.getElementById('lf_auto_renewal').checked = false;
  openModal('licenseFormModal');
}

function editLicense(l) {
  document.getElementById('licenseId').value = l.id;
  document.getElementById('licFormTitle').textContent = 'Edit License';
  document.getElementById('lf_software_name').value = l.software_name;
  document.getElementById('lf_license_type').value = l.license_type || '';
  document.getElementById('lf_vendor').value = l.vendor || '';
  document.getElementById('lf_license_key').value = l.license_key || '';
  document.getElementById('lf_start_date').value = l.start_date || '';
  document.getElementById('lf_expiry_date').value = l.expiry_date || '';
  document.getElementById('lf_seats_total').value = l.seats_total;
  document.getElementById('lf_seats_used').value = l.seats_used;
  document.getElementById('lf_cost').value = l.cost;
  document.getElementById('lf_department_id').value = l.department_id || '';
  document.getElementById('lf_renewal_status').value = l.renewal_status;
  document.getElementById('lf_auto_renewal').checked = !!l.auto_renewal;
  document.getElementById('lf_notes').value = l.notes || '';
  openModal('licenseFormModal');
}

async function submitLicenseForm() {
  const id = document.getElementById('licenseId').value;
  const payload = {
    software_name: document.getElementById('lf_software_name').value,
    license_type: document.getElementById('lf_license_type').value,
    vendor: document.getElementById('lf_vendor').value,
    license_key: document.getElementById('lf_license_key').value,
    start_date: document.getElementById('lf_start_date').value,
    expiry_date: document.getElementById('lf_expiry_date').value,
    seats_total: document.getElementById('lf_seats_total').value,
    seats_used: document.getElementById('lf_seats_used').value,
    cost: document.getElementById('lf_cost').value,
    department_id: document.getElementById('lf_department_id').value,
    renewal_status: document.getElementById('lf_renewal_status').value,
    auto_renewal: document.getElementById('lf_auto_renewal').checked,
    notes: document.getElementById('lf_notes').value,
  };
  if (!payload.software_name) { showToast('Software name is required.', 'error'); return; }
  try {
    if (id) { await apiPut(`/api/licenses/${id}`, payload); showToast('License updated successfully.', 'success'); }
    else { await apiPost('/api/licenses', payload); showToast('License added successfully.', 'success'); }
    closeModal('licenseFormModal');
    loadLicenses();
  } catch (e) { showToast(e.message, 'error'); }
}

function exportLicenses(fmt) { downloadFile(`/api/licenses/export/${fmt}?` + buildQuery(lFilters())); }
