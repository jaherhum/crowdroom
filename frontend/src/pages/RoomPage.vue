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
          <img
            class="album-art"
            :src="currentSong.song.album_art_url || ALBUM_ART_PLACEHOLDER"
            :alt="`${currentSong.song.title} album art`"
            @error="onArtError"
          />
          <div class="track-info">
            <h3>{{ currentSong.song.title }}</h3>
            <p class="text-secondary">{{ currentSong.song.artist }}</p>
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
          <div v-if="currentSong.id" class="now-playing-actions">
            <button
              class="btn btn-ghost"
              :class="{ active: hasVotedSkip, 'on-cooldown': voteOnCooldown }"
              :title="hasVotedSkip ? 'Undo skip vote' : 'Vote to skip'"
              @click="voteSkip(currentSong.id)"
            >
              <i class="ph ph-skip-forward"></i> VoteSkip
              <span class="skip-vote-badge">{{ currentSong.votes_skip || 0 }}</span>
            </button>
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
        <details open>
          <summary>
            <h3><i class="ph ph-queue"></i> Queue <span class="badge">{{ queueItems.length }}</span></h3>
          </summary>
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
        </details>
      </section>

      <!-- Search -->
      <section class="panel search-panel">
        <details @toggle="onSearchToggle">
          <summary>
            <h3><i class="ph ph-magnifying-glass"></i> Search</h3>
          </summary>
          <div v-if="spotifyBanner" class="empty-state">
            <i class="ph ph-spotify-logo"></i>
            <p>{{ spotifyBanner.message }}</p>
            <router-link to="/profile" class="btn btn-primary" style="margin-top: var(--space-3)"
              >Set up in Profile</router-link
            >
          </div>
          <div class="search-input-wrapper">
            <i class="ph ph-magnifying-glass"></i>
            <input
              ref="searchInput"
              v-model="searchQuery"
              type="text"
              class="input"
              placeholder="Search for songs..."
              autocomplete="off"
              :disabled="!!spotifyBanner"
              @input="debouncedSearch"
            />
          </div>
          <div class="track-list">
            <TrackItem v-for="track in searchResults" :key="track.external_id" :track="track">
              <template #actions>
                <button
                  class="btn btn-secondary"
                  title="Add to queue"
                  :disabled="addingIds.has(track.external_id)"
                  @click="addToQueue(track.external_id)"
                >
                  <i class="ph ph-plus"></i>
                </button>
              </template>
            </TrackItem>
          </div>
          <div
            v-if="searchQuery.length >= 2 && searchResults.length === 0 && !searching"
            class="empty-state"
          >
            <p>No results found.</p>
          </div>
        </details>
      </section>

      <!-- Members -->
      <aside class="panel members-panel">
        <details>
          <summary>
            <h3>
              <i class="ph ph-users"></i> Members <span class="badge">{{ members.length }}</span>
            </h3>
          </summary>
          <ul class="members-list">
            <li v-for="member in members" :key="member.id" class="member-item">
              <img
                v-if="member.avatar_url"
                :src="member.avatar_url"
                class="member-avatar member-avatar-img"
                alt=""
              />
              <span v-else class="member-avatar">{{
                (member.username || '?')[0].toUpperCase()
              }}</span>
              <span>{{ member.username || 'Unknown' }}</span>
            </li>
          </ul>
        </details>
      </aside>

      <!-- History -->
      <section class="panel history-panel">
        <details>
          <summary>
            <h3>
              <i class="ph ph-clock-counter-clockwise"></i> Recently Played
              <span class="badge">{{ history.length }}</span>
            </h3>
          </summary>
          <div class="track-list">
            <div v-for="entry in history" :key="entry.id" class="track-item">
              <img
                v-if="entry.song?.album_art_url"
                class="track-item-art"
                :src="entry.song.album_art_url"
                alt=""
              />
              <div class="track-item-info">
                <div class="track-item-title">{{ entry.song?.title || entry.song_id }}</div>
                <div class="track-item-artist">
                  {{ entry.song?.artist || '' }} &middot;
                  {{ new Date(entry.played_at).toLocaleTimeString() }}
                </div>
              </div>
            </div>
          </div>
          <p v-if="history.length === 0" class="text-tertiary" style="padding: var(--space-3)">
            No history yet.
          </p>
        </details>
      </section>
    </main>

    <div
      v-if="showLeaveModal"
      class="modal-overlay"
      @click.self="cancelLeave"
    >
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="leave-modal-title">
        <h3 id="leave-modal-title">{{ isHost ? 'Close this room?' : 'Leave this room?' }}</h3>
        <p class="text-tertiary">
          {{ isHost
            ? 'You are the host. Leaving will close the room for everyone.'
            : 'You can rejoin later with the room code.' }}
        </p>
        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" @click="cancelLeave">Cancel</button>
          <button type="button" class="btn btn-danger" @click="confirmLeave">
            {{ isHost ? 'Close room' : 'Leave' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue';
import { useRouter, onBeforeRouteLeave } from 'vue-router';
import { apiGet, apiPost, apiDelete } from '../composables/useApi.js';
import { useAuth } from '../composables/useAuth.js';
import { useWebSocket } from '../composables/useWebSocket.js';
import { useToast } from '../composables/useToast.js';
import ThemeToggle from '../components/ThemeToggle.vue';
import TrackItem from '../components/TrackItem.vue';
import { ALBUM_ART_PLACEHOLDER, onArtError } from '../composables/useAlbumArt.js';

const props = defineProps({
  id: { type: String, required: true },
});

const router = useRouter();
const { userId } = useAuth();
const { connectToRoom, disconnect, onEvent, offEvent } = useWebSocket();
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
const searchInput = ref(null);

// Focus the search field when the Search panel is expanded so the user can
// type immediately. The native <details> toggle event fires after the
// open/closed state has flipped; nextTick ensures the input is in the DOM.
function onSearchToggle(event) {
  if (event.target.open) {
    nextTick(() => searchInput.value?.focus());
  }
}

const isPlaying = ref(false);
const hasVotedSkip = ref(false);
const voteOnCooldown = ref(false);
const playbackPositionMs = ref(0);
const elapsedMs = ref(0);
let progressFrame = null;
let progressStartTime = null;

const spotifyBanner = ref(null);
const addingIds = ref(new Set());

const showLeaveModal = ref(false);
// Resolver for the pending leave confirmation. onBeforeRouteLeave awaits this
// promise so navigation pauses until the user picks Cancel or Leave.
let leaveResolver = null;

const progressPercent = computed(() => {
  if (!currentSong.value) return 0;
  const durationMs = currentSong.value.song.duration * 1000;
  return Math.min((elapsedMs.value / durationMs) * 100, 100);
});

let searchTimeout = null;
let searchController = null;
const wsHandlers = [];
let leaving = false;

function handleBeforeUnload() {
  if (leaving || !roomId.value) return;
  navigator.sendBeacon(
    `/api/v1/rooms/${roomId.value}/leave`,
    new Blob([], { type: 'application/json' })
  );
}

onMounted(async () => {
  if (!roomId.value) {
    router.push('/rooms');
    return;
  }

  try {
    await loadRoom();
    await loadSession();
    await Promise.all([loadQueue(), loadCurrentSong(), loadMembers(), loadHistory()]);
    await loadPlaybackState();
    setupWebSocket();
    window.addEventListener('beforeunload', handleBeforeUnload);
  } catch (err) {
    showToast(err.detail || 'Failed to load room');
  }
});

onUnmounted(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload);
  teardownWebSocket();
  clearTimeout(searchTimeout);
  if (searchController) searchController.abort();
  if (progressFrame) cancelAnimationFrame(progressFrame);
});

