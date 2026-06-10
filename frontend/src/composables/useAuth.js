import { ref, computed } from 'vue';

const API_BASE = '/api/v1';

// In-memory auth state. The access token lives in an httpOnly cookie that JS
// cannot read (XSS-resistant); identity is derived from GET /auth/me instead.
const user = ref(null);
const ready = ref(false);

export function clearAuth() {
  user.value = null;
}

/**
 * Fetch the current user from the backend using the httpOnly auth cookie.
 *
 * Uses a raw fetch (not the shared apiRequest) so a 401 during bootstrap does
 * not trigger a redirect — an unauthenticated visitor is a valid state here.
 *
 * @returns {Promise<object|null>} The user object, or null if not authenticated.
 */
export async function fetchMe() {
  try {
    const response = await fetch(`${API_BASE}/auth/me`, {
      credentials: 'include',
    });
    if (response.ok) {
      user.value = await response.json();
    } else {
      user.value = null;
    }
  } catch {
    user.value = null;
  } finally {
    ready.value = true;
  }
  return user.value;
}

export function useAuth() {
  const isAuthenticated = computed(() => !!user.value);
  const username = computed(() => user.value?.username || '');
  const hasPassword = computed(() => !!user.value?.has_password);
  const userId = computed(() => user.value?.id || null);
  const avatarUrl = computed(() => user.value?.avatar_url || null);

  function setHasPassword(value) {
    if (user.value) {
      user.value.has_password = value;
    }
  }

  function setAvatarUrl(value) {
    if (user.value) {
      user.value.avatar_url = value;
    }
  }

  async function logout() {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch {
      // ignore — clear local state regardless
    }
    clearAuth();
  }

  return {
    user,
    ready,
    isAuthenticated,
    username,
    hasPassword,
    userId,
    avatarUrl,
    fetchMe,
    setHasPassword,
    setAvatarUrl,
    logout,
  };
}
