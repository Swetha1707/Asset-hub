async function previewReport(key, label) {
  document.getElementById('reportPreviewTitle').textContent = label;
  openModal('reportPreviewModal');
  const table = document.getElementById('reportPreviewTable');
  table.innerHTML = '<tr><td><div class="skeleton"></div></td></tr>';
  try {
    const res = await apiGet(`/api/reports/${key}`);
    if (!res.data.length) { table.innerHTML = `<tr><td><div class="empty-state">No data available for this report.</div></td></tr>`; return; }
    const head = `<thead><tr>${res.columns.map(c => `<th>${escapeHtml(c[1])}</th>`).join('')}</tr></thead>`;
    const body = `<tbody>${res.data.map(row => `<tr>${res.columns.map(c => `<td data-label="${escapeHtml(c[1])}">${escapeHtml(row[c[0]])}</td>`).join('')}</tr>`).join('')}</tbody>`;
    table.innerHTML = head + body;
  } catch (e) {
    table.innerHTML = `<tr><td>Error: ${escapeHtml(e.message)}</td></tr>`;
  }
}

function exportReport(key, fmt) {
  downloadFile(`/api/reports/${key}/export/${fmt}`);
}
