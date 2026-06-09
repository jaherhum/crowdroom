<template>
  <main class="page login-page">
    <div class="login-container">
      <header class="login-header">
        <h1>CrowdRoom</h1>
        <p class="text-secondary">Collaborative music, together.</p>
      </header>

      <form v-if="mode === 'LOCAL'" class="login-form" @submit.prevent="localLogin">
        <div class="input-group">
          <label for="username">Pick a username</label>
          <input id="username" v-model="localUsername" type="text" class="input" placeholder="your name" maxlength="32" autocomplete="off" required>
        </div>
        <div class="input-group">
          <label for="local-password">Password <span class="text-secondary">(optional, needed to create rooms)</span></label>
          <input id="local-password" v-model="localPassword" type="password" class="input" placeholder="leave blank to join as guest" minlength="6" autocomplete="current-password">
        </div>
        <button type="submit" class="btn btn-primary btn-full">Enter</button>
      </form>

      <div v-else>
        <div class="tab-switcher">
          <button type="button" :class="['tab', { active: activeTab === 'login' }]" @click="activeTab = 'login'">Login</button>
          <button type="button" :class="['tab', { active: activeTab === 'register' }]" @click="activeTab = 'register'">Register</button>
        </div>

        <form v-if="activeTab === 'login'" class="login-form" @submit.prevent="onlineLogin">
          <input v-model="identifier" type="text" class="input" placeholder="Username or email" autocomplete="username" required>
          <input v-model="password" type="password" class="input" placeholder="Password" autocomplete="current-password" required>
          <button type="submit" class="btn btn-primary btn-full">Login</button>
        </form>

        <form v-else class="login-form" @submit.prevent="onlineRegister">
          <input v-model="regUsername" type="text" class="input" placeholder="Username" maxlength="32" autocomplete="username" required>
          <input v-model="regEmail" type="email" class="input" placeholder="Email" autocomplete="email" required>
          <input v-model="regPassword" type="password" class="input" placeholder="Password (min 8 chars)" minlength="8" autocomplete="new-password" required>
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
import { useRouter } from 'vue-router';
import { apiGet, apiPost } from '../composables/useApi.js';
import { useAuth } from '../composables/useAuth.js';
import ThemeToggle from '../components/ThemeToggle.vue';

const router = useRouter();
const { setToken, setUsername, setHasPassword } = useAuth();

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

onMounted(async () => {
  try {
    const result = await apiGet('/auth/mode');
    mode.value = result.mode;
  } catch {
    mode.value = 'LOCAL';
  }
});

async function localLogin() {
  error.value = '';
  try {
    const body = { username: localUsername.value.trim() };
    if (localPassword.value) {
      body.password = localPassword.value;
    }
    const result = await apiPost('/auth/local-login', body);
    setToken(result.access_token);
    setUsername(localUsername.value.trim());
    const me = await apiGet('/auth/me');
    setHasPassword(me.has_password);
    router.push('/rooms');
  } catch (err) {
    error.value = err.detail || 'Login failed';
  }
}

async function onlineLogin() {
  error.value = '';
  try {
    const result = await apiPost('/auth/login', { identifier: identifier.value.trim(), password: password.value });
    setToken(result.access_token);
    setUsername(identifier.value.trim());
    const me = await apiGet('/auth/me');
    setHasPassword(me.has_password);
    router.push('/rooms');
  } catch (err) {
    error.value = err.detail || 'Invalid credentials';
  }
}

async function onlineRegister() {
  error.value = '';
  try {
    const result = await apiPost('/auth/register', { username: regUsername.value.trim(), email: regEmail.value.trim(), password: regPassword.value });
    setToken(result.access_token);
    setUsername(regUsername.value.trim());
    setHasPassword(true);
    router.push('/rooms');
  } catch (err) {
    error.value = err.detail || 'Registration failed';
  }
}
</script>
