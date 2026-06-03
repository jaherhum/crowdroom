import { apiGet, apiPost, apiDelete } from '../api.js';
import { requireAuth, getUserId, getToken } from '../auth.js';
import { connectToRoom, onEvent, disconnect } from '../websocket.js';
import { initTheme, toggleTheme } from '../theme.js';
import { showToast } from '../toast.js';

let roomId = null;
let sessionId = null;
let isHost = false;
let currentSong = null;
let progressFrame = null;
let isPlaying = false;
let playbackPositionMs = 0;

document.addEventListener('DOMContentLoaded', async () => {
  requireAuth();
  initTheme();

  history.pushState(null, '', location.href);
  window.addEventListener('popstate', () => {
    history.pushState(null, '', location.href);
  });

  document.querySelector('.theme-toggle').addEventListener('click', toggleTheme);

  roomId = new URLSearchParams(window.location.search).get('id');
  if (!roomId) {
    window.location.href = '/rooms';
    return;
  }

  document.getElementById('leave-btn').addEventListener('click', leaveRoom);
  setupSearch();

  try {
    await loadRoom();
    await loadSession();
    await Promise.all([loadQueue(), loadCurrentSong(), loadMembers(), loadHistory()]);
    await loadPlaybackState();
    connectWebSocket();
  } catch (err) {
    showToast(err.detail || 'Failed to load room');
  }
});

async function loadRoom() {
  const room = await apiGet(`/rooms/${roomId}`);
  document.getElementById('room-name').textContent = room.room_name;
  document.getElementById('room-code').textContent = room.room_code;
  document.title = `CrowdRoom — ${room.room_name}`;

  isHost = room.host_user_id === getUserId();
  if (isHost) {
    document.getElementById('host-controls').hidden = false;
    setupHostControls();
    checkSpotifyConnection();
  }
}

async function loadSession() {
  const sessions = await apiGet('/session/');
  const session = sessions.find((sess) => sess.room_id === roomId);
  if (session) {
    sessionId = session.id;
  }
}

async function loadQueue() {
  if (!sessionId) return;
  const items = await apiGet(`/queue/?session_id=${sessionId}`);
  renderQueue(items);
}

async function loadCurrentSong() {
  if (!sessionId) return;
  const item = await apiGet(`/queue/current?session_id=${sessionId}`);
  renderNowPlaying(item);
}

async function loadMembers() {
  const members = await apiGet(`/rooms/${roomId}/members`);
  renderMembers(members);
}

async function loadHistory() {
  try {
    const history = await apiGet(`/rooms/${roomId}/history/`);
    renderHistory(history);
  } catch {
    renderHistory([]);
  }
}

async function loadPlaybackState() {
  try {
    await syncPlaybackPosition();
    if (isPlaying) {
      const icon = document.getElementById('play-pause-icon');
      icon.className = 'ph ph-pause';
      startProgressAnimation();
    }
  } catch {
    // ignore
  }
}

async function syncPlaybackPosition() {
  const state = await apiGet(`/rooms/${roomId}/playback`);
  if (state.status === 'playing') {
    isPlaying = true;
    playbackPositionMs = state.elapsed_ms || 0;
  } else if (state.status === 'paused') {
    isPlaying = false;
    playbackPositionMs = state.elapsed_ms || 0;
  } else {
    isPlaying = false;
    playbackPositionMs = 0;
  }
}

function renderQueue(items) {
  const container = document.getElementById('queue-list');
  const emptyEl = document.getElementById('queue-empty');

  const queueItems = items.slice(1);

  if (queueItems.length === 0) {
    container.innerHTML = '';
    emptyEl.hidden = false;
    return;
  }

  emptyEl.hidden = true;
  container.innerHTML = queueItems.map((item) => `
    <div class="track-item" data-id="${item.id}">
      <img class="track-item-art" src="${item.song.album_art_url || ''}" alt="">
      <div class="track-item-info">
        <div class="track-item-title">${escapeHtml(item.song.title)}</div>
        <div class="track-item-artist">${escapeHtml(item.song.artist)}${item.added_by ? ` · ${escapeHtml(item.added_by.username)}` : ''}</div>
      </div>
    </div>
  `).join('');
}

function renderNowPlaying(item) {
  const emptyEl = document.getElementById('now-playing-empty');
  const nowPlayingEl = document.getElementById('now-playing');

  if (!item || !item.song) {
    emptyEl.hidden = false;
    nowPlayingEl.hidden = true;
    currentSong = null;
    if (progressFrame) cancelAnimationFrame(progressFrame);
    return;
  }

  emptyEl.hidden = true;
  nowPlayingEl.hidden = false;
  currentSong = item;

  const art = document.getElementById('album-art');
  art.src = item.song.album_art_url || '';
  art.alt = `${item.song.title} album art`;

  document.getElementById('track-title').textContent = item.song.title;
  document.getElementById('track-artist').textContent = item.song.artist;
  document.getElementById('time-total').textContent = formatTime(item.song.duration * 1000);
  document.getElementById('now-playing-votes').textContent = item.votes_skip || 0;

  const skipBtn = document.getElementById('now-playing-skip-btn');
  skipBtn.onclick = () => voteSkip(item.id);
}

