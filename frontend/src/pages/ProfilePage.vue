<template>
  <div class="page">
    <header class="app-header">
      <button class="btn btn-ghost" @click="router.push('/rooms')">
        <i class="ph ph-arrow-left"></i> Back
      </button>
      <h2>Profile</h2>
      <div class="header-actions">
        <ThemeToggle />
      </div>
    </header>

    <main class="container profile-container">
      <!-- Avatar & Username -->
      <section class="panel profile-header-panel">
        <div class="profile-avatar-section">
          <button
            type="button"
            class="profile-avatar-wrapper"
            aria-label="Change avatar"
            @click="$refs.avatarInput.click()"
          >
            <img v-if="avatarUrl" :src="avatarUrl" class="profile-avatar" alt="avatar" />
            <span v-else class="profile-avatar profile-avatar-fallback">{{
              (username || '?')[0].toUpperCase()
            }}</span>
            <div class="avatar-overlay"><i class="ph ph-camera"></i></div>
          </button>
          <input
            ref="avatarInput"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            hidden
            @change="uploadAvatar"
          />
        </div>
        <h2 class="profile-username">{{ username }}</h2>
      </section>

      <!-- Password Section -->
      <section class="panel">
        <h3><i class="ph ph-lock"></i> Password</h3>
        <form class="profile-form" @submit.prevent="changePassword">
          <div class="input-group">
            <label for="current-password">Current password</label>
            <input
              id="current-password"
              v-model="currentPassword"
              type="password"
              class="input"
              placeholder="Current password"
              required
            />
          </div>
          <div class="input-group">
            <label for="new-password">New password</label>
            <input
              id="new-password"
              v-model="newPassword"
              type="password"
              class="input"
              placeholder="Min 6 characters"
              minlength="6"
              required
            />
          </div>
          <div class="input-group">
            <label for="confirm-password">Confirm new password</label>
            <input
              id="confirm-password"
              v-model="confirmPassword"
              type="password"
              class="input"
              placeholder="Repeat password"
              minlength="6"
              required
            />
          </div>
          <p v-if="passwordError" class="error-text">{{ passwordError }}</p>
          <p v-if="passwordSuccess" class="success-text">{{ passwordSuccess }}</p>
          <button type="submit" class="btn btn-primary" :disabled="passwordLoading">
            Change Password
          </button>
        </form>
      </section>

      <!-- Streaming Connections -->
      <section class="panel">
        <h3><i class="ph ph-link"></i> Streaming Connections</h3>
        <div class="connections-list">
          <div class="connection-item">
            <div class="connection-info">
              <i class="ph ph-spotify-logo connection-icon"></i>
              <div>
                <strong>Spotify</strong>
                <p v-if="spotifyConnected" class="text-secondary connection-status connected">
                  Connected
                </p>
                <p v-else class="text-secondary connection-status">Not connected</p>
              </div>
            </div>
            <div class="connection-actions">
              <template v-if="spotifyConnected">
                <button
                  class="btn btn-secondary"
                  :disabled="spotifyLoading"
                  @click="connectSpotify"
                >
                  {{ spotifyLoading ? 'Connecting…' : 'Reconnect' }}
                </button>
                <button class="btn btn-ghost btn-danger" @click="disconnectSpotify">
                  Disconnect
                </button>
              </template>
              <template v-else-if="hasAppCredentials">
                <button class="btn btn-primary" :disabled="spotifyLoading" @click="connectSpotify">
                  {{ spotifyLoading ? 'Connecting…' : 'Connect' }}
                </button>
                <button class="btn btn-ghost" @click="showSpotifySetup = true">Change App</button>
              </template>
              <template v-else>
                <button class="btn btn-primary" @click="showSpotifySetup = true">Set up</button>
              </template>
            </div>
          </div>
        </div>
      </section>

      <!-- Spotify App Credentials Modal -->
      <div v-if="showSpotifySetup" class="modal-overlay" @click.self="showSpotifySetup = false">
        <div class="modal">
          <h3>Set up Spotify App</h3>
          <p class="text-secondary" style="margin-bottom: var(--space-4)">
            Create a Spotify Developer app at
            <a href="https://developer.spotify.com/dashboard" target="_blank"
              >developer.spotify.com</a
            >. Set the redirect URI to:
          </p>
          <code class="redirect-uri-display">{{ redirectUri }}</code>
          <form style="margin-top: var(--space-4)" @submit.prevent="saveSpotifyCredentials">
            <div class="input-group">
              <label for="spotify-client-id">Client ID</label>
              <input
                id="spotify-client-id"
                v-model="spotifyClientId"
                type="text"
                class="input"
                placeholder="Your Spotify Client ID"
                required
              />
            </div>
            <div class="input-group" style="margin-top: var(--space-3)">
              <label for="spotify-client-secret">Client Secret</label>
              <input
                id="spotify-client-secret"
                v-model="spotifyClientSecret"
                type="password"
                class="input"
                placeholder="Your Spotify Client Secret"
                required
              />
            </div>
            <div class="modal-actions" style="margin-top: var(--space-4)">
              <button type="button" class="btn btn-secondary" @click="showSpotifySetup = false">
                Cancel
              </button>
              <button type="submit" class="btn btn-primary" :disabled="spotifyLoading">
                {{ spotifyLoading ? 'Connecting…' : 'Save & Connect' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { apiGet, apiPost, apiDelete } from '../composables/useApi.js';
import { useAuth } from '../composables/useAuth.js';
import { useToast } from '../composables/useToast.js';
import ThemeToggle from '../components/ThemeToggle.vue';

const router = useRouter();
const { username, avatarUrl, setAvatarUrl } = useAuth();
const { showToast } = useToast();

const currentPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const passwordError = ref('');
const passwordSuccess = ref('');
const passwordLoading = ref(false);

const spotifyConnected = ref(false);
const hasAppCredentials = ref(false);
const showSpotifySetup = ref(false);
const spotifyClientId = ref('');
const spotifyClientSecret = ref('');
const spotifyLoading = ref(false);

const redirectUri = computed(() => window.location.origin + '/api/v1/auth/spotify/callback');

async function connectSpotify() {
  if (spotifyLoading.value) return;
  spotifyLoading.value = true;
  try {
    sessionStorage.setItem('spotify_return_page', '/profile');
    const { authorize_url } = await apiPost('/auth/spotify/start');
    if (authorize_url) {
      window.location.href = authorize_url;
    } else {
      spotifyLoading.value = false;
    }
  } catch (err) {
    spotifyLoading.value = false;
    showToast(err.detail || 'Could not start Spotify connection');
  }
}

onMounted(async () => {
  await loadConnections();
});

async function loadConnections() {
  try {
    const connections = await apiGet('/platform-connections/');
    spotifyConnected.value = connections.some((conn) => conn.platform === 'spotify');
    if (!spotifyConnected.value) {
      const { has_credentials } = await apiGet('/platform-connections/spotify/has-app-credentials');
      hasAppCredentials.value = has_credentials;
    }
  } catch {
    // ignore
  }
}

async function changePassword() {
  passwordError.value = '';
  passwordSuccess.value = '';

  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = 'Passwords do not match';
    return;
  }

  passwordLoading.value = true;
  try {
    await apiPost('/auth/change-password', {
      current_password: currentPassword.value,
      new_password: newPassword.value,
    });
    passwordSuccess.value = 'Password changed';
    currentPassword.value = '';
    newPassword.value = '';
    confirmPassword.value = '';
  } catch (err) {
    passwordError.value = err.detail || 'Failed to change password';
  } finally {
    passwordLoading.value = false;
  }
}

async function saveSpotifyCredentials() {
  if (spotifyLoading.value) return;
  if (!spotifyClientId.value.trim() || !spotifyClientSecret.value.trim()) {
    showToast('Both fields are required');
    return;
  }
  spotifyLoading.value = true;
  try {
    await apiPost('/platform-connections/', {
      platform: 'spotify',
      credentials: {
        client_id: spotifyClientId.value.trim(),
        client_secret: spotifyClientSecret.value.trim(),
      },
    });
    showSpotifySetup.value = false;
    await connectSpotify();
  } catch (err) {
    spotifyLoading.value = false;
    showToast(err.detail || 'Invalid credentials');
  }
}

async function uploadAvatar(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const user = await apiPost('/auth/avatar', formData);
    if (!user) return;
    setAvatarUrl(user.avatar_url);
    showToast('Avatar updated');
  } catch (err) {
    showToast(err.detail || 'Upload failed');
  }
}

