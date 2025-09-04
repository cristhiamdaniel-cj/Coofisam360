// Cliente ligero basado en fetch (sin axios)
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE || '';
const DEFAULT_TIMEOUT = 20000;

function withQuery(url, params) {
  if (!params) return url;
  const u = new URL(url, (typeof window !== 'undefined' ? window.location.origin : 'http://localhost'));
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') u.searchParams.set(k, v);
  });
  return u.toString();
}

async function request(method, path, { params, body, headers } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT);
  const base = BASE_URL || (typeof window !== 'undefined' ? '' : '');
  const url = withQuery(base + path, params);
  const h = { 'Content-Type': 'application/json', ...(headers || {}) };
  try {
    if (typeof window !== 'undefined') {
      const token = window.localStorage.getItem('authToken');
      if (token) h.Authorization = `Token ${token}`;
    }
  } catch (_) {}

  const res = await fetch(url, {
    method,
    headers: h,
    signal: controller.signal,
    body: method === 'GET' || method === 'HEAD' ? undefined : (body ? JSON.stringify(body) : undefined),
  });
  clearTimeout(timer);

  const isJson = (res.headers.get('content-type') || '').includes('application/json');
  const data = isJson ? await res.json().catch(() => undefined) : await res.text();
  if (!res.ok) {
    const message = (data && (data.error || data.message)) || res.statusText || 'API error';
    throw { status: res.status, message, data };
  }
  return { status: res.status, data };
}

const api = {
  get: (path, { params } = {}) => request('GET', path, { params }),
  post: (path, body) => request('POST', path, { body }),
  put: (path, body) => request('PUT', path, { body }),
  delete: (path, params) => request('DELETE', path, { params }),
};

export default api;
