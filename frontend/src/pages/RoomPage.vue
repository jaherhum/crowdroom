<template>
  <div class="page room-page">
    <header class="room-header">
      <h2>{{ roomName }}</h2>
      <div class="header-actions">
        <span class="badge">{{ roomCode }}</span>
        <ThemeToggle />
        <button class="btn btn-ghost btn-danger" @click="leaveRoom">Leave</button>
      </div>
    </header>

    <main class="room-layout">
      <!-- Now Playing -->
      <section class="panel now-playing-panel">
        <div v-if="!currentSong" class="empty-state">
          <i class="ph ph-music-notes"></i>
          <p>Nothing playing</p>
        </div>
        <div v-else>
          <img class="album-art" :src="currentSong.song.album_art_url || ''" :alt="`${currentSong.song.title} album art`">
          <div class="track-info">
            <h3>{{ currentSong.song.title }}</h3>
            <p class="text-secondary">{{ currentSong.song.artist }}</p>
          </div>
          <div v-if="currentSong.id" class="now-playing-actions">
            <button
              class="btn btn-ghost"
              :class="{ active: hasVotedSkip }"
              :disabled="voteOnCooldown"
              :title="hasVotedSkip ? 'Undo skip vote' : 'Vote to skip'"
              @click="voteSkip(currentSong.id)"
            >
              <i class="ph ph-skip-forward"></i> VoteSkip <span class="skip-vote-badge">{{ currentSong.votes_skip || 0 }}</span>
            </button>
          </div>
          <div class="progress-container">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
            </div>
            <div class="progress-times">
              <span>{{ formatTime(elapsedMs) }}</span>
              <span>{{ formatTime(currentSong.song.duration * 1000) }}</span>
            </div>
          </div>
          <div v-if="isHost" class="playback-controls">
            <button class="btn btn-icon" title="Play/Pause" @click="togglePlayPause">
              <i :class="isPlaying ? 'ph ph-pause' : 'ph ph-play'"></i>
            </button>
            <button class="btn btn-icon" title="Skip" @click="hostSkip">
              <i class="ph ph-skip-forward"></i>
            </button>
          </div>
        </div>
      </section>

      <!-- Queue -->
      <section class="panel queue-panel">
        <h3><i class="ph ph-queue"></i> Queue</h3>
        <div class="track-list">
          <TrackItem
            v-for="item in queueItems"
            :key="item.id"
            :track="item.song"
            :added-by="item.added_by?.username || ''"
          />
        </div>
        <div v-if="queueItems.length === 0" class="empty-state">
          <i class="ph ph-playlist"></i>
          <p>Queue is empty. Search and add songs!</p>
        </div>
      </section>

      <!-- Search -->
      <section class="panel search-panel">
        <h3><i class="ph ph-magnifying-glass"></i> Search</h3>
        <div v-if="spotifyBanner" class="empty-state">
          <i class="ph ph-spotify-logo"></i>
          <p>{{ spotifyBanner.message }}</p>
          <router-link to="/profile" class="btn btn-primary" style="margin-top: var(--space-3);">Set up in Profile</router-link>
        </div>
        <div class="search-input-wrapper">
          <i class="ph ph-magnifying-glass"></i>
          <input v-model="searchQuery" type="text" class="input" placeholder="Search for songs..." autocomplete="off" :disabled="!!spotifyBanner" @input="debouncedSearch">
        </div>
        <div class="track-list">
          <TrackItem v-for="track in searchResults" :key="track.external_id" :track="track">
            <template #actions>
              <button class="btn btn-secondary" title="Add to queue" @click="addToQueue(track.external_id)">
                <i class="ph ph-plus"></i>
              </button>
            </template>
          </TrackItem>
        </div>
        <div v-if="searchQuery.length >= 2 && searchResults.length === 0 && !searching" class="empty-state">
          <p>No results found.</p>
        </div>
      </section>

      <!-- Members -->
      <aside class="panel members-panel">
        <h3><i class="ph ph-users"></i> Members <span class="badge">{{ members.length }}</span></h3>
        <ul class="members-list">
          <li v-for="member in members" :key="member.id" class="member-item">
            <img v-if="member.avatar_url" :src="member.avatar_url" class="member-avatar member-avatar-img" alt="">
            <span v-else class="member-avatar">{{ (member.username || '?')[0].toUpperCase() }}</span>
            <span>{{ member.username || 'Unknown' }}</span>
          </li>
        </ul>
      </aside>

      <!-- History -->
      <section class="panel history-panel">
        <details>
          <summary><h3><i class="ph ph-clock-counter-clockwise"></i> Recently Played</h3></summary>
          <div class="track-list">
            <div v-for="(entry, index) in history" :key="index" class="track-item">
              <img v-if="entry.song?.album_art_url" class="track-item-art" :src="entry.song.album_art_url" alt="">
              <div class="track-item-info">
                <div class="track-item-title">{{ entry.song?.title || entry.song_id }}</div>
                <div class="track-item-artist">{{ entry.song?.artist || '' }} &middot; {{ new Date(entry.played_at).toLocaleTimeString() }}</div>
              </div>
            </div>
          </div>
          <p v-if="history.length === 0" class="text-tertiary" style="padding: var(--space-3);">No history yet.</p>
        </details>
      </section>
    </main>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { apiGet, apiPost, apiDelete } from '../composables/useApi.js';
