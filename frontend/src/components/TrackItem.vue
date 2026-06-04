<template>
  <div class="track-item">
    <img class="track-item-art" :src="track.album_art_url || ''" alt="">
    <div class="track-item-info">
      <div class="track-item-title">{{ track.title }}</div>
      <div class="track-item-artist">{{ track.artist }}<template v-if="addedBy"> &middot; {{ addedBy }}</template></div>
    </div>
    <div v-if="$slots.actions" class="track-item-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  track: { type: Object, required: true },
  addedBy: { type: String, default: '' },
});
</script>
