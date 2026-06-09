import router from '../router/index.js';
import { clearAuth } from './useAuth.js';

const API_BASE = '/api/v1';

export async function apiRequest(method, path, body = null, options = {}) {
  const headers = {};

  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
  let payload;
  if (body === null) {
    payload = undefined;
  } else if (isFormData) {
    payload = body;
  } else {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: payload,
    credentials: 'include',
    signal: options.signal,
  });

  if (response.status === 401) {
    clearAuth();
    if (router.currentRoute.value.path !== '/login') {
      router.push('/login');
    }
    return;
  }

  if (response.status === 204) {
    return null;
  }

  const data = await response.json();

  if (!response.ok) {
    if (response.status === 403 && data.code === 'PROFILE_INCOMPLETE') {
      router.push('/complete-profile');
      return;
    }
    const error = new Error(data.detail || 'Request failed');
    error.status = response.status;
    error.detail = data.detail;
    error.code = data.code;
    error.retryAfter = data.retry_after;
    throw error;
  }

  return data;
}

export const apiGet = (path, options) => apiRequest('GET', path, null, options);
export const apiPost = (path, body = {}, options) => apiRequest('POST', path, body, options);
export const apiPatch = (path, body = {}, options) => apiRequest('PATCH', path, body, options);
export const apiDelete = (path, options) => apiRequest('DELETE', path, null, options);
