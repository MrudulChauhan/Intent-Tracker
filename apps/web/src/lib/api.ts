const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function fetchApi(path: string, opts?: RequestInit) {
  const res = await fetch(`${API}${path}`, { ...opts, cache: 'no-store' });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

export const api = {
  stats: () => fetchApi('/api/stats'),
  projects: (p?: Record<string, string>) =>
    fetchApi('/api/projects' + (p ? '?' + new URLSearchParams(p) : '')),
  project: (id: number) => fetchApi(`/api/projects/${id}`),
  mentions: (p?: Record<string, string>) =>
    fetchApi('/api/mentions' + (p ? '?' + new URLSearchParams(p) : '')),
  mentionStats: () => fetchApi('/api/mentions/stats'),
  github: () => fetchApi('/api/github'),
  discoveries: (p?: Record<string, string>) =>
    fetchApi('/api/discoveries' + (p ? '?' + new URLSearchParams(p) : '')),
  reviewDiscovery: (id: number) =>
    fetch(`${API}/api/discoveries/${id}/review`, { method: 'POST' }),
  solvers: (p?: Record<string, string>) =>
    fetchApi('/api/solvers' + (p ? '?' + new URLSearchParams(p) : '')),
  scanLog: () => fetchApi('/api/scan-log'),
  scan: () => fetch(`${API}/api/scan`, { method: 'POST' }),
};
