<template>
  <main class="page login-page">
    <div class="login-container">
      <header class="login-header">
        <h1>Complete Your Profile</h1>
        <p class="text-secondary">An email and password are now required to continue.</p>
      </header>

      <form class="login-form" @submit.prevent="submit">
        <div class="input-group">
          <label for="email">Email</label>
          <input id="email" v-model="email" type="email" class="input" placeholder="you@example.com" autocomplete="email" required>
        </div>
        <div class="input-group">
          <label for="password">Password</label>
          <input id="password" v-model="password" type="password" class="input" placeholder="Min 8 characters" minlength="8" autocomplete="new-password" required>
        </div>
        <div class="input-group">
          <label for="confirm-password">Confirm password</label>
          <input id="confirm-password" v-model="confirmPassword" type="password" class="input" placeholder="Repeat password" minlength="8" autocomplete="new-password" required>
        </div>
        <button type="submit" class="btn btn-primary btn-full" :disabled="loading">Save &amp; Continue</button>
      </form>

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
const { setHasPassword } = useAuth();

const email = ref('');
const password = ref('');
const confirmPassword = ref('');
const error = ref('');
const loading = ref(false);

onMounted(async () => {
  try {
    const me = await apiGet('/auth/me');
    if (me.profile_complete) {
      router.push('/rooms');
      return;
    }
    if (me.email) {
      email.value = me.email;
    }
  } catch {
    // If /me fails with 401, useApi redirects to /login
  }
});

async function submit() {
  error.value = '';

  if (password.value !== confirmPassword.value) {
    error.value = 'Passwords do not match';
    return;
  }

  loading.value = true;
  try {
    await apiPost('/auth/complete-profile', {
      email: email.value.trim(),
      password: password.value,
    });
    setHasPassword(true);
    router.push('/rooms');
  } catch (err) {
    error.value = err.detail || 'Failed to complete profile';
  } finally {
    loading.value = false;
  }
}
</script>
