document.addEventListener('DOMContentLoaded', () => {
  loadAssets();
  loadMaintenanceRequests();
});

async function loadAssets() {
  const res = await apiGet('/api/my-assigned-assets');

  document.getElementById('mr_asset_id').innerHTML =
    res.data.map(a => `
      <option value="${a.id}">
        ${escapeHtml(a.asset_code)} - ${escapeHtml(a.name)}
      </option>
    `).join('');
}

async function loadMaintenanceRequests() {
  const res = await apiGet('/api/my-maintenance');

  const tbody = document.getElementById('myMaintenanceBody');

  if (!res.data.length) {
    tbody.innerHTML =
      `<tr><td colspan="5">No maintenance requests.</td></tr>`;
    return;
  }

  tbody.innerHTML = res.data.map(r => `
    <tr>
      <td>${escapeHtml(r.asset_code)} - ${escapeHtml(r.asset_name)}</td>
      <td>${escapeHtml(r.problem)}</td>
      <td>${escapeHtml(r.description || '-')}</td>
      <td>${statusBadge(r.status)}</td>
      <td>${escapeHtml(r.admin_comment || '-')}</td>
    </tr>
  `).join('');
}

async function submitMaintenanceRequest() {
  const payload = {
    asset_id: document.getElementById('mr_asset_id').value,
    problem: document.getElementById('mr_problem').value.trim(),
    description:
      document.getElementById('mr_description').value.trim()
  };

  if (!payload.problem) {
    showToast('Please enter the problem.', 'error');
    return;
  }

  try {
    await apiPost('/api/my-maintenance', payload);

    showToast(
      'Maintenance request submitted.',
      'success'
    );

    closeModal('maintenanceRequestModal');

    loadMaintenanceRequests();

  } catch (e) {
    showToast(e.message, 'error');
  }
}