<template>
  <main class="page login-page">
    <div class="login-container">
      <header class="login-header">
        <img :src="logoUrl" alt="CrowdRoom" class="login-logo" />
        <h1>CrowdRoom</h1>
        <p class="text-secondary">Collaborative music, together.</p>
      </header>

      <form v-if="mode === 'LOCAL'" class="login-form" @submit.prevent="localLogin">
        <div class="input-group">
          <label for="username">Pick a username</label>
          <input
            id="username"
            v-model="localUsername"
            type="text"
            class="input"
            placeholder="your name"
            maxlength="32"
            autocomplete="off"
            required
          />
        </div>
        <div class="input-group">
          <label for="local-password"
            >Password <span class="text-secondary">(optional, needed to create rooms)</span></label
          >
          <input
            id="local-password"
            v-model="localPassword"
            type="password"
            class="input"
            placeholder="leave blank to join as guest"
            minlength="6"
            autocomplete="current-password"
          />
        </div>
        <button type="submit" class="btn btn-primary btn-full">Enter</button>
      </form>

      <div v-else>
        <div class="tab-switcher">
          <button
            type="button"
            :class="['tab', { active: activeTab === 'login' }]"
            @click="activeTab = 'login'"
          >
            Login
          </button>
          <button
            type="button"
            :class="['tab', { active: activeTab === 'register' }]"
            @click="activeTab = 'register'"
          >
            Register
          </button>
        </div>

        <form v-if="activeTab === 'login'" class="login-form" @submit.prevent="onlineLogin">
          <input
            v-model="identifier"
            type="text"
            class="input"
            placeholder="Username or email"
            autocomplete="username"
            required
          />
          <input
            v-model="password"
            type="password"
            class="input"
            placeholder="Password"
            autocomplete="current-password"
            required
          />
          <button type="submit" class="btn btn-primary btn-full">Login</button>
        </form>

        <form v-else class="login-form" @submit.prevent="onlineRegister">
          <input
            v-model="regUsername"
            type="text"
            class="input"
            placeholder="Username"
            maxlength="32"
            autocomplete="username"
            required
          />
          <input
            v-model="regEmail"
            type="email"
            class="input"
            placeholder="Email"
            autocomplete="email"
            required
          />
          <input
            v-model="regPassword"
            type="password"
            class="input"
            placeholder="Password (min 8 chars)"
            minlength="8"
            autocomplete="new-password"
            required
          />
          <button type="submit" class="btn btn-primary btn-full">Register</button>
        </form>
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>
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
import logoUrl from '../assets/logo.svg';

const route = useRoute();
const router = useRouter();
const { fetchMe } = useAuth();

const mode = ref('LOCAL');
const activeTab = ref('login');
const error = ref('');

const localUsername = ref('');
const localPassword = ref('');
const identifier = ref('');
const password = ref('');
const regUsername = ref('');
const regEmail = ref('');
const regPassword = ref('');

const inviteToken = ref('');

onMounted(async () => {
  inviteToken.value = (route.query.invite || '').toString();
  try {
    const result = await apiGet('/auth/mode');
    mode.value = result.mode;
  } catch {
    mode.value = 'LOCAL';
  }
});

async function postAuthRedirect() {
  if (inviteToken.value) {
    try {
      const join = await apiPost(`/rooms/invite/${inviteToken.value}/join`);
      router.push(`/room/${join.room_id}`);
      return;
    } catch (err) {
      error.value = err.detail || 'Failed to join invite';
      return;
    }
  }
  router.push('/rooms');
}

async function localLogin() {
  error.value = '';
  try {
    const body = { username: localUsername.value.trim() };
    if (localPassword.value) {
      body.password = localPassword.value;
    }
    await apiPost('/auth/local-login', body);
    await fetchMe();
    await postAuthRedirect();
  } catch (err) {
    error.value = err.detail || 'Login failed';
  }
}

async function onlineLogin() {
  error.value = '';
  try {
    await apiPost('/auth/login', {
      identifier: identifier.value.trim(),
      password: password.value,
    });
    await fetchMe();
    await postAuthRedirect();
  } catch (err) {
    error.value = err.detail || 'Invalid credentials';
  }
}

async function onlineRegister() {
  error.value = '';
  try {
    await apiPost('/auth/register', {
      username: regUsername.value.trim(),
      email: regEmail.value.trim(),
      password: regPassword.value,
    });
    await fetchMe();
    await postAuthRedirect();
  } catch (err) {
    error.value = err.detail || 'Registration failed';
  }
}
</script>
