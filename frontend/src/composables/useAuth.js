import { ref, computed } from 'vue';

const AUTH_KEYS = ['access_token', 'username', 'has_password'];

const token = ref(localStorage.getItem('access_token'));
const username = ref(localStorage.getItem('username') || '');
const hasPassword = ref(localStorage.getItem('has_password') === 'true');

export function clearAuth() {
  for (const key of AUTH_KEYS) {
    localStorage.removeItem(key);
  }
  token.value = null;
  username.value = '';
  hasPassword.value = false;
}

export function useAuth() {
  const isAuthenticated = computed(() => !!token.value);

  const userId = computed(() => {
    if (!token.value) return null;
    try {
      const payload = JSON.parse(atob(token.value.split('.')[1]));
      return payload.sub;
    } catch {
      return null;
    }
  });

  function setToken(newToken) {
    token.value = newToken;
    localStorage.setItem('access_token', newToken);
  }

  function setUsername(newUsername) {
    username.value = newUsername;
    localStorage.setItem('username', newUsername);
  }

  function setHasPassword(value) {
    hasPassword.value = value;
    localStorage.setItem('has_password', value ? 'true' : 'false');
  }

  function logout() {
    clearAuth();
  }

  return {
    token,
    username,
    hasPassword,
    isAuthenticated,
    userId,
    setToken,
    setUsername,
    setHasPassword,
    logout,
  };
}
