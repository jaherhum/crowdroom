import { apiGet, apiPost } from '../api.js';
import { requireAuth, getUserId, getUsername, logout } from '../auth.js';
import { initTheme, toggleTheme } from '../theme.js';
import { showToast } from '../toast.js';

let joinTargetRoomId = null;

document.addEventListener('DOMContentLoaded', async () => {
  requireAuth();
  initTheme();

  try {
    const me = await apiGet('/auth/me');
    if (me.room_id) {
      window.location.href = `/room?id=${me.room_id}`;
      return;
    }
  } catch {
    // continue to rooms page
  }

  document.getElementById('username-display').textContent = getUsername();
  document.getElementById('logout-btn').addEventListener('click', logout);
  document.querySelector('.theme-toggle').addEventListener('click', toggleTheme);

  setupCreateModal();
  setupJoinPinModal();
  await loadRooms();
});

async function loadRooms() {
  try {
    const rooms = await apiGet('/rooms/');
    const userId = getUserId();
    const allRooms = rooms.filter((room) => room.host_user_id !== userId);
    const myRooms = rooms.filter((room) => room.host_user_id === userId);

    renderRooms(allRooms, 'rooms-list', 'rooms-empty');

    if (myRooms.length > 0) {
      document.getElementById('my-rooms-section').hidden = false;
      renderRooms(myRooms, 'my-rooms-list', null);
    }
  } catch (err) {
    showToast(err.detail || 'Failed to load rooms');
  }
}

function renderRooms(rooms, containerId, emptyId) {
  const container = document.getElementById(containerId);
  container.innerHTML = '';

  if (rooms.length === 0 && emptyId) {
    document.getElementById(emptyId).hidden = false;
    return;
  }
  if (emptyId) document.getElementById(emptyId).hidden = true;

  rooms.forEach((room) => {
    const card = document.createElement('div');
    card.className = 'card room-card';
    card.innerHTML = `
      <div class="room-card-header">
        <span class="room-card-name">${escapeHtml(room.room_name)}</span>
        ${room.is_private ? '<span class="badge"><i class="ph ph-lock"></i> Private</span>' : ''}
      </div>
      <div class="room-card-meta">
        <span><i class="ph ph-hash"></i> ${room.room_code}</span>
      </div>
      <div class="room-card-actions">
        <button class="btn btn-primary join-btn" data-room-id="${room.id}" data-private="${room.is_private}">Join</button>
      </div>
    `;
    container.appendChild(card);
  });

  container.addEventListener('click', handleJoinClick);
}

function handleJoinClick(event) {
  const btn = event.target.closest('.join-btn');
  if (!btn) return;

  const roomId = btn.dataset.roomId;
  const isPrivate = btn.dataset.private === 'true';

  if (isPrivate) {
    joinTargetRoomId = roomId;
    document.getElementById('join-pin-modal').hidden = false;
  } else {
    joinRoom(roomId, null).catch(() => {});
  }
}

async function joinRoom(roomId, pin) {
  try {
    const body = {};
    if (pin) body.pin = pin;
    await apiPost(`/rooms/${roomId}/join`, body);
    window.location.href = `/room?id=${roomId}`;
  } catch (err) {
    showToast(err.detail || 'Failed to join room');
    throw err;
  }
}

function setupCreateModal() {
  const modal = document.getElementById('create-room-modal');
  const form = document.getElementById('create-room-form');
  const privateCheck = document.getElementById('is-private-check');
  const pinGroup = document.getElementById('pin-group');

  document.getElementById('create-room-btn').addEventListener('click', () => {
    modal.hidden = false;
  });

  document.getElementById('cancel-create').addEventListener('click', () => {
    modal.hidden = true;
    form.reset();
  });

  modal.addEventListener('click', (event) => {
    if (event.target === modal) {
      modal.hidden = true;
      form.reset();
    }
  });

  privateCheck.addEventListener('change', () => {
    pinGroup.hidden = !privateCheck.checked;
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const userId = getUserId();
    const roomName = form.room_name.value.trim();
    const isPrivate = privateCheck.checked;
    const pin = isPrivate ? form.pin.value : null;
    const platform = form.platform.value;
    const maxMembers = parseInt(form.max_members.value, 10) || 50;
    const skipThreshold = parseInt(form.skip_threshold.value, 10) || 2;

    try {
      const room = await apiPost('/rooms/', {
        host_user_id: userId,
        room_name: roomName,
        is_private: isPrivate,
        pin: pin,
        settings: {
          skip_threshold: skipThreshold,
          max_members: maxMembers,
        },
      });

      await apiPost('/session/', {
        room_id: room.id,
        current_platform: platform,
      });

      await apiPost(`/rooms/${room.id}/join`, {});
      window.location.href = `/room?id=${room.id}`;
    } catch (err) {
      showToast(err.detail || 'Failed to create room');
    }
  });
}

function setupJoinPinModal() {
  const modal = document.getElementById('join-pin-modal');
  const form = document.getElementById('join-pin-form');

  document.getElementById('cancel-join').addEventListener('click', () => {
    modal.hidden = true;
    form.reset();
    joinTargetRoomId = null;
  });

  modal.addEventListener('click', (event) => {
    if (event.target === modal) {
      modal.hidden = true;
      form.reset();
      joinTargetRoomId = null;
    }
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const pin = form.pin.value;
    if (joinTargetRoomId && pin) {
      try {
        await joinRoom(joinTargetRoomId, pin);
      } catch {
        return;
      }
      modal.hidden = true;
      joinTargetRoomId = null;
      form.reset();
    }
  });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