async function disconnectSpotify() {
  try {
    await apiDelete('/platform-connections/spotify');
    spotifyConnected.value = false;
    hasAppCredentials.value = false;
    showToast('Spotify disconnected');
  } catch (err) {
    showToast(err.detail || 'Failed to disconnect');
  }
}
</script>

<style scoped>
.profile-container {
  max-width: 600px;
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding: var(--space-5) var(--space-4);
}

.profile-header-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-5);
}

.profile-avatar-wrapper {
  position: relative;
  cursor: pointer;
  border-radius: 50%;
  overflow: hidden;
  width: 96px;
  height: 96px;
  padding: 0;
  border: none;
  background: none;
  display: block;
}

.profile-avatar-wrapper:focus-visible {
  outline: 2px solid var(--accent, #1db954);
  outline-offset: 2px;
}

.profile-avatar {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  object-fit: cover;
}

.profile-avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-3);
  color: var(--text-1);
  font-size: 2.5rem;
  font-weight: 600;
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  opacity: 0;
  transition: opacity 0.2s;
  font-size: 1.5rem;
  color: white;
}

.profile-avatar-wrapper:hover .avatar-overlay {
  opacity: 1;
}

.profile-username {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}

.profile-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.connections-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.connection-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3);
  border-radius: var(--radius-2);
  background: var(--surface-2);
}

.connection-info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.connection-icon {
  font-size: 2rem;
}

.connection-status {
  margin: 0;
  font-size: 0.85rem;
}

.connection-status.connected {
  color: var(--success);
}

.connection-actions {
  display: flex;
  gap: var(--space-2);
}

.success-text {
  color: var(--success);
  font-size: 0.9rem;
}

.redirect-uri-display {
  display: block;
  padding: var(--space-2) var(--space-3);
  background: var(--surface-2);
  border-radius: var(--radius-1);
  word-break: break-all;
  font-size: 0.85rem;
}
</style>
