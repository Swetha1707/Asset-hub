document.addEventListener('DOMContentLoaded', () => {
  loadAssignedAssets();
  loadReturnRequests();
});

async function loadAssignedAssets() {
  const res = await apiGet('/api/my-assigned-assets');

  const select = document.getElementById('rr_asset_id');

  select.innerHTML = res.data.map(a =>
    `<option value="${a.id}">
      ${escapeHtml(a.asset_code)} - ${escapeHtml(a.name)}
    </option>`
  ).join('');
}

async function loadReturnRequests() {
  const res = await apiGet('/api/return-requests');

  const tbody = document.getElementById('returnRequestsBody');

  if (!res.data.length) {
    tbody.innerHTML =
      `<tr><td colspan="5">No return requests.</td></tr>`;
    return;
  }

  tbody.innerHTML = res.data.map(r => `
    <tr>
      <td>${escapeHtml(r.asset_code)} - ${escapeHtml(r.asset_name)}</td>
      <td>${escapeHtml(r.reason || '-')}</td>
      <td>${statusBadge(r.status)}</td>
      <td>${escapeHtml(r.admin_comment || '-')}</td>
      <td>${formatDate(r.created_at)}</td>
    </tr>
  `).join('');
}

async function submitReturnRequest() {
  const payload = {
    asset_id: document.getElementById('rr_asset_id').value,
    reason: document.getElementById('rr_reason').value.trim()
  };

  if (!payload.reason) {
    showToast('Please enter a reason.', 'error');
    return;
  }

  try {
    await apiPost('/api/return-requests', payload);

    showToast('Return request submitted.', 'success');

    closeModal('returnRequestModal');

    document.getElementById('rr_reason').value = '';

    loadReturnRequests();

  } catch (e) {
    showToast(e.message, 'error');
  }
}