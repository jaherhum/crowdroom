import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Hoisted so the vi.mock factory can reference them. Mocks the router so the
// 1008 redirect is observable without a real router/jsdom navigation.
const { push, currentRoute } = vi.hoisted(() => ({
  push: vi.fn(),
  currentRoute: { value: { path: '/room/room-1' } },
}));

vi.mock('../router/index.js', () => ({
  default: { push, currentRoute },
}));

// A controllable fake WebSocket. Instances are tracked so tests can drive
// open/message/close/error transitions deterministically.
const sockets = [];

class FakeWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  constructor(url) {
    this.url = url;
    this.readyState = FakeWebSocket.CONNECTING;
    this.listeners = { open: [], message: [], close: [], error: [] };
    this.sent = [];
    sockets.push(this);
  }

  addEventListener(type, cb) {
    this.listeners[type].push(cb);
  }

  removeEventListener(type, cb) {
    this.listeners[type] = this.listeners[type].filter((fn) => fn !== cb);
  }

  send(data) {
    this.sent.push(data);
  }

  close() {
    this.readyState = FakeWebSocket.CLOSED;
  }

  // Test helpers
  emitOpen() {
    this.readyState = FakeWebSocket.OPEN;
    this.listeners.open.forEach((fn) => fn());
  }

  emitMessage(obj) {
    this.listeners.message.forEach((fn) => fn({ data: JSON.stringify(obj) }));
  }

  emitClose(code) {
    this.readyState = FakeWebSocket.CLOSED;
    this.listeners.close.forEach((fn) => fn({ code }));
  }

  emitError() {
    this.listeners.error.forEach((fn) => fn());
  }
}

let useWebSocket;

beforeEach(async () => {
  sockets.length = 0;
  push.mockClear();
  currentRoute.value = { path: '/room/room-1' };
  vi.stubGlobal('WebSocket', FakeWebSocket);
  vi.stubGlobal('location', { protocol: 'http:', host: 'localhost:3000' });
  vi.useFakeTimers();
  // Re-import fresh so module-level socket state is reset between tests.
  vi.resetModules();
  ({ useWebSocket } = await import('./useWebSocket.js'));
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('useWebSocket', () => {
  it('opens a socket to the room and marks connected', () => {
    const { connected, connectToRoom } = useWebSocket();
    connectToRoom('room-1');
    expect(sockets).toHaveLength(1);
    expect(sockets[0].url).toBe('ws://localhost:3000/ws/room-1');
    sockets[0].emitOpen();
    expect(connected.value).toBe(true);
  });

  it('replies to ping with pong', () => {
    const { connectToRoom } = useWebSocket();
    connectToRoom('room-1');
    sockets[0].emitOpen();
    sockets[0].emitMessage({ type: 'ping' });
    expect(sockets[0].sent).toContain(JSON.stringify({ type: 'pong' }));
  });

  it('dispatches events to registered listeners', () => {
    const { connectToRoom, onEvent } = useWebSocket();
    const cb = vi.fn();
    onEvent('queue_updated', cb);
    connectToRoom('room-1');
    sockets[0].emitOpen();
    sockets[0].emitMessage({ type: 'queue_updated', queue: [] });
    expect(cb).toHaveBeenCalledWith({ type: 'queue_updated', queue: [] });
  });

  it('stops dispatching after offEvent', () => {
    const { connectToRoom, onEvent, offEvent } = useWebSocket();
    const cb = vi.fn();
    onEvent('skip_vote', cb);
    offEvent('skip_vote', cb);
    connectToRoom('room-1');
    sockets[0].emitOpen();
    sockets[0].emitMessage({ type: 'skip_vote' });
    expect(cb).not.toHaveBeenCalled();
  });

  it('reconnects with exponential backoff after a close', () => {
    const { connectToRoom } = useWebSocket();
    connectToRoom('room-1');
    sockets[0].emitOpen();
    sockets[0].emitClose();
    // First backoff is 1000ms.
    expect(sockets).toHaveLength(1);
    vi.advanceTimersByTime(1000);
    expect(sockets).toHaveLength(2);
  });

  it('does not reconnect after an explicit disconnect', () => {
    const { connectToRoom, disconnect, connected } = useWebSocket();
    connectToRoom('room-1');
    sockets[0].emitOpen();
    disconnect();
    expect(connected.value).toBe(false);
    vi.advanceTimersByTime(60000);
    expect(sockets).toHaveLength(1);
  });

  it('error does not schedule a duplicate reconnect alongside close', () => {
    const { connectToRoom } = useWebSocket();
    connectToRoom('room-1');
    sockets[0].emitOpen();
    // error handler detaches+closes and schedules one reconnect; the manual
    // close below should be a no-op for reconnect since listeners are gone.
    sockets[0].emitError();
    vi.advanceTimersByTime(1000);
    expect(sockets).toHaveLength(2);
  });

  it('does not reconnect and redirects to /rooms on a 1008 close', () => {
    const { connectToRoom, connected } = useWebSocket();
    connectToRoom('room-1');
    sockets[0].emitOpen();
    sockets[0].emitClose(1008);
    expect(connected.value).toBe(false);
    expect(push).toHaveBeenCalledWith('/rooms');
    // No reconnect attempt should ever fire.
    vi.advanceTimersByTime(60000);
    expect(sockets).toHaveLength(1);
  });

  it('does not redirect again if already on /rooms', () => {
    currentRoute.value = { path: '/rooms' };
    const { connectToRoom } = useWebSocket();
    connectToRoom('room-1');
    sockets[0].emitOpen();
    sockets[0].emitClose(1008);
    expect(push).not.toHaveBeenCalled();
  });
});
