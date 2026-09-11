const CHART_COLORS = ['#4f46e5', '#0891b2', '#16a34a', '#d97706', '#dc2626', '#7c3aed', '#db2777', '#0d9488'];

document.addEventListener('DOMContentLoaded', loadDashboard);

async function loadDashboard() {
  try {
    const res = await apiGet('/api/dashboard/summary');
    renderCards(res.cards);
    renderInsights(res.insights);
    renderCharts(res.charts);
  } catch (e) {
    showToast('Failed to load dashboard: ' + e.message, 'error');
  }
}

function renderCards(cards) {
  const items = [
    { label: 'Total Assets', value: cards.total_assets, icon: '💻' },
    { label: 'Assigned', value: cards.assigned, icon: '👤' },
    { label: 'Available', value: cards.available, icon: '✅' },
    { label: 'Under Maintenance', value: cards.maintenance, icon: '🔧' },
    { label: 'Total Value', value: formatMoney(cards.total_value), icon: '💰' },
    { label: 'Total Employees', value: cards.total_employees, icon: '👥' },
    { label: 'Pending Requests', value: cards.pending_requests, icon: '📝' },
    { label: 'Active Licenses', value: cards.active_licenses, icon: '🔑' },
    { label: 'Expiring Licenses', value: cards.expiring_licenses, icon: '⚠️' },
    { label: 'Retired Assets', value: cards.retired, icon: '📦' },
  ];
  const container = document.getElementById('statCards');
  container.innerHTML = items.slice(0, 5).map(cardHtml).join('');
  // second row for remaining stats
  const row2 = document.createElement('div');
  row2.className = 'grid grid-cols-5';
  row2.style.marginTop = '18px';
  row2.innerHTML = items.slice(5).map(cardHtml).join('');
  container.after(row2);
}
function cardHtml(item) {
  return `<div class="card stat-card"><div class="stat-icon">${item.icon}</div><div class="stat-label">${item.label}</div><div class="stat-value">${item.value}</div></div>`;
}

function renderInsights(insights) {
  const container = document.getElementById('insightCards');
  if (!container) return;
  if (!insights.length) {
    container.innerHTML = `<div class="empty-state"><div class="icon">✨</div>No notable insights right now — everything looks healthy.</div>`;
    return;
  }
  container.innerHTML = insights.map(i => `
    <div class="insight-card">
      <div class="insight-icon">${i.icon}</div>
      <div>${escapeHtml(i.text)}</div>
    </div>`).join('');
}

function renderCharts(charts) {
  makeDoughnut('chartByCategory', charts.by_category);
  makeBar('chartByDepartment', charts.by_department);
  makeDoughnut('chartByStatus', charts.by_status);
  makeBar('chartValueByDept', charts.value_by_department);
  makeBar('chartMaintenance', charts.maintenance_overview);
  makeLine('chartRequests', charts.monthly_requests);
}

function makeDoughnut(id, rows) {
  if (!rows || !rows.length) return;
  new Chart(document.getElementById(id), {
    type: 'doughnut',
    data: {
      labels: rows.map(r => r.label),
      datasets: [{ data: rows.map(r => r.value), backgroundColor: CHART_COLORS }]
    },
    options: { plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 11 } } } }, responsive: true }
  });
}
function makeBar(id, rows) {
  if (!rows || !rows.length) return;
  new Chart(document.getElementById(id), {
    type: 'bar',
    data: {
      labels: rows.map(r => r.label),
      datasets: [{ data: rows.map(r => r.value), backgroundColor: CHART_COLORS[0], borderRadius: 6 }]
    },
    options: { plugins: { legend: { display: false } }, responsive: true, scales: { y: { beginAtZero: true } } }
  });
}
function makeLine(id, rows) {
  if (!rows || !rows.length) return;
  new Chart(document.getElementById(id), {
    type: 'line',
    data: {
      labels: rows.map(r => r.label),
      datasets: [{ data: rows.map(r => r.value), borderColor: CHART_COLORS[2], backgroundColor: 'rgba(22,163,74,.15)', fill: true, tension: .35 }]
    },
    options: { plugins: { legend: { display: false } }, responsive: true, scales: { y: { beginAtZero: true } } }
  });
}
