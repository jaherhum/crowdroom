import { useAuth } from './useAuth.js';
import { useRouter } from 'vue-router';

const API_BASE = '/api/v1';

export function useApi() {
  const { token } = useAuth();
  const router = useRouter();

  async function request(method, path, body = null) {
    const headers = {};
    if (token.value) {
      headers['Authorization'] = `Bearer ${token.value}`;
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
      router.push('/login');
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

  return {
    apiGet: (path) => request('GET', path),
    apiPost: (path, body = {}) => request('POST', path, body),
    apiPatch: (path, body = {}) => request('PATCH', path, body),
    apiDelete: (path) => request('DELETE', path),
  };
}

export async function apiRequest(method, path, body = null) {
  const headers = {};
  const tokenValue = localStorage.getItem('access_token');
  if (tokenValue) {
    headers['Authorization'] = `Bearer ${tokenValue}`;
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
    if (response.status === 403 && data.code === 'PROFILE_INCOMPLETE') {
      window.location.href = '/complete-profile';
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
