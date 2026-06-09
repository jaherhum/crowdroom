<template>
  <div class="page">
    <header class="app-header">
      <h2>CrowdRoom</h2>
      <div class="header-actions">
        <router-link to="/profile" class="avatar-link" title="Profile">
          <img v-if="avatarUrl" :src="avatarUrl" class="nav-avatar" alt="avatar">
          <span v-else class="nav-avatar nav-avatar-fallback">{{ (username || '?')[0].toUpperCase() }}</span>
        </router-link>
        <ThemeToggle />
        <button class="btn btn-ghost" @click="handleLogout">Logout</button>
      </div>
    </header>

    <main class="container">
      <section class="rooms-section">
        <div class="section-header">
          <h3>Rooms</h3>
          <div class="header-actions">
            <form class="join-code-form" @submit.prevent="joinByCode">
              <input v-model="joinCode" type="text" class="input" placeholder="Room code" maxlength="6" style="width: 120px;">
              <button type="submit" class="btn btn-secondary">Join</button>
            </form>
            <button class="btn btn-primary" @click="handleCreateRoom">
              <i class="ph ph-plus"></i> Create Room
            </button>
          </div>
        </div>
        <div class="rooms-grid">
          <div v-for="room in otherRooms" :key="room.id" class="card room-card" @click="handleJoin(room)">
            <div class="room-card-header">
              <span class="room-card-name">{{ room.room_name }}</span>
              <span v-if="room.is_private" class="badge"><i class="ph ph-lock"></i> Private</span>
            </div>
            <div class="room-card-meta">
              <span><i class="ph ph-hash"></i> {{ room.room_code }}</span>
            </div>
            <div class="room-card-actions">
              <button class="btn btn-primary" @click.stop="handleJoin(room)">Join</button>
            </div>
          </div>
        </div>
        <p v-if="otherRooms.length === 0" class="empty-state">
          <i class="ph ph-music-notes"></i>
          <span>No rooms available. Create one!</span>
        </p>
      </section>

      <section v-if="myRooms.length > 0" class="my-rooms-section">
        <div class="section-header">
          <h3>My Rooms</h3>
        </div>
        <div class="rooms-grid">
          <div v-for="room in myRooms" :key="room.id" class="card room-card" @click="handleJoin(room)">
            <div class="room-card-header">
              <span class="room-card-name">{{ room.room_name }}</span>
              <span v-if="room.is_private" class="badge"><i class="ph ph-lock"></i> Private</span>
            </div>
            <div class="room-card-meta">
              <span><i class="ph ph-hash"></i> {{ room.room_code }}</span>
            </div>
            <div class="room-card-actions">
              <button class="btn btn-primary" @click.stop="handleJoin(room)">Join</button>
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- Create Room Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <h3>Create Room</h3>
        <form class="login-form" @submit.prevent="createRoom">
          <input v-model="newRoom.name" type="text" class="input" placeholder="Room name" maxlength="255" required>
          <label class="checkbox-label">
            <input v-model="newRoom.isPrivate" type="checkbox"> Private room
          </label>
          <div v-if="newRoom.isPrivate">
            <input v-model="newRoom.pin" type="text" class="input" placeholder="PIN (4-6 digits)" pattern="\d{4,6}">
          </div>
          <select v-model="newRoom.platform" class="input">
            <option value="spotify">Spotify</option>
            <option value="tidal">Tidal</option>
          </select>
          <div class="form-row">
            <label class="input-label">
              Max members
              <input v-model.number="newRoom.maxMembers" type="number" class="input" min="2" max="200">
            </label>
            <label class="input-label">
              Skip votes needed
              <input v-model.number="newRoom.skipThreshold" type="number" class="input" min="1" max="50">
            </label>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" @click="showCreateModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary">Create</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Set Password Modal -->
    <div v-if="showPasswordModal" class="modal-overlay" @click.self="showPasswordModal = false">
      <div class="modal">
        <h3>Set a password</h3>
        <p class="text-secondary">A password is required to create rooms.</p>
        <form class="login-form" @submit.prevent="submitPassword">
          <input v-model="newPassword" type="password" class="input" placeholder="Password (min 6 chars)" minlength="6" required>
          <input v-model="confirmPassword" type="password" class="input" placeholder="Confirm password" minlength="6" required>
          <p v-if="passwordError" class="error-text">{{ passwordError }}</p>
          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" @click="showPasswordModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary">Set Password</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Join PIN Modal -->
    <div v-if="showPinModal" class="modal-overlay" @click.self="closePinModal">
      <div class="modal">
        <h3>Enter PIN</h3>
        <form class="login-form" @submit.prevent="submitPin">
          <input v-model="joinPin" type="text" class="input" placeholder="Room PIN" pattern="\d{4,6}" required>
          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" @click="closePinModal">Cancel</button>
            <button type="submit" class="btn btn-primary">Join</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { apiGet, apiPost } from '../composables/useApi.js';
