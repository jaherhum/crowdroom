import { createApp } from 'vue';
import App from './App.vue';
import router from './router/index.js';
import { fetchMe } from './composables/useAuth.js';
import './composables/useTheme.js';

// Self-hosted Phosphor icons (regular weight) — vendored via npm instead of a
// CDN <link> so the app works offline and isn't blocked by third-party outages.
import '@phosphor-icons/web/regular';

import './assets/css/variables.css';
import './assets/css/base.css';
import './assets/css/components.css';
import './assets/css/layout.css';
import './assets/css/pages/login.css';
import './assets/css/pages/rooms.css';
import './assets/css/pages/room.css';
import './assets/css/fonts.css';

// Resolve auth state from the httpOnly cookie before mounting so the router
// guard can rely on isAuthenticated synchronously.
fetchMe().finally(() => {
  const app = createApp(App);
  app.use(router);
  app.mount('#app');
});
