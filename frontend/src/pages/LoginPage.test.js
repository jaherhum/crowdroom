import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import LoginPage from './LoginPage.vue';

// ThemeToggle reads window.matchMedia at import time; jsdom does not shim it.
beforeEach(() => {
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockReturnValue({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// Hoisted so vi.mock factories (also hoisted) can reference them.
const { push, currentRoute, clearAuth } = vi.hoisted(() => ({
  push: vi.fn(),
  currentRoute: { value: { path: '/login' } },
  clearAuth: vi.fn(),
}));

// App router: the instance useApi.js reads for 401 redirects.
vi.mock('../router/index.js', () => ({
  default: { push, currentRoute },
}));

// useAuth: LoginPage calls useAuth().fetchMe; useApi calls clearAuth.
vi.mock('../composables/useAuth.js', () => ({
  clearAuth,
  useAuth: () => ({ fetchMe: vi.fn().mockResolvedValue({}) }),
}));

// vue-router hooks used directly by LoginPage.
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push }),
}));

function stubFetch(routes) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url, opts = {}) => {
      const method = opts.method || 'GET';
      const hit = routes.find((r) => r.method === method && url === `/api/v1${r.path}`);
      if (!hit) {
        return Promise.reject(new Error(`unexpected fetch: ${method} ${url}`));
      }
      return Promise.resolve({
        status: hit.status,
        ok: hit.status >= 200 && hit.status < 300,
        json: () => Promise.resolve(hit.body ?? {}),
      });
    }),
  );
}

const ONLINE_BAD = [
  { method: 'GET', path: '/auth/mode', status: 200, body: { mode: 'ONLINE' } },
  { method: 'POST', path: '/auth/login', status: 401, body: { detail: 'Invalid credentials' } },
];

const ONLINE_GOOD = [
  { method: 'GET', path: '/auth/mode', status: 200, body: { mode: 'ONLINE' } },
  { method: 'POST', path: '/auth/login', status: 200, body: {} },
];

const LOCAL_BAD = [
  { method: 'GET', path: '/auth/mode', status: 500 },
  { method: 'POST', path: '/auth/local-login', status: 401, body: { detail: 'Invalid credentials' } },
];

describe('LoginPage', () => {
  beforeEach(() => {
    push.mockClear();
    clearAuth.mockClear();
    vi.unstubAllGlobals();
  });

  it('shows an error and stays put when online credentials are invalid', async () => {
    stubFetch(ONLINE_BAD);
    const wrapper = mount(LoginPage, { global: { stubs: { ThemeToggle: true } } });
    await flushPromises();

    await wrapper.find('input[placeholder="Username or email"]').setValue('unknown-user');
    await wrapper.find('input[placeholder="Password"]').setValue('wrong-password');
    await wrapper.find('form').trigger('submit');
    await flushPromises();

    const errorText = wrapper.find('.error-text');
    expect(errorText.exists()).toBe(true);
    expect(errorText.text()).toBe('Invalid credentials');
    expect(push).not.toHaveBeenCalled();
  });

  it('shows an error and stays put when local credentials are invalid', async () => {
    stubFetch(LOCAL_BAD);
    const wrapper = mount(LoginPage, { global: { stubs: { ThemeToggle: true } } });
    await flushPromises();

    await wrapper.find('#username').setValue('unknown');
    await wrapper.find('#local-password').setValue('wrong-password');
    await wrapper.find('form').trigger('submit');
    await flushPromises();

    const errorText = wrapper.find('.error-text');
    expect(errorText.exists()).toBe(true);
    expect(errorText.text()).toBe('Invalid credentials');
    expect(push).not.toHaveBeenCalled();
  });

  it('redirects to /rooms on successful login', async () => {
    stubFetch(ONLINE_GOOD);
    const wrapper = mount(LoginPage, { global: { stubs: { ThemeToggle: true } } });
    await flushPromises();

    await wrapper.find('input[placeholder="Username or email"]').setValue('real-user');
    await wrapper.find('input[placeholder="Password"]').setValue('correct-password');
    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(wrapper.find('.error-text').exists()).toBe(false);
    expect(push).toHaveBeenCalledWith('/rooms');
  });
});