import { useAuth } from '../composables/useAuth.js';
import { useToast } from '../composables/useToast.js';
import ThemeToggle from '../components/ThemeToggle.vue';

const router = useRouter();
const { username, userId, hasPassword, setHasPassword, logout } = useAuth();
const { showToast } = useToast();

const avatarUrl = ref(null);
const rooms = ref([]);
const showCreateModal = ref(false);
const showPinModal = ref(false);
const showPasswordModal = ref(false);
const joinPin = ref('');
const joinCode = ref('');
const joinTargetRoomId = ref(null);
const newPassword = ref('');
const confirmPassword = ref('');
const passwordError = ref('');

const newRoom = ref({
  name: '',
  isPrivate: false,
  pin: '',
  platform: 'spotify',
  maxMembers: 50,
  skipThreshold: 2,
});

const myRooms = computed(() => rooms.value.filter((room) => room.host_user_id === userId.value));
const otherRooms = computed(() => rooms.value.filter((room) => room.host_user_id !== userId.value));

onMounted(async () => {
  try {
    const me = await apiGet('/auth/me');
    setHasPassword(me.has_password);
    avatarUrl.value = me.avatar_url || null;
    if (me.room_id) {
      router.push(`/room/${me.room_id}`);
      return;
    }
  } catch {
    // continue
  }
  await loadRooms();
});

async function loadRooms() {
  try {
    rooms.value = await apiGet('/rooms/');
  } catch (err) {
    showToast(err.detail || 'Failed to load rooms');
  }
}

function handleLogout() {
  logout();
  router.push('/login');
}

function handleJoin(room) {
  if (room.is_private) {
    joinTargetRoomId.value = room.id;
    showPinModal.value = true;
  } else {
    joinRoom(room.id, null);
  }
}

async function joinRoom(targetRoomId, pin) {
  try {
    const body = {};
    if (pin) body.pin = pin;
    await apiPost(`/rooms/${targetRoomId}/join`, body);
    router.push(`/room/${targetRoomId}`);
  } catch (err) {
    showToast(err.detail || 'Failed to join room');
  }
}

async function joinByCode() {
  const code = joinCode.value.trim().toUpperCase();
  if (!code) return;
  try {
    const room = await apiGet(`/rooms/code/${code}`);
    handleJoin(room);
  } catch (err) {
    showToast(err.detail || 'Room not found');
  }
}

function closePinModal() {
  showPinModal.value = false;
  joinPin.value = '';
  joinTargetRoomId.value = null;
}

function submitPin() {
  if (joinTargetRoomId.value && joinPin.value) {
    joinRoom(joinTargetRoomId.value, joinPin.value);
    closePinModal();
  }
}

function handleCreateRoom() {
  if (!hasPassword.value) {
    showPasswordModal.value = true;
    return;
  }
  newRoom.value.name = `${username.value}'s Room`;
  showCreateModal.value = true;
}

async function submitPassword() {
  passwordError.value = '';
  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = 'Passwords do not match';
    return;
  }
  try {
    await apiPost('/auth/set-password', { password: newPassword.value });
    setHasPassword(true);
    showPasswordModal.value = false;
    newPassword.value = '';
    confirmPassword.value = '';
    newRoom.value.name = `${username.value}'s Room`;
    showCreateModal.value = true;
  } catch (err) {
    passwordError.value = err.detail || 'Failed to set password';
  }
}

async function createRoom() {
  try {
    const room = await apiPost('/rooms/', {
      room_name: newRoom.value.name,
      is_private: newRoom.value.isPrivate,
      pin: newRoom.value.isPrivate ? newRoom.value.pin : null,
      settings: {
        skip_threshold: newRoom.value.skipThreshold,
        max_members: newRoom.value.maxMembers,
      },
    });

    await apiPost('/session/', {
      room_id: room.id,
      current_platform: newRoom.value.platform,
    });

    await apiPost(`/rooms/${room.id}/join`, {});
    showCreateModal.value = false;
    router.push(`/room/${room.id}`);
  } catch (err) {
    showToast(err.detail || 'Failed to create room');
  }
}
</script>
