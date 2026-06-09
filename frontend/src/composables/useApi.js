import router from '../router/index.js';
import { clearAuth } from './useAuth.js';

const API_BASE = '/api/v1';

export async function apiRequest(method, path, body = null) {
  const headers = {};
  const tokenValue = localStorage.getItem('access_token');
  if (tokenValue) {
    headers['Authorization'] = `Bearer ${tokenValue}`;
  }

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
  });

  if (response.status === 401 && tokenValue) {
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
    throw error;
  }

  return data;
}

export const apiGet = (path) => apiRequest('GET', path);
export const apiPost = (path, body = {}) => apiRequest('POST', path, body);
export const apiPatch = (path, body = {}) => apiRequest('PATCH', path, body);
export const apiDelete = (path) => apiRequest('DELETE', path);
