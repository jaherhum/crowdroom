import { createApp } from 'vue';
import App from './App.vue';
import router from './router/index.js';

import './assets/css/variables.css';
import './assets/css/base.css';
import './assets/css/components.css';
import './assets/css/layout.css';
import './assets/css/pages/login.css';
import './assets/css/pages/rooms.css';
import './assets/css/pages/room.css';

const app = createApp(App);
app.use(router);
app.mount('#app');
