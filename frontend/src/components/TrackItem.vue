<template>
  <div class="track-item">
    <img
      class="track-item-art"
      :src="track.album_art_url || ALBUM_ART_PLACEHOLDER"
      alt=""
      @error="onArtError"
    />
    <div class="track-item-info">
      <div class="track-item-title">{{ track.title }}</div>
      <div class="track-item-artist">
        {{ track.artist }}<template v-if="addedBy"> &middot; {{ addedBy }}</template>
      </div>
    </div>
    <div v-if="$slots.actions" class="track-item-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
import { ALBUM_ART_PLACEHOLDER, onArtError } from '../composables/useAlbumArt.js';

defineProps({
  track: { type: Object, required: true },
  addedBy: { type: String, default: '' },
});
</script>