import { useAuth } from '../composables/useAuth.js';
import { useWebSocket } from '../composables/useWebSocket.js';
import { useToast } from '../composables/useToast.js';
import ThemeToggle from '../components/ThemeToggle.vue';
import TrackItem from '../components/TrackItem.vue';

const props = defineProps({
  id: { type: String, required: true },
});

const router = useRouter();
const { userId } = useAuth();
const { connectToRoom, disconnect, onEvent } = useWebSocket();
const { showToast } = useToast();

const roomId = ref(props.id);
const roomName = ref('Loading...');
const roomCode = ref('');
const isHost = ref(false);
const sessionId = ref(null);

const currentSong = ref(null);
const queueItems = ref([]);
const members = ref([]);
const history = ref([]);
const searchQuery = ref('');
const searchResults = ref([]);
const searching = ref(false);

const isPlaying = ref(false);
const hasVotedSkip = ref(false);
const voteOnCooldown = ref(false);
const playbackPositionMs = ref(0);
const elapsedMs = ref(0);
let progressFrame = null;
let progressStartTime = null;

const spotifyBanner = ref(null);

const progressPercent = computed(() => {
  if (!currentSong.value) return 0;
  const durationMs = currentSong.value.song.duration * 1000;
  return Math.min((elapsedMs.value / durationMs) * 100, 100);
});

let searchTimeout = null;

onMounted(async () => {
  if (!roomId.value) {
    router.push('/rooms');
    return;
  }

  window.history.pushState(null, '', location.href);
  window.addEventListener('popstate', preventBack);

  try {
    await loadRoom();
    await loadSession();
    await Promise.all([loadQueue(), loadCurrentSong(), loadMembers(), loadHistory()]);
    await loadPlaybackState();
    setupWebSocket();
  } catch (err) {
    showToast(err.detail || 'Failed to load room');
  }
});

onUnmounted(() => {
  disconnect();
  window.removeEventListener('popstate', preventBack);
  if (progressFrame) cancelAnimationFrame(progressFrame);
});

function preventBack() {
  window.history.pushState(null, '', location.href);
}

async function loadRoom() {
  const room = await apiGet(`/rooms/${roomId.value}`);
  roomName.value = room.room_name;
  roomCode.value = room.room_code;
  isHost.value = room.host_user_id === userId.value;
  if (isHost.value) await checkSpotifyConnection();
}