onBeforeRouteLeave(async () => {
  if (leaving) return true;
  const confirmed = await requestLeaveConfirmation();
  if (!confirmed) return false;
  await sendLeave();
  return true;
});

function requestLeaveConfirmation() {
  // If a confirmation is already pending, reuse it instead of stacking modals.
  if (leaveResolver) return new Promise((resolve) => (leaveResolver = resolve));
  showLeaveModal.value = true;
  return new Promise((resolve) => {
    leaveResolver = resolve;
  });
}

function resolveLeave(confirmed) {
  showLeaveModal.value = false;
  if (leaveResolver) {
    leaveResolver(confirmed);
    leaveResolver = null;
  }
}

function cancelLeave() {
  resolveLeave(false);
}

function confirmLeave() {
  resolveLeave(true);
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
  // COUPLING: the backend returns the full queue with index 0 being the
  // currently-playing track (see queue_repo.get_first_item ordering). The
  // "up next" list must exclude it, so we drop index 0 here. If the backend
  // ever stops putting the current song first, update this slice too.
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
      spotifyBanner.value = {
        message: 'Connect Spotify in your profile to enable search and playback',
      };
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
  // Cancel any in-flight search so out-of-order responses can't overwrite
  // results from a newer query.
  if (searchController) searchController.abort();
  searchController = new AbortController();
  const signal = searchController.signal;

  searching.value = true;
  try {
    searchResults.value = await apiGet(
      `/search/?room_id=${roomId.value}&q=${encodeURIComponent(query)}`,
      { signal },
    );
  } catch (err) {
    if (err.name === 'AbortError') return;
    showToast(err.detail || 'Search failed');
  } finally {
    if (!signal.aborted) searching.value = false;
  }
}

