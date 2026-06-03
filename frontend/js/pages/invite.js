import { apiGet, apiPost } from '../api.js';
import { isAuthenticated, setToken, setUsername } from '../auth.js';
import { initTheme, toggleTheme } from '../theme.js';
import { showToast } from '../toast.js';

document.addEventListener('DOMContentLoaded', async () => {
  initTheme();
  document.querySelector('.theme-toggle').addEventListener('click', toggleTheme);

  const token = new URLSearchParams(window.location.search).get('token');
  if (!token) {
    showError('Invalid invite link');
    return;
  }

  try {
    const preview = await apiGet(`/rooms/invite/${token}`);
    document.getElementById('invite-loading').hidden = true;

    if (isAuthenticated()) {
      showInviteInfo(preview, token);
    } else {
      showLoginForm(preview, token);
    }
  } catch (err) {
    showError(err.detail || 'Invite link is invalid or expired');
  }
});

function showInviteInfo(preview, token) {
  const infoEl = document.getElementById('invite-info');
  infoEl.hidden = false;
  document.getElementById('invite-room-name').textContent = preview.room_name;
  document.getElementById('invite-detail').textContent = preview.is_private ? 'Private room' : 'Public room';

  document.getElementById('join-invite-btn').addEventListener('click', async () => {
    try {
      const result = await apiPost(`/rooms/invite/${token}/join`);
      window.location.href = `/room?id=${result.room_id}`;
    } catch (err) {
      showError(err.detail || 'Failed to join');
    }
  });
}

function showLoginForm(preview, token) {
  const loginEl = document.getElementById('invite-login');
  loginEl.hidden = false;
  document.getElementById('invite-loading').hidden = true;

  const form = document.getElementById('invite-login-form');
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const username = document.getElementById('invite-username').value.trim();
    if (!username) return;

    try {
      const loginResult = await apiPost('/auth/local-login', { username });
      setToken(loginResult.access_token);
      setUsername(username);

      const joinResult = await apiPost(`/rooms/invite/${token}/join`);
      window.location.href = `/room?id=${joinResult.room_id}`;
    } catch (err) {
      showError(err.detail || 'Failed to join');
    }
  });
}

function showError(message) {
  document.getElementById('invite-loading').hidden = true;
  const errorEl = document.getElementById('invite-error');
  errorEl.textContent = message;
  errorEl.hidden = false;
}
