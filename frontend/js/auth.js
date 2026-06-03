export function getToken() {
  return localStorage.getItem('access_token');
}

export function setToken(token) {
  localStorage.setItem('access_token', token);
}

export function getUsername() {
  return localStorage.getItem('username') || '';
}

export function setUsername(username) {
  localStorage.setItem('username', username);
}

export function getUserId() {
  const token = getToken();
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.sub;
  } catch {
    return null;
  }
}

export function isAuthenticated() {
  return !!getToken();
}

export function logout() {
  localStorage.clear();
  window.location.href = '/login';
}

export function requireAuth() {
  if (!isAuthenticated()) {
    window.location.href = '/login';
  }
}
