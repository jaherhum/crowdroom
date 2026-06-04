import { ref, computed } from 'vue';

const token = ref(localStorage.getItem('access_token'));
const username = ref(localStorage.getItem('username') || '');

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

  function logout() {
    token.value = null;
    username.value = '';
    localStorage.clear();
  }

  return {
    token,
    username,
    isAuthenticated,
    userId,
    setToken,
    setUsername,
    logout,
  };
}
