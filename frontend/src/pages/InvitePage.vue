<template>
  <main class="page login-page">
    <div class="login-container">
      <header class="login-header">
        <h1>CrowdRoom</h1>
        <p class="text-secondary">You've been invited!</p>
      </header>

      <div v-if="loading" class="empty-state">
        <p>Loading invite...</p>
      </div>

      <div v-else-if="error" class="error-text">{{ error }}</div>

      <div v-else-if="isAuthenticated && preview" class="card">
        <h3>{{ preview.room_name }}</h3>
        <p class="text-secondary">{{ preview.is_private ? 'Private room' : 'Public room' }}</p>
        <button
          class="btn btn-primary btn-full"
          style="margin-top: var(--space-4)"
          @click="joinInvite"
        >
          Join Room
        </button>
      </div>

      <div v-else-if="!isAuthenticated && preview">
        <p class="text-secondary" style="margin-bottom: var(--space-4)">
          Login first to join this room.
        </p>
        <form class="login-form" @submit.prevent="loginAndJoin">
          <input
            v-model="inviteUsername"
            type="text"
            class="input"
            placeholder="Pick a username"
            maxlength="32"
            autocomplete="off"
            required
          />
          <button type="submit" class="btn btn-primary btn-full">Enter & Join</button>
        </form>
      </div>
    </div>

    <ThemeToggle class="theme-toggle" />
  </main>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { apiGet, apiPost } from '../composables/useApi.js';
import { useAuth } from '../composables/useAuth.js';
import ThemeToggle from '../components/ThemeToggle.vue';

const route = useRoute();
const router = useRouter();
const { isAuthenticated, setToken, setUsername, setHasPassword } = useAuth();

const loading = ref(true);
const error = ref('');
const preview = ref(null);
const inviteUsername = ref('');
let inviteToken = '';

onMounted(async () => {
  inviteToken = route.query.token || new URLSearchParams(window.location.search).get('token');
  if (!inviteToken) {
    error.value = 'Invalid invite link';
    loading.value = false;
    return;
  }

  try {
    preview.value = await apiGet(`/rooms/invite/${inviteToken}`);
  } catch (err) {
    error.value = err.detail || 'Invite link is invalid or expired';
  } finally {
    loading.value = false;
  }
});

async function joinInvite() {
  try {
    const result = await apiPost(`/rooms/invite/${inviteToken}/join`);
    router.push(`/room/${result.room_id}`);
  } catch (err) {
    error.value = err.detail || 'Failed to join';
  }
}

async function loginAndJoin() {
  const name = inviteUsername.value.trim();
  if (!name) return;
  try {
    const loginResult = await apiPost('/auth/local-login', { username: name });
    setToken(loginResult.access_token);
    setUsername(name);
    setHasPassword(false);
    const joinResult = await apiPost(`/rooms/invite/${inviteToken}/join`);
    router.push(`/room/${joinResult.room_id}`);
  } catch (err) {
    error.value = err.detail || 'Failed to join';
  }
}
</script>
