let currentPage = 1;
let deleteTargetId = null;
const PERMS = window.USER_PERMS || null; // populated below via data attr fallback

document.addEventListener('DOMContentLoaded', () => {
  loadAssets();
  ['fSearch', 'fCategory', 'fDepartment', 'fStatus', 'fAssigned'].forEach(id => {
    const el = document.getElementById(id);
    el.addEventListener(id === 'fSearch' ? 'input' : 'change', debounce(() => { currentPage = 1; loadAssets(); }, 300));
  });
});

function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }

function currentFilters() {
  return {
    q: document.getElementById('fSearch').value,
    category_id: document.getElementById('fCategory').value,
    department_id: document.getElementById('fDepartment').value,
    status: document.getElementById('fStatus').value,
    assigned: document.getElementById('fAssigned').value,
  };
}
function buildQuery(params) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v) q.set(k, v); });
  return q.toString();
}

function resetFilters() {
  ['fSearch'].forEach(id => document.getElementById(id).value = '');
  ['fCategory', 'fDepartment', 'fStatus', 'fAssigned'].forEach(id => document.getElementById(id).value = '');
  currentPage = 1;
  loadAssets();
}

async function loadAssets() {
  const tbody = document.getElementById('assetsTableBody');
  tbody.innerHTML = `<tr><td colspan="8"><div class="skeleton"></div></td></tr>`;
  try {
    const params = Object.assign({ page: currentPage, per_page: 12 }, currentFilters());
    const res = await apiGet('/api/assets?' + buildQuery(params));
    if (!res.data.length) {
      tbody.innerHTML = `<tr><td colspan="8"><div class="empty-state"><div class="icon">📭</div>No assets match your filters.</div></td></tr>`;
      document.getElementById('assetsPagination').innerHTML = '';
      return;
    }
    tbody.innerHTML = res.data.map(rowHtml).join('');
    renderPagination(res.total, res.page, res.per_page);
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="8">Error: ${escapeHtml(e.message)}</td></tr>`;
  }
}

function rowHtml(a) {
  return `<tr>
    <td data-label="Asset ID"><a href="#" onclick="viewAsset(${a.id}); return false;" style="color:var(--primary); font-weight:600;">${escapeHtml(a.asset_code)}</a></td>
    <td data-label="Name">${escapeHtml(a.name)}</td>
    <td data-label="Category">${escapeHtml(a.category_name || '-')}</td>
    <td data-label="Department">${escapeHtml(a.department_name || '-')}</td>
    <td data-label="Assigned To">${escapeHtml(a.assigned_employee_name || '-')}</td>
    <td data-label="Status">${statusBadge(a.status)}</td>
    <td data-label="Value">${formatMoney(a.current_value)}</td>
    <td data-label="Actions">
      ${hasPerm('EDIT_ASSETS') ? `<button class="btn btn-sm btn-outline" onclick="editAsset(${a.id})">Edit</button>` : ''}
      ${hasPerm('DELETE_ASSETS') ? `<button class="btn btn-sm btn-danger" onclick="askDelete(${a.id})">Delete</button>` : ''}
    </td>
  </tr>`;
}

function hasPerm(code) {
  return document.body.dataset.perms && document.body.dataset.perms.includes(code);
}

function renderPagination(total, page, perPage) {
  const pages = Math.ceil(total / perPage);
  const el = document.getElementById('assetsPagination');
  if (pages <= 1) { el.innerHTML = ''; return; }
  let html = '';
  for (let i = 1; i <= pages; i++) {
    html += `<button class="${i === page ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
  }
  el.innerHTML = html;
}
function goToPage(p) { currentPage = p; loadAssets(); }

// ---------------- Add/Edit form ----------------
function handleCategoryChange() {
  const category = document.getElementById('af_category_id').value;
  const group = document.getElementById('newCategoryGroup');
  const input = document.getElementById('af_new_category_name');

  if (category === 'OTHERS') {
    group.style.display = 'block';
    input.required = true;
    input.focus();
  } else {
    group.style.display = 'none';
    input.required = false;
    input.value = '';
  }
}
function openAssetForm(asset = null) {
  document.getElementById('assetForm').reset();
  document.getElementById('newCategoryGroup').style.display = 'none';
document.getElementById('af_new_category_name').value = '';
document.getElementById('af_new_category_name').required = false;
  document.getElementById('assetId').value = '';
  document.getElementById('assetFormTitle').textContent = asset ? 'Edit Asset' : 'Add Asset';
  if (asset) {
    document.getElementById('assetId').value = asset.id;
    document.getElementById('af_asset_code').value = asset.asset_code;
    document.getElementById('af_asset_code').disabled = true;
    document.getElementById('af_name').value = asset.name;
    document.getElementById('af_category_id').value = asset.category_id || '';
    document.getElementById('af_department_id').value = asset.department_id || '';
    document.getElementById('af_brand').value = asset.brand || '';
    document.getElementById('af_model').value = asset.model || '';
    document.getElementById('af_serial_number').value = asset.serial_number || '';
    document.getElementById('af_vendor').value = asset.vendor || '';
    document.getElementById('af_purchase_date').value = asset.purchase_date || '';
    document.getElementById('af_purchase_cost').value = asset.purchase_cost || '';
    document.getElementById('af_current_value').value = asset.current_value || '';
    document.getElementById('af_location').value = asset.location || '';
    document.getElementById('af_warranty_start').value = asset.warranty_start || '';
    document.getElementById('af_warranty_end').value = asset.warranty_end || '';
    document.getElementById('af_status').value = asset.status;
    document.getElementById('af_condition_status').value = asset.condition_status;
    document.getElementById('af_description').value = asset.description || '';
  } else {
    document.getElementById('af_asset_code').disabled = false;
  }
  openModal('assetFormModal');
}

