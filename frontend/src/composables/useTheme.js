import { ref } from 'vue';

const theme = ref(
  localStorage.getItem('theme') ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'),
);

function applyTheme(value) {
  document.documentElement.setAttribute('data-theme', value);
}

applyTheme(theme.value);

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (event) => {
  if (!localStorage.getItem('theme')) {
    theme.value = event.matches ? 'dark' : 'light';
    applyTheme(theme.value);
  }
});

export function useTheme() {
  function toggleTheme() {
    const next = theme.value === 'dark' ? 'light' : 'dark';
    theme.value = next;
    localStorage.setItem('theme', next);
    applyTheme(next);
  }

  return { theme, toggleTheme };
}
