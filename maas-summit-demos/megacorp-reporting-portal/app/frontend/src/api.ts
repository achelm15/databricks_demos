const API_BASE = '/api';

let sessionId: string | null = localStorage.getItem('session_id');

async function apiFetch(path: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };
  if (sessionId) {
    headers['X-Session-Id'] = sessionId;
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    localStorage.removeItem('session_id');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export const api = {
  // Auth
  login: async (email: string, tenantId: string) => {
    const data = await apiFetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, tenant_id: tenantId }),
    });
    sessionId = data.session_id;
    localStorage.setItem('session_id', data.session_id);
    return data;
  },

  getMe: () => apiFetch('/auth/me'),

  // Metrics
  getOverview: () => apiFetch('/metrics/overview'),
  getReachByDevice: () => apiFetch('/metrics/reach-by-device'),
  getReachByRegion: (campaign?: string) =>
    apiFetch(`/metrics/reach-by-region${campaign ? `?campaign=${campaign}` : ''}`),
  getFrequency: () => apiFetch('/metrics/frequency'),

  // Reports
  getReports: () => apiFetch('/reports'),
  saveReport: (report: { title: string; description?: string; query_text: string }) =>
    apiFetch('/reports', { method: 'POST', body: JSON.stringify(report) }),
  searchReports: (q: string) => apiFetch(`/reports/search?q=${encodeURIComponent(q)}`),

  // Genie
  askGenie: (question: string) =>
    apiFetch('/genie/ask', { method: 'POST', body: JSON.stringify({ question }) }),
  getGenieResult: (conversationId: string, messageId: string) =>
    apiFetch(`/genie/result/${conversationId}/${messageId}`),

  // Sandbox (Branching)
  createSandbox: () => apiFetch('/sandbox/create', { method: 'POST' }),
  deleteSandbox: (branchId: string) => apiFetch(`/sandbox/${branchId}`, { method: 'DELETE' }),

  // Features
  getFeatures: () => apiFetch('/features'),

  // Health
  health: () => apiFetch('/health'),
};

export default api;