async function editAsset(id) {
  try {
    const res = await apiGet(`/api/assets/${id}`);
    openAssetForm(res.asset);
  } catch (e) { showToast(e.message, 'error'); }
}

async function submitAssetForm() {
  const id = document.getElementById('assetId').value;
  const payload = {
    asset_code: document.getElementById('af_asset_code').value,
    name: document.getElementById('af_name').value,
category_id:
  document.getElementById('af_category_id').value === 'OTHERS'
    ? ''
    : document.getElementById('af_category_id').value,

new_category_name:
  document.getElementById('af_category_id').value === 'OTHERS'
    ? document.getElementById('af_new_category_name').value.trim()
    : '',
        department_id: document.getElementById('af_department_id').value,
    brand: document.getElementById('af_brand').value,
    model: document.getElementById('af_model').value,
    serial_number: document.getElementById('af_serial_number').value,
    vendor: document.getElementById('af_vendor').value,
    purchase_date: document.getElementById('af_purchase_date').value,
    purchase_cost: document.getElementById('af_purchase_cost').value,
    current_value: document.getElementById('af_current_value').value,
    location: document.getElementById('af_location').value,
    warranty_start: document.getElementById('af_warranty_start').value,
    warranty_end: document.getElementById('af_warranty_end').value,
    status: document.getElementById('af_status').value,
    condition_status: document.getElementById('af_condition_status').value,
    description: document.getElementById('af_description').value,
  };
  if (!payload.asset_code || !payload.name) {
  showToast('Asset ID and Name are required.', 'error');
  return;
}

if (!payload.category_id && !payload.new_category_name) {
  showToast('Please select a category or enter a new category name.', 'error');
  return;
}
  try {
    if (id) {
      await apiPut(`/api/assets/${id}`, payload);
      showToast('Asset updated successfully.', 'success');
    } else {
      await apiPost('/api/assets', payload);
      showToast('Asset added successfully.', 'success');
    }
    closeModal('assetFormModal');
    loadAssets();
  } catch (e) { showToast(e.message, 'error'); }
}

function askDelete(id) {
  deleteTargetId = id;
  openModal('deleteConfirmModal');
}
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('confirmDeleteBtn').addEventListener('click', async () => {
    try {
      await apiDelete(`/api/assets/${deleteTargetId}`);
      showToast('Asset deleted successfully.', 'success');
      closeModal('deleteConfirmModal');
      loadAssets();
    } catch (e) { showToast(e.message, 'error'); }
  });
});

// ---------------- Details ----------------
async function viewAsset(id) {
  openModal('assetDetailsModal');
  const body = document.getElementById('assetDetailsBody');
  body.innerHTML = 'Loading...';
  try {
    const res = await apiGet(`/api/assets/${id}`);
    const a = res.asset;
    body.innerHTML = `
      <div class="grid grid-cols-2" style="margin-bottom:16px;">
        <div><strong>Asset ID:</strong> ${escapeHtml(a.asset_code)}</div>
        <div><strong>Status:</strong> ${statusBadge(a.status)}</div>
        <div><strong>Name:</strong> ${escapeHtml(a.name)}</div>
        <div><strong>Category:</strong> ${escapeHtml(a.category_name || '-')}</div>
        <div><strong>Brand/Model:</strong> ${escapeHtml(a.brand || '-')} / ${escapeHtml(a.model || '-')}</div>
        <div><strong>Serial No.:</strong> ${escapeHtml(a.serial_number || '-')}</div>
        <div><strong>Department:</strong> ${escapeHtml(a.department_name || '-')}</div>
        <div><strong>Location:</strong> ${escapeHtml(a.location || '-')}</div>
        <div><strong>Assigned To:</strong> ${escapeHtml(a.assigned_employee_name || '-')}</div>
        <div><strong>Condition:</strong> ${escapeHtml(a.condition_status)}</div>
        <div><strong>Purchase Date:</strong> ${formatDate(a.purchase_date)}</div>
        <div><strong>Purchase Cost:</strong> ${formatMoney(a.purchase_cost)}</div>
        <div><strong>Current Value:</strong> ${formatMoney(a.current_value)}</div>
        <div><strong>Warranty:</strong> ${formatDate(a.warranty_start)} → ${formatDate(a.warranty_end)}</div>
      </div>
      <p>${escapeHtml(a.description || '')}</p>

      <h4>Maintenance History</h4>
      ${listOrEmpty(res.maintenance, m => `${escapeHtml(m.maintenance_type || 'Maintenance')} — ${statusBadge(m.status)} (${formatDate(m.start_date)})`)}

      <h4 style="margin-top:16px;">Assignment History</h4>
      ${listOrEmpty(res.assignments, x => `${escapeHtml(x.employee_name)} — assigned ${formatDate(x.assigned_date)} ${x.is_active ? '(current)' : ''}`)}

      <h4 style="margin-top:16px;">Request History</h4>
      ${listOrEmpty(res.requests, r => `Request #${r.id} — ${statusBadge(r.status)}`)}
    `;
  } catch (e) {
    body.innerHTML = `Error: ${escapeHtml(e.message)}`;
  }
}
function listOrEmpty(items, renderer) {
  if (!items || !items.length) return `<div class="empty-state" style="padding:16px;">No records found.</div>`;
  return `<ul>${items.map(i => `<li>${renderer(i)}</li>`).join('')}</ul>`;
}

// ---------------- Export ----------------
function exportAssets(fmt) {
  const params = currentFilters();
  downloadFile(`/api/assets/export/${fmt}?` + buildQuery(params));
}
