document.addEventListener('DOMContentLoaded', () => {
  const insightContainer = document.getElementById('aiInsightsList');

  if (insightContainer) {
    loadAiInsights();
  }
  document.getElementById('aiChatForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('aiChatInput');
    const q = input.value.trim();
    if (!q) return;
    appendChat(q, 'user');
    input.value = '';
    try {
      const res = await apiPost('/api/ai/ask', { question: q });
      appendChat(res.answer, 'bot');
    } catch (err) {
      appendChat('Sorry, something went wrong: ' + err.message, 'bot');
    }
  });
});

function appendChat(text, who) {
  const body = document.getElementById('aiChatBody');
  const el = document.createElement('div');
  el.className = `ai-msg ai-msg-${who}`;
  el.textContent = text;
  body.appendChild(el);
  body.scrollTop = body.scrollHeight;
}

async function loadAiInsights() {
  const container = document.getElementById('aiInsightsList');
  try {
    const res = await apiGet('/api/ai/insights');
    if (!res.insights.length) { container.innerHTML = `<div class="empty-state">No notable insights right now.</div>`; return; }
    container.innerHTML = res.insights.map(i => `
      <div class="insight-card" style="margin-bottom:10px;">
        <div>
          <strong>${escapeHtml(i.text)}</strong>
          ${i.items && i.items.length ? `<div style="font-size:12.5px; color:var(--text-muted); margin-top:4px;">${i.items.map(escapeHtml).join(', ')}</div>` : ''}
        </div>
      </div>`).join('') + `<div class="form-hint" style="margin-top:10px;">${escapeHtml(res.note)}</div>`;
  } catch (e) { container.innerHTML = `Error: ${escapeHtml(e.message)}`; }
}
