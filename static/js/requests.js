let statusFilter = '';

document.addEventListener('DOMContentLoaded', loadRequests);

function filterStatus(status, btn) {
  statusFilter = status;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  loadRequests();
}

async function loadRequests() {
  const tbody = document.getElementById('requestsBody');
  tbody.innerHTML = `<tr><td colspan="7"><div class="skeleton"></div></td></tr>`;
  try {
    const q = statusFilter ? `?status=${statusFilter}` : '';
    const res = await apiGet('/api/requests' + q);
    if (!res.data.length) { tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="icon">📝</div>No requests found.</div></td></tr>`; return; }
    const isEmployee = window.CURRENT_ROLE === 'EMPLOYEE';
   tbody.innerHTML = res.data.map(r => `
  <tr>

    ${isEmployee ? '' :
      `<td data-label="Requested By">
        ${escapeHtml(r.employee_name)}
      </td>`
    }

    <td data-label="Category">
      ${escapeHtml(r.category_name || '-')}
    </td>

    <td data-label="Reason">
      ${escapeHtml(r.reason || '-')}
    </td>

    <td data-label="Required Date">
      ${formatDate(r.required_date)}
    </td>

    <td data-label="Status">
      ${statusBadge(r.status)}
    </td>

    <td data-label="Assigned Asset">
      ${escapeHtml(r.assigned_asset_code || '-')}
    </td>

    <td data-label="Admin Response">
      ${escapeHtml(r.admin_comment || '-')}
    </td>

    ${isEmployee ? '' : `
      <td data-label="Actions">
        ${r.status === 'PENDING' ? `
          <button class="btn btn-sm btn-success"
                  onclick="openDecision(${r.id}, 'APPROVED', ${r.category_id})">
            Approve
          </button>

          <button class="btn btn-sm btn-danger"
                  onclick="openDecision(${r.id}, 'REJECTED', null)">
            Reject
          </button>
        ` : '-'}
      </td>
    `}

  </tr>
`).join('');
  } catch (e) { tbody.innerHTML = `<tr><td colspan="7">Error: ${escapeHtml(e.message)}</td></tr>`; }
}

function openRequestForm() { openModal('requestFormModal'); }

async function submitRequestForm() {
  const payload = {
    category_id: document.getElementById('rf_category_id').value,
    reason: document.getElementById('rf_reason').value,
    required_date: document.getElementById('rf_required_date').value,
  };
  if (!payload.reason) { showToast('Please provide a reason for the request.', 'error'); return; }
  try {
    await apiPost('/api/requests', payload);
    showToast('Request submitted successfully.', 'success');
    closeModal('requestFormModal');
    loadRequests();
  } catch (e) { showToast(e.message, 'error'); }
}

async function openDecision(reqId, decision, categoryId) {
  document.getElementById('decisionReqId').value = reqId;
  document.getElementById('decisionType').value = decision;
  document.getElementById('decisionTitle').textContent = decision === 'APPROVED' ? 'Approve Request' : 'Reject Request';
  document.getElementById('decisionComment').value = '';
  const assetGroup = document.getElementById('assetSelectGroup');
  const assetSelect = document.getElementById('decisionAssetId');
  if (decision === 'APPROVED' && categoryId) {
    assetGroup.style.display = 'block';
    assetSelect.innerHTML = '<option>Loading...</option>';
    try {
      const res = await apiGet(`/api/requests/available-assets/${categoryId}`);
      if (!res.data.length) {
        assetSelect.innerHTML = '<option value="">No available assets in this category</option>';
      } else {
        assetSelect.innerHTML = res.data.map(a => `<option value="${a.id}">${escapeHtml(a.asset_code)} - ${escapeHtml(a.name)}</option>`).join('');
      }
    } catch (e) { assetSelect.innerHTML = '<option value="">Error loading assets</option>'; }
  } else {
    assetGroup.style.display = 'none';
  }
  openModal('decisionModal');
}

async function submitDecision() {
  const reqId = document.getElementById('decisionReqId').value;
  const decision = document.getElementById('decisionType').value;
  const payload = {
    decision,
    assigned_asset_id: decision === 'APPROVED' ? (document.getElementById('decisionAssetId').value || null) : null,
    comment: document.getElementById('decisionComment').value,
  };
  try {
    await apiPost(`/api/requests/${reqId}/decision`, payload);
    showToast(`Request ${decision.toLowerCase()} successfully.`, 'success');
    closeModal('decisionModal');
    loadRequests();
  } catch (e) { showToast(e.message, 'error'); }
}
