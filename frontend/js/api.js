const API_BASE = '/api/v1';

async function request(method, path, body = null) {
  const headers = {};
  const token = localStorage.getItem('access_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (body !== null) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== null ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401) {
    localStorage.clear();
    window.location.href = '/login';
    return;
  }

  if (response.status === 204) {
    return null;
  }

  const data = await response.json();

  if (!response.ok) {
    const error = new Error(data.detail || 'Request failed');
    error.status = response.status;
    error.detail = data.detail;
    throw error;
  }

  return data;
}

export function apiGet(path) {
  return request('GET', path);
}

export function apiPost(path, body = {}) {
  return request('POST', path, body);
}

export function apiPatch(path, body = {}) {
  return request('PATCH', path, body);
}

export function apiDelete(path) {
  return request('DELETE', path);
}
