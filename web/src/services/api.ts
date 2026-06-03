const CC_BASE = '/api/cc';
const PIPELINE_BASE = '/api/pipeline';

export const api = {
  getSession: (sid: string) =>
    fetch(`${CC_BASE}/sessions/${sid}`).then((r) => r.json()),

  getStats: () =>
    fetch(`${CC_BASE}/admin/stats`).then((r) => r.json()),

  getAgents: () =>
    fetch(`${CC_BASE}/admin/agents`).then((r) => r.json()),

  askAI: (text: string) =>
    fetch(`${PIPELINE_BASE}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, type: 'text-query' }),
    }).then((r) => r.json()),
};
