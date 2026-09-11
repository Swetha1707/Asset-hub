document.addEventListener('DOMContentLoaded', () => {
  loadEmployees();
  ['eSearch', 'eDepartment', 'eStatus'].forEach(id => {
    document.getElementById(id).addEventListener(id === 'eSearch' ? 'input' : 'change', debounce(loadEmployees, 300));
  });
});
function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }

function empFilters() {
  return { q: document.getElementById('eSearch').value, department_id: document.getElementById('eDepartment').value, status: document.getElementById('eStatus').value };
}
function buildQuery(params) { const q = new URLSearchParams(); Object.entries(params).forEach(([k, v]) => { if (v) q.set(k, v); }); return q.toString(); }

async function loadEmployees() {
  const tbody = document.getElementById('employeesTableBody');
  tbody.innerHTML = `<tr><td colspan="7"><div class="skeleton"></div></td></tr>`;
  try {
    const res = await apiGet('/api/employees?' + buildQuery(empFilters()));
    if (!res.data.length) { tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="icon">👥</div>No employees found.</div></td></tr>`; return; }
    tbody.innerHTML = res.data.map(e => `
      <tr>
        <td data-label="Employee ID"><a href="#" onclick="viewEmployee(${e.id}); return false;" style="color:var(--primary); font-weight:600;">${escapeHtml(e.employee_code)}</a></td>
        <td data-label="Name">${escapeHtml(e.name)}</td>
        <td data-label="Department">${escapeHtml(e.department_name || '-')}</td>
        <td data-label="Designation">${escapeHtml(e.designation || '-')}</td>
        <td data-label="Status">${statusBadge(e.status)}</td>
        <td data-label="Assets Held">${e.asset_count}</td>
        <td data-label="Actions">${hasPerm('MANAGE_EMPLOYEES') ? `<button class="btn btn-sm btn-outline" onclick="editEmployee(${e.id})">Edit</button>` : ''}</td>
      </tr>`).join('');
  } catch (e) { tbody.innerHTML = `<tr><td colspan="7">Error: ${escapeHtml(e.message)}</td></tr>`; }
}
function hasPerm(code) { return document.body.dataset.perms && document.body.dataset.perms.includes(code); }

function openEmployeeForm(emp = null) {
  document.getElementById('employeeId').value = '';
  document.getElementById('empFormTitle').textContent = emp ? 'Edit Employee' : 'Add Employee';
  ['ef_employee_code', 'ef_name', 'ef_email', 'ef_phone', 'ef_designation', 'ef_joining_date'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('ef_department_id').value = '';
  document.getElementById('ef_status').value = 'ACTIVE';
  if (emp) {
    document.getElementById('employeeId').value = emp.id;
    document.getElementById('ef_employee_code').value = emp.employee_code;
    document.getElementById('ef_employee_code').disabled = true;
    document.getElementById('ef_name').value = emp.name;
    document.getElementById('ef_email').value = emp.email;
    document.getElementById('ef_phone').value = emp.phone || '';
    document.getElementById('ef_department_id').value = emp.department_id || '';
    document.getElementById('ef_designation').value = emp.designation || '';
    document.getElementById('ef_joining_date').value = emp.joining_date || '';
    document.getElementById('ef_status').value = emp.status;
  } else {
    document.getElementById('ef_employee_code').disabled = false;
  }
  openModal('employeeFormModal');
}

async function editEmployee(id) {
  const res = await apiGet(`/api/employees/${id}`);
  openEmployeeForm(res.employee);
}

async function submitEmployeeForm() {
  const id = document.getElementById('employeeId').value;
  const payload = {
    employee_code: document.getElementById('ef_employee_code').value,
    name: document.getElementById('ef_name').value,
    email: document.getElementById('ef_email').value,
    phone: document.getElementById('ef_phone').value,
    department_id: document.getElementById('ef_department_id').value,
    designation: document.getElementById('ef_designation').value,
    joining_date: document.getElementById('ef_joining_date').value,
    status: document.getElementById('ef_status').value,
  };
  if (!payload.employee_code || !payload.name || !payload.email) { showToast('Employee ID, Name and Email are required.', 'error'); return; }
  try {
    if (id) { await apiPut(`/api/employees/${id}`, payload); showToast('Employee updated successfully.', 'success'); }
    else { await apiPost('/api/employees', payload); showToast('Employee added successfully.', 'success'); }
    closeModal('employeeFormModal');
    loadEmployees();
  } catch (e) { showToast(e.message, 'error'); }
}

async function viewEmployee(id) {
  openModal('employeeDetailsModal');
  const body = document.getElementById('employeeDetailsBody');
  body.innerHTML = 'Loading...';
  try {
    const res = await apiGet(`/api/employees/${id}`);
    const emp = res.employee;
    body.innerHTML = `
      <div class="grid grid-cols-2" style="margin-bottom:16px;">
        <div><strong>Employee ID:</strong> ${escapeHtml(emp.employee_code)}</div>
        <div><strong>Status:</strong> ${statusBadge(emp.status)}</div>
        <div><strong>Name:</strong> ${escapeHtml(emp.name)}</div>
        <div><strong>Department:</strong> ${escapeHtml(emp.department_name || '-')}</div>
        <div><strong>Email:</strong> ${escapeHtml(emp.email)}</div>
        <div><strong>Designation:</strong> ${escapeHtml(emp.designation || '-')}</div>
        <div><strong>Phone:</strong> ${escapeHtml(emp.phone || '-')}</div>
        <div><strong>Joined:</strong> ${formatDate(emp.joining_date)}</div>
      </div>
      <h4>Current Assets</h4>
      ${res.current_assets.length ? `<ul>${res.current_assets.map(a => `<li>${escapeHtml(a.asset_code)} — ${escapeHtml(a.name)} ${statusBadge(a.status)}</li>`).join('')}</ul>` : `<div class="empty-state" style="padding:16px;">No assets currently assigned.</div>`}
      <h4 style="margin-top:16px;">Asset History</h4>
      ${res.history.length ? `<ul>${res.history.map(h => `<li>${escapeHtml(h.asset_code)} — assigned ${formatDate(h.assigned_date)}</li>`).join('')}</ul>` : `<div class="empty-state" style="padding:16px;">No history.</div>`}
      <h4 style="margin-top:16px;">Requests</h4>
      ${res.requests.length ? `<ul>${res.requests.map(r => `<li>Request #${r.id} — ${statusBadge(r.status)}</li>`).join('')}</ul>` : `<div class="empty-state" style="padding:16px;">No requests.</div>`}
    `;
  } catch (e) { body.innerHTML = `Error: ${escapeHtml(e.message)}`; }
}

function exportEmployees(fmt) { downloadFile(`/api/employees/export/${fmt}?` + buildQuery(empFilters())); }