function startProgressAnimation() {
  if (progressFrame) cancelAnimationFrame(progressFrame);
  if (!currentSong || !isPlaying) return;

  const durationMs = currentSong.song.duration * 1000;
  const offsetMs = playbackPositionMs || 0;
  const startTime = Date.now();

  function update() {
    const elapsed = offsetMs + (Date.now() - startTime);
    const progress = Math.min(elapsed / durationMs, 1);
    document.getElementById('progress-fill').style.width = `${progress * 100}%`;
    document.getElementById('time-elapsed').textContent = formatTime(elapsed);

    if (progress < 1 && isPlaying) {
      progressFrame = requestAnimationFrame(update);
    }
  }

  progressFrame = requestAnimationFrame(update);
}

function renderMembers(members) {
  const container = document.getElementById('members-list');
  document.getElementById('member-count').textContent = members.length;

  container.innerHTML = members.map((member) => {
    const initial = (member.username || '?')[0].toUpperCase();
    const hostBadge = member.id === getUserId() ? '' : '';
    return `
      <li class="member-item">
        <span class="member-avatar">${initial}</span>
        <span>${escapeHtml(member.username || 'Unknown')}</span>
      </li>
    `;
  }).join('');
}

function renderHistory(entries) {
  const container = document.getElementById('history-list');
  if (entries.length === 0) {
    container.innerHTML = '<p class="text-tertiary" style="padding: var(--space-3);">No history yet.</p>';
    return;
  }

  container.innerHTML = entries.map((entry) => `
    <div class="track-item">
      ${entry.song && entry.song.album_art_url ? `<img class="track-item-art" src="${entry.song.album_art_url}" alt="">` : ''}
      <div class="track-item-info">
        <div class="track-item-title">${entry.song ? escapeHtml(entry.song.title) : escapeHtml(entry.song_id)}</div>
        <div class="track-item-artist">${entry.song ? escapeHtml(entry.song.artist) : ''} · ${new Date(entry.played_at).toLocaleTimeString()}</div>
      </div>
    </div>
  `).join('');
}

async function checkSpotifyConnection() {
  try {
    const connections = await apiGet('/platform-connections/');
    const hasSpotify = connections.some((conn) => conn.platform === 'spotify');
    if (!hasSpotify) {
      const { has_credentials } = await apiGet('/platform-connections/spotify/has-app-credentials');
      const searchPanel = document.querySelector('.search-panel');
      const banner = document.createElement('div');
      banner.className = 'empty-state';

      if (has_credentials) {
        banner.innerHTML = `
          <i class="ph ph-spotify-logo"></i>
          <p>Connect Spotify to enable search and playback</p>
          <a href="/api/v1/auth/spotify?token=${getToken()}" class="btn btn-primary" style="margin-top: var(--space-3);">Connect Spotify</a>
        `;
      } else {
        banner.innerHTML = `
          <i class="ph ph-spotify-logo"></i>
          <p>Set up your Spotify app to enable search and playback</p>
          <button id="setup-spotify-btn" class="btn btn-primary" style="margin-top: var(--space-3);">Set up Spotify</button>
        `;
      }
      searchPanel.querySelector('.search-input-wrapper').before(banner);
      document.getElementById('search-input').disabled = true;

      if (!has_credentials) {
        document.getElementById('setup-spotify-btn').addEventListener('click', showSpotifyCredentialsModal);
      }
    }
  } catch {
    // ignore
  }
}

function showSpotifyCredentialsModal() {
  const modal = document.getElementById('spotify-credentials-modal');
  modal.hidden = false;

  const form = document.getElementById('spotify-credentials-form');
  form.onsubmit = async (event) => {
    event.preventDefault();
    const clientId = document.getElementById('spotify-client-id').value.trim();
    const clientSecret = document.getElementById('spotify-client-secret').value.trim();

    if (!clientId || !clientSecret) {
      showToast('Both fields are required');
      return;
    }

    try {
      await apiPost('/platform-connections/', {
        platform: 'spotify',
        credentials: { client_id: clientId, client_secret: clientSecret },
      });
      modal.hidden = true;
      window.location.href = `/api/v1/auth/spotify?token=${getToken()}`;
    } catch (err) {
      showToast(err.detail || 'Invalid credentials');
    }
  };

  document.getElementById('spotify-modal-cancel').addEventListener('click', () => {
    modal.hidden = true;
  });
}

function setupSearch() {
  const input = document.getElementById('search-input');
  let timeout = null;

  input.addEventListener('input', () => {
    clearTimeout(timeout);
    const query = input.value.trim();
    if (query.length < 2) {
      document.getElementById('search-results').innerHTML = '';
      document.getElementById('search-empty').hidden = true;
      return;
    }
    timeout = setTimeout(() => handleSearch(query), 300);
  });
}

