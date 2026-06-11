<template>
  <nav v-if="totalPages > 1" class="pagination" aria-label="Room list pagination">
    <button
      class="btn btn-ghost"
      type="button"
      :disabled="currentPage === 1"
      aria-label="Previous page"
      @click="$emit('update:page', currentPage - 1)"
    >
      <i class="ph ph-caret-left"></i>
    </button>
    <button
      v-for="page in totalPages"
      :key="page"
      class="btn"
      type="button"
      :class="page === currentPage ? 'btn-primary' : 'btn-ghost'"
      :aria-current="page === currentPage ? 'page' : undefined"
      :aria-label="`Page ${page}`"
      @click="$emit('update:page', page)"
    >
      {{ page }}
    </button>
    <button
      class="btn btn-ghost"
      type="button"
      :disabled="currentPage === totalPages"
      aria-label="Next page"
      @click="$emit('update:page', currentPage + 1)"
    >
      <i class="ph ph-caret-right"></i>
    </button>
  </nav>
</template>

<script setup>
defineProps({
  currentPage: { type: Number, required: true },
  totalPages: { type: Number, required: true },
});

defineEmits(['update:page']);
</script>
