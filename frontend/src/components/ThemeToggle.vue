<template>
  <button class="btn-icon" aria-label="Toggle theme" @click="toggleTheme">
    <i :class="theme === 'dark' ? 'ph ph-moon' : 'ph ph-sun'"></i>
  </button>
</template>

<script setup>
import { useTheme } from '../composables/useTheme.js';
const { theme, toggleTheme } = useTheme();
</script>