async function addToQueue(externalId) {
  if (!sessionId.value) {
    showToast('No active session');
    return;
  }
  if (addingIds.value.has(externalId)) return;
  addingIds.value = new Set(addingIds.value).add(externalId);
  try {
    await apiGet(`/search/${externalId}?room_id=${roomId.value}`);
    const dbSong = await apiGet(`/songs/by-external/${externalId}?platform=spotify`);
    await apiPost('/queue/', { session_id: sessionId.value, song_id: dbSong.id, group: 'manual' });
    showToast('Added to queue', 'success');
    loadQueue();
  } catch (err) {
    showToast(err.detail || 'Failed to add song');
  } finally {
    const next = new Set(addingIds.value);
    next.delete(externalId);
    addingIds.value = next;
  }
}

const VOTE_COOLDOWN_MS = 2500;
let voteCooldownUntil = 0;

async function voteSkip(queueItemId) {
  if (voteOnCooldown.value) {
    const remainingMs = Math.max(0, voteCooldownUntil - Date.now());
    const seconds = Math.ceil(remainingMs / 1000) || 1;
    showToast(`Slow down — you can vote again in ${seconds}s`);
    return;
  }
  voteOnCooldown.value = true;
  voteCooldownUntil = Date.now() + VOTE_COOLDOWN_MS;
  try {
    if (hasVotedSkip.value) {
      await apiDelete(`/queue/vote?queue_item_id=${queueItemId}`);
      hasVotedSkip.value = false;
    } else {
      await apiPost('/queue/vote', { queue_item_id: queueItemId });
      hasVotedSkip.value = true;
    }
  } catch (err) {
    // The server enforces its own cooldown and returns 429 with retry_after.
    if (err.status === 429) {
      const seconds = Math.ceil(err.retryAfter || 0) || 1;
      showToast(`Too many votes — please wait ${seconds}s`);
    } else {
      showToast(err.detail || 'Vote failed');
    }
  }
  setTimeout(() => {
    voteOnCooldown.value = false;
  }, VOTE_COOLDOWN_MS);
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

  const register = (eventType, handler) => {
    onEvent(eventType, handler);
    wsHandlers.push([eventType, handler]);
  };

  register('queue_updated', (msg) => {
    if (msg.queue) {
      // COUPLING: mirror loadQueue() — index 0 is the current song, so the
      // "up next" list drops it. Keep both slices in sync.
      queueItems.value = msg.queue.slice(1);
    } else {
      loadQueue();
    }
  });

  register('song_changed', async (msg) => {
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
      // COUPLING: brief delay to let the backend finish persisting the new
      // current song (finish_song updates session state asynchronously before
      // this song_changed event settles). Without it, the host's auto-play can
      // fire against a stale current song. 500ms is a heuristic buffer, not a
      // guaranteed sync point — the real guard is the isPlaying/currentSong
      // check below.
      await new Promise((resolve) => setTimeout(resolve, 500));
      if (isHost.value && !isPlaying.value && currentSong.value) {
        try {
          await apiPost('/playback/play', { song_id: currentSong.value.song.id });
        } catch (err) {
          handlePlaybackError(err);
        }
      }
    }
    loadQueue();
  });

  register('skip_vote', (msg) => {
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

  register('playback_state_changed', async (msg) => {
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

  const refreshMembers = async () => {
    if (leaving) return;
    try {
      await loadMembers();
    } catch {
      // The room may have just been closed; the room_closed handler redirects.
    }
  };
  register('member_joined', refreshMembers);
  register('member_left', refreshMembers);

  register('room_closed', () => {
    if (leaving) return;
    leaving = true;
    showToast('This room was closed by the host');
    teardownWebSocket();
    router.push('/rooms');
  });
}

function teardownWebSocket() {
  for (const [eventType, handler] of wsHandlers) {
    offEvent(eventType, handler);
  }
  wsHandlers.length = 0;
  disconnect();
}

async function sendLeave() {
  leaving = true;
  try {
    await apiPost(`/rooms/${roomId.value}/leave`);
  } catch {
    // ignore
  }
  teardownWebSocket();
}

async function leaveRoom() {
  // Navigating triggers onBeforeRouteLeave, which shows the confirmation modal
  // and performs sendLeave() if the user confirms.
  router.push('/rooms');
}

function formatTime(ms) {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}
</script>
