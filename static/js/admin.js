let permTargetId = null;

document.addEventListener('DOMContentLoaded', loadAdmins);

async function loadAdmins() {
  const tbody = document.getElementById('adminsBody');
  try {
    const res = await apiGet('/api/admin/admins');
    if (!res.data.length) { tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state">No administrators found.</div></td></tr>`; return; }
    tbody.innerHTML = res.data.map(a => `
      <tr>
        <td data-label="Name">${escapeHtml(a.full_name)}</td>
        <td data-label="Username">${escapeHtml(a.username)}</td>
        <td data-label="Email">${escapeHtml(a.email)}</td>
        <td data-label="Role">${escapeHtml(a.role_name.replace('_',' '))}</td>
        <td data-label="Status">${statusBadge(a.is_active ? 'ACTIVE' : 'INACTIVE')}</td>
        <td data-label="Actions" style="display:flex; gap:6px; flex-wrap:wrap;">
          ${a.role_name !== 'SUPER_ADMIN' ? `<button class="btn btn-sm btn-outline" onclick="toggleStatus(${a.id}, ${a.is_active ? 0 : 1})">${a.is_active ? 'Deactivate' : 'Activate'}</button>` : ''}
          <button class="btn btn-sm btn-outline" onclick="openPermissions(${a.id})">Permissions</button>
          <button class="btn btn-sm btn-outline" onclick="viewAdminActivity(${a.id})">Activity</button>
        </td>
      </tr>`).join('');
  } catch (e) { tbody.innerHTML = `<tr><td colspan="6">Error: ${escapeHtml(e.message)}</td></tr>`; }
}

function openAdminForm() {
  ['af_full_name', 'af_username', 'af_email', 'af_phone', 'af_password'].forEach(id => document.getElementById(id).value = '');
  openModal('adminFormModal');
}

async function submitAdminForm() {
  const payload = {
    full_name: document.getElementById('af_full_name').value,
    username: document.getElementById('af_username').value,
    email: document.getElementById('af_email').value,
    phone: document.getElementById('af_phone').value,
    password: document.getElementById('af_password').value,
  };
  if (!payload.full_name || !payload.username || !payload.email || !payload.password) { showToast('Please fill all required fields.', 'error'); return; }
  if (payload.password.length < 8) { showToast('Password must be at least 8 characters.', 'error'); return; }
  try {
    await apiPost('/api/admin/admins', payload);
    showToast('Administrator created successfully.', 'success');
    closeModal('adminFormModal');
    loadAdmins();
  } catch (e) { showToast(e.message, 'error'); }
}

async function toggleStatus(id, newStatus) {
  try {
    await apiPost(`/api/admin/admins/${id}/status`, { is_active: newStatus });
    showToast('Administrator status updated.', 'success');
    loadAdmins();
  } catch (e) { showToast(e.message, 'error'); }
}

async function openPermissions(id) {
  permTargetId = id;
  openModal('permissionsModal');
  const body = document.getElementById('permissionsBody');
  body.innerHTML = 'Loading...';
  try {
    const res = await apiGet(`/api/admin/admins/${id}/permissions`);
    body.innerHTML = res.all.map(p => `
      <label class="checkbox-row" style="margin-bottom:10px;">
        <input type="checkbox" value="${p.code}" ${res.granted.includes(p.code) ? 'checked' : ''} class="perm-checkbox">
        ${escapeHtml(p.label)}
      </label>`).join('');
  } catch (e) { body.innerHTML = `Error: ${escapeHtml(e.message)}`; }
}

async function savePermissions() {
  const checked = Array.from(document.querySelectorAll('.perm-checkbox:checked')).map(c => c.value);
  try {
    await apiPost(`/api/admin/admins/${permTargetId}/permissions`, { permissions: checked });
    showToast('Permissions updated successfully.', 'success');
    closeModal('permissionsModal');
    loadAdmins();
  } catch (e) { showToast(e.message, 'error'); }
}

async function viewAdminActivity(id) {
  openModal('adminActivityModal');
  const tbody = document.getElementById('adminActivityBody');
  tbody.innerHTML = `<tr><td colspan="4"><div class="skeleton"></div></td></tr>`;
  try {
    const res = await apiGet(`/api/admin/admins/${id}/activity`);
    if (!res.data.length) { tbody.innerHTML = `<tr><td colspan="4"><div class="empty-state">No activity recorded.</div></td></tr>`; return; }
    tbody.innerHTML = res.data.map(a => `
      <tr><td data-label="Action">${escapeHtml(a.action)}</td><td data-label="Module">${escapeHtml(a.module || '-')}</td><td data-label="Description">${escapeHtml(a.description || '-')}</td><td data-label="Timestamp">${formatDate(a.created_at)}</td></tr>`).join('');
  } catch (e) { tbody.innerHTML = `<tr><td colspan="4">Error: ${escapeHtml(e.message)}</td></tr>`; }
}