async function loadSession() {
  try {
    const session = await apiGet(`/session/by-room/${roomId.value}`);
    sessionId.value = session.id;
  } catch {
    try {
      const sessions = await apiGet('/session/');
      const match = sessions.find((sess) => sess.room_id === roomId.value);
      if (match) sessionId.value = match.id;
    } catch {
      sessionId.value = null;
    }
  }
}

async function loadQueue() {
  if (!sessionId.value) return;
  const items = await apiGet(`/queue/?session_id=${sessionId.value}`);
  queueItems.value = items.slice(1);
}

async function loadCurrentSong() {
  if (!sessionId.value) return;
  const item = await apiGet(`/queue/current?session_id=${sessionId.value}`);
  currentSong.value = item?.song ? item : null;
}

async function loadMembers() {
  members.value = await apiGet(`/rooms/${roomId.value}/members`);
}

async function loadHistory() {
  try {
    history.value = await apiGet(`/rooms/${roomId.value}/history/`);
  } catch {
    history.value = [];
  }
}

async function loadPlaybackState() {
  try {
    await syncPlaybackPosition();
    if (isPlaying.value && !currentSong.value) {
      await loadExternalTrack();
    }
    if (isPlaying.value) startProgressAnimation();
  } catch {
    // ignore
  }
}

let currentExternalId = null;

async function syncPlaybackPosition() {
  const state = await apiGet(`/rooms/${roomId.value}/playback`);
  if (state.status === 'playing') {
    isPlaying.value = true;
    playbackPositionMs.value = state.elapsed_ms || 0;
  } else if (state.status === 'paused') {
    isPlaying.value = false;
    playbackPositionMs.value = state.elapsed_ms || 0;
  } else {
    isPlaying.value = false;
    playbackPositionMs.value = 0;
  }
  currentExternalId = state.current_song_id || null;
  elapsedMs.value = playbackPositionMs.value;
}

async function loadExternalTrack() {
  if (!currentExternalId) return;
  try {
    const song = await apiGet(`/songs/by-external/${currentExternalId}?platform=spotify`);
    currentSong.value = { id: null, votes_skip: 0, song };
  } catch {
    // song not yet in DB
  }
}

function startProgressAnimation() {
  if (progressFrame) cancelAnimationFrame(progressFrame);
  if (!currentSong.value || !isPlaying.value) return;

  const offsetMs = playbackPositionMs.value || 0;
  progressStartTime = Date.now();

  function update() {
    const elapsed = offsetMs + (Date.now() - progressStartTime);
    elapsedMs.value = elapsed;
    const durationMs = currentSong.value?.song?.duration * 1000;
    if (durationMs && elapsed < durationMs && isPlaying.value) {
      progressFrame = requestAnimationFrame(update);
    }
  }

  progressFrame = requestAnimationFrame(update);
}

async function checkSpotifyConnection() {
  try {
    const connections = await apiGet('/platform-connections/');
    const hasSpotify = connections.some((conn) => conn.platform === 'spotify');
    if (!hasSpotify) {
      spotifyBanner.value = { message: 'Connect Spotify in your profile to enable search and playback' };
    }
  } catch {
    // ignore
  }
}

function debouncedSearch() {
  clearTimeout(searchTimeout);
  const query = searchQuery.value.trim();
  if (query.length < 2) {
    searchResults.value = [];
    return;
  }
  searchTimeout = setTimeout(() => handleSearch(query), 300);
}

async function handleSearch(query) {
  searching.value = true;
  try {
    searchResults.value = await apiGet(`/search/?room_id=${roomId.value}&q=${encodeURIComponent(query)}`);
  } catch (err) {
    showToast(err.detail || 'Search failed');
  } finally {
    searching.value = false;
  }
}

async function addToQueue(externalId) {
  if (!sessionId.value) {
    showToast('No active session');
    return;
  }
  try {
    await apiGet(`/search/${externalId}?room_id=${roomId.value}`);
    const dbSong = await apiGet(`/songs/by-external/${externalId}?platform=spotify`);
    await apiPost('/queue/', { session_id: sessionId.value, song_id: dbSong.id, group: 'manual' });
    showToast('Added to queue', 'success');
    loadQueue();
  } catch (err) {
    showToast(err.detail || 'Failed to add song');
  }
}

