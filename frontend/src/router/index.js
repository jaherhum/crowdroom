import { createRouter, createWebHistory } from 'vue-router';
import { useAuth } from '../composables/useAuth.js';

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../pages/LoginPage.vue'),
    meta: { guest: true },
  },
  {
    path: '/rooms',
    name: 'Rooms',
    component: () => import('../pages/RoomsPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/room/:id',
    name: 'Room',
    component: () => import('../pages/RoomPage.vue'),
    meta: { requiresAuth: true },
    props: true,
  },
  {
    path: '/invite',
    name: 'Invite',
    component: () => import('../pages/InvitePage.vue'),
  },
  {
    path: '/room',
    redirect: (to) => {
      const id = to.query.id;
      if (id) return `/room/${id}`;
      return '/rooms';
    },
  },
  {
    path: '/',
    redirect: '/rooms',
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/rooms',
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const { isAuthenticated } = useAuth();

  const returnRoom = sessionStorage.getItem('spotify_return_room');
  if (returnRoom && isAuthenticated.value && to.path !== `/room/${returnRoom}`) {
    sessionStorage.removeItem('spotify_return_room');
    return `/room/${returnRoom}`;
  }

  if (to.meta.requiresAuth && !isAuthenticated.value) {
    return '/login';
  }

  if (to.meta.guest && isAuthenticated.value) {
    return '/rooms';
  }
});

export default router;