async function handleSearch(query) {
  const resultsEl = document.getElementById('search-results');
  const emptyEl = document.getElementById('search-empty');

  try {
    const results = await apiGet(`/search/?room_id=${roomId}&q=${encodeURIComponent(query)}`);

    if (results.length === 0) {
      resultsEl.innerHTML = '';
      emptyEl.hidden = false;
      return;
    }

    emptyEl.hidden = true;
    resultsEl.innerHTML = results.map((track) => `
      <div class="track-item">
        <img class="track-item-art" src="${track.album_art_url || ''}" alt="">
        <div class="track-item-info">
          <div class="track-item-title">${escapeHtml(track.title)}</div>
          <div class="track-item-artist">${escapeHtml(track.artist)}</div>
        </div>
        <div class="track-item-actions">
          <button class="btn btn-secondary add-btn" data-external-id="${track.external_id}" title="Add to queue">
            <i class="ph ph-plus"></i>
          </button>
        </div>
      </div>
    `).join('');

    resultsEl.querySelectorAll('.add-btn').forEach((btn) => {
      btn.addEventListener('click', () => addToQueue(btn.dataset.externalId));
    });
  } catch (err) {
    showToast(err.detail || 'Search failed');
  }
}

async function addToQueue(externalId) {
  if (!sessionId) {
    showToast('No active session');
    return;
  }

  try {
    await apiGet(`/search/${externalId}?room_id=${roomId}`);

    const dbSong = await apiGet(`/songs/by-external/${externalId}?platform=spotify`);

    await apiPost('/queue/', {
      session_id: sessionId,
      song_id: dbSong.id,
      group: 'manual',
    });

    showToast('Added to queue', 'success');
    loadQueue();
  } catch (err) {
    showToast(err.detail || 'Failed to add song');
  }
}

async function voteSkip(queueItemId) {
  try {
    await apiPost('/queue/vote', {
      queue_item_id: queueItemId,
      user_id: getUserId(),
    });
  } catch (err) {
    showToast(err.detail || 'Vote failed');
  }
}

function setupHostControls() {
  document.getElementById('play-pause-btn').addEventListener('click', async () => {
    try {
      if (isPlaying) {
        await apiPost('/playback/pause');
      } else if (currentSong) {
        await apiPost('/playback/play', { song_id: currentSong.song.id });
      }
    } catch (err) {
      handlePlaybackError(err);
    }
  });

  document.getElementById('skip-btn').addEventListener('click', async () => {
    try {
      await apiPost('/playback/skip');
    } catch (err) {
      handlePlaybackError(err);
    }
  });
}

function handlePlaybackError(err) {
  const msg = err.detail || 'Playback control failed';
  if (msg.toLowerCase().includes('reconnect') || msg.toLowerCase().includes('re-link')) {
    showToast(`${msg} <a href="/api/v1/auth/spotify?token=${getToken()}">Reconnect</a>`, 'error');
  } else {
    showToast(msg);
  }
}

function connectWebSocket() {
  connectToRoom(roomId);

  onEvent('queue_updated', (msg) => {
    if (msg.queue) {
      renderQueue(msg.queue);
    } else {
      loadQueue();
    }
  });

  onEvent('song_changed', async () => {
    await loadCurrentSong();
    loadQueue();
    loadHistory();
    await new Promise((resolve) => setTimeout(resolve, 500));
    console.log('[song_changed] isHost=%s isPlaying=%s currentSong=%s', isHost, isPlaying, !!currentSong);
    if (isHost && !isPlaying && currentSong) {
      try {
        await apiPost('/playback/play', { song_id: currentSong.song.id });
      } catch (err) {
        console.error('[auto-play failed]', err.detail || err.message);
      }
    }
  });

  onEvent('skip_vote', (msg) => {
    const btn = document.querySelector(`.skip-btn[data-item-id="${msg.queue_item_id}"]`);
    if (btn) {
      btn.textContent = `Skip (${msg.current_votes})`;
    }
    if (currentSong && currentSong.id === msg.queue_item_id) {
      document.getElementById('now-playing-votes').textContent = msg.current_votes;
    }
    if (msg.skip_triggered) {
      loadCurrentSong();
      loadQueue();
    }
  });

  onEvent('playback_state_changed', async (msg) => {
    const icon = document.getElementById('play-pause-icon');
    if (msg.status === 'playing') {
      isPlaying = true;
      icon.className = 'ph ph-pause';
      await syncPlaybackPosition();
      startProgressAnimation();
    } else {
      isPlaying = false;
      if (progressFrame) cancelAnimationFrame(progressFrame);
      icon.className = 'ph ph-play';
    }
  });

  onEvent('member_joined', () => loadMembers());
  onEvent('member_left', () => loadMembers());
}

async function leaveRoom() {
  try {
    await apiPost(`/rooms/${roomId}/leave`);
  } catch {
    // ignore errors on leave
  }
  disconnect();
  window.location.href = '/rooms';
}

function formatTime(ms) {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

window.addEventListener('beforeunload', () => {
  disconnect();
});
