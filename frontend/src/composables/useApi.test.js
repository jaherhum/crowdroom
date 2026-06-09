import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Hoisted so the vi.mock factories (also hoisted) can safely reference them.
const { push, currentRoute, clearAuth } = vi.hoisted(() => ({
  push: vi.fn(),
  currentRoute: { value: { path: '/rooms' } },
  clearAuth: vi.fn(),
}));

// Mock the router so apiRequest's redirects are observable without a real one.
vi.mock('../router/index.js', () => ({
  default: { push, currentRoute },
}));

// Mock clearAuth so we can assert it runs on 401.
vi.mock('./useAuth.js', () => ({
  clearAuth,
}));

import { apiGet, apiPost, apiRequest } from './useApi.js';

function mockFetch({ status = 200, ok = status >= 200 && status < 300, body = {} } = {}) {
  return vi.fn().mockResolvedValue({
    status,
    ok,
    json: vi.fn().mockResolvedValue(body),
  });
}

describe('apiRequest', () => {
  beforeEach(() => {
    push.mockClear();
    clearAuth.mockClear();
    currentRoute.value.path = '/rooms';
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('returns parsed JSON on success', async () => {
    vi.stubGlobal('fetch', mockFetch({ status: 200, body: { id: 1 } }));
    const data = await apiGet('/rooms/');
    expect(data).toEqual({ id: 1 });
  });

  it('sends JSON content-type and stringified body for plain objects', async () => {
    const fetchMock = mockFetch({ status: 200, body: { ok: true } });
    vi.stubGlobal('fetch', fetchMock);
    await apiPost('/queue/', { song_id: 5 });
    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers['Content-Type']).toBe('application/json');
    expect(options.body).toBe(JSON.stringify({ song_id: 5 }));
    expect(options.credentials).toBe('include');
  });

  it('does not set JSON content-type for FormData', async () => {
    const fetchMock = mockFetch({ status: 200, body: {} });
    vi.stubGlobal('fetch', fetchMock);
    const fd = new FormData();
    fd.append('file', 'x');
    await apiRequest('POST', '/auth/avatar', fd);
    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers['Content-Type']).toBeUndefined();
    expect(options.body).toBe(fd);
  });

  it('clears auth and redirects to /login on 401', async () => {
    vi.stubGlobal('fetch', mockFetch({ status: 401, ok: false }));
    const result = await apiGet('/rooms/');
    expect(result).toBeUndefined();
    expect(clearAuth).toHaveBeenCalledOnce();
    expect(push).toHaveBeenCalledWith('/login');
  });

  it('does not redirect on 401 when already on /login', async () => {
    currentRoute.value.path = '/login';
    vi.stubGlobal('fetch', mockFetch({ status: 401, ok: false }));
    await apiGet('/auth/me');
    expect(clearAuth).toHaveBeenCalledOnce();
    expect(push).not.toHaveBeenCalled();
  });

  it('returns null on 204 No Content', async () => {
    vi.stubGlobal('fetch', mockFetch({ status: 204, ok: true }));
    const result = await apiPost('/rooms/x/leave');
    expect(result).toBeNull();
  });

  it('redirects to /complete-profile on 403 PROFILE_INCOMPLETE', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch({ status: 403, ok: false, body: { code: 'PROFILE_INCOMPLETE' } }),
    );
    const result = await apiGet('/rooms/');
    expect(result).toBeUndefined();
    expect(push).toHaveBeenCalledWith('/complete-profile');
  });

  it('throws an error carrying status/detail/code on other failures', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch({ status: 400, ok: false, body: { detail: 'Bad input', code: 'INVALID' } }),
    );
    await expect(apiGet('/rooms/')).rejects.toMatchObject({
      message: 'Bad input',
      status: 400,
      detail: 'Bad input',
      code: 'INVALID',
    });
  });

  it('surfaces retry_after on 429 rate-limit errors', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch({
        status: 429,
        ok: false,
        body: { detail: 'Too many requests. Try again in 2.0s.', retry_after: 2 },
      }),
    );
    await expect(apiPost('/queue/vote', { queue_item_id: 'x' })).rejects.toMatchObject({
      status: 429,
      retryAfter: 2,
    });
  });
});
