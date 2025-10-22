export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8001"; // gateway

async function req(path: string, init?: RequestInit) {
  const r = await fetch(`${API_BASE}${path}`, { headers: { "Content-Type": "application/json" }, ...init });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export const API = {
  listCases: () => req("/cases"),
  getCase: (id: string) => req(`/cases/${id}`),
  assign: (id: string, user: string) => req(`/cases/${id}/assign?user=${encodeURIComponent(user)}`, { method: "PATCH" }),
  addNote: (id: string, text: string) => req(`/cases/${id}/notes`, { method: "POST", body: JSON.stringify({ text }) }),
  
  // Analytics endpoints
  getAnalytics: (hours: number = 24) => req(`/analytics?hours=${hours}`),
  getKPIs: (hours: number = 24) => req(`/analytics/kpis?hours=${hours}`),
  getTrends: (hours: number = 24) => req(`/analytics/trends?hours=${hours}`),
  getDistributions: (hours: number = 24) => req(`/analytics/distributions?hours=${hours}`),
};