const VOTE_COOLDOWN_MS = 2500;

async function voteSkip(queueItemId) {
  if (voteOnCooldown.value) return;
  voteOnCooldown.value = true;
  try {
    if (hasVotedSkip.value) {
      await apiDelete(`/queue/vote?queue_item_id=${queueItemId}&user_id=${userId.value}`);
      hasVotedSkip.value = false;
    } else {
      await apiPost('/queue/vote', { queue_item_id: queueItemId, user_id: userId.value });
      hasVotedSkip.value = true;
    }
  } catch (err) {
    showToast(err.detail || 'Vote failed');
  }
  setTimeout(() => { voteOnCooldown.value = false; }, VOTE_COOLDOWN_MS);
}

async function togglePlayPause() {
  try {
    if (isPlaying.value) {
      await apiPost('/playback/pause');
    } else if (currentSong.value?.song?.id) {
      await apiPost('/playback/play', { song_id: currentSong.value.song.id });
    } else {
      await apiPost('/playback/play', {});
    }
  } catch (err) {
    handlePlaybackError(err);
  }
}

async function hostSkip() {
  try {
    await apiPost('/playback/skip');
  } catch (err) {
    handlePlaybackError(err);
  }
}

function handlePlaybackError(err) {
  const msg = err.detail || 'Playback control failed';
  showToast(msg);
}

function setupWebSocket() {
  connectToRoom(roomId.value);

  onEvent('queue_updated', (msg) => {
    if (msg.queue) {
      queueItems.value = msg.queue.slice(1);
    } else {
      loadQueue();
    }
  });

  onEvent('song_changed', async (msg) => {
    hasVotedSkip.value = false;
    if (msg.song && !msg.song.id) {
      currentSong.value = {
        id: null,
        votes_skip: 0,
        song: msg.song,
      };
      isPlaying.value = true;
      await syncPlaybackPosition();
      startProgressAnimation();
    } else {
      await loadCurrentSong();
      loadHistory();
      await new Promise((resolve) => setTimeout(resolve, 500));
      if (isHost.value && !isPlaying.value && currentSong.value) {
        try {
          await apiPost('/playback/play', { song_id: currentSong.value.song.id });
        } catch (err) {
          console.error('[auto-play failed]', err.detail || err.message);
        }
      }
    }
    loadQueue();
  });

  onEvent('skip_vote', (msg) => {
    if (currentSong.value && currentSong.value.id === msg.queue_item_id) {
      currentSong.value = { ...currentSong.value, votes_skip: msg.current_votes };
    }
    if (msg.skip_triggered) {
      hasVotedSkip.value = false;
      isPlaying.value = false;
      if (progressFrame) cancelAnimationFrame(progressFrame);
      loadCurrentSong();
      loadQueue();
      loadHistory();
    }
  });

  onEvent('playback_state_changed', async (msg) => {
    if (msg.status === 'playing') {
      isPlaying.value = true;
      await syncPlaybackPosition();
      if (!currentSong.value && currentExternalId) {
        await loadExternalTrack();
      }
      startProgressAnimation();
    } else if (msg.status === 'stopped') {
      isPlaying.value = false;
      currentSong.value = null;
      if (progressFrame) cancelAnimationFrame(progressFrame);
    } else {
      isPlaying.value = false;
      if (progressFrame) cancelAnimationFrame(progressFrame);
    }
  });

  onEvent('member_joined', () => loadMembers());
  onEvent('member_left', () => loadMembers());
}

async function leaveRoom() {
  try {
    await apiPost(`/rooms/${roomId.value}/leave`);
  } catch {
    // ignore
  }
  disconnect();
  router.push('/rooms');
}

function formatTime(ms) {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}
</script>
