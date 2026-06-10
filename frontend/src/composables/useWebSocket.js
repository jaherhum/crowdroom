import { ref } from 'vue';

let socket = null;
let currentRoomId = null;
let reconnectAttempts = 0;
let reconnectTimer = null;
let heartbeatTimer = null;
const HEARTBEAT_TIMEOUT_MS = 45000;
const listeners = new Map();
const connected = ref(false);

function handleVisibilityChange() {
  if (document.visibilityState === 'visible' && currentRoomId) {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      reconnectAttempts = 0;
      connect();
    }
  }
}

document.addEventListener('visibilitychange', handleVisibilityChange);

function handleOpen() {
  reconnectAttempts = 0;
  connected.value = true;
  resetHeartbeatTimer();
}

function handleMessage(event) {
  let msg;
  try {
    msg = JSON.parse(event.data);
  } catch {
    return;
  }

  if (msg.type === 'ping') {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'pong' }));
    }
    resetHeartbeatTimer();
    return;
  }

  const eventType = msg.type || msg.event;
  if (eventType && listeners.has(eventType)) {
    for (const callback of listeners.get(eventType)) {
      callback(msg);
    }
  }
}

function handleClose() {
  connected.value = false;
  clearHeartbeatTimer();
  scheduleReconnect();
}

function handleError() {
  // Drop the failed socket without letting its close handler trigger a
  // second reconnect — detachAndClose strips the listeners first.
  detachAndClose();
  scheduleReconnect();
}

// Remove our listeners and close the current socket so a stale connection can
// never fire callbacks or schedule reconnects after we've moved on.
function detachAndClose() {
  if (!socket) return;
  socket.removeEventListener('open', handleOpen);
  socket.removeEventListener('message', handleMessage);
  socket.removeEventListener('close', handleClose);
  socket.removeEventListener('error', handleError);
  try {
    socket.close();
  } catch {
    // ignore — socket may already be closing
  }
  socket = null;
}

function connect() {
  if (
    socket &&
    (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)
  ) {
    return;
  }
  // Ensure any prior socket is fully detached before opening a new one.
  detachAndClose();

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  socket = new WebSocket(`${protocol}//${location.host}/ws/${currentRoomId}`);

  socket.addEventListener('open', handleOpen);
  socket.addEventListener('message', handleMessage);
  socket.addEventListener('close', handleClose);
  socket.addEventListener('error', handleError);
}

function resetHeartbeatTimer() {
  clearHeartbeatTimer();
  heartbeatTimer = setTimeout(() => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close(4000, 'heartbeat timeout');
    }
  }, HEARTBEAT_TIMEOUT_MS);
}

function clearHeartbeatTimer() {
  if (heartbeatTimer) {
    clearTimeout(heartbeatTimer);
    heartbeatTimer = null;
  }
}

function scheduleReconnect() {
  if (!currentRoomId) return;
  if (reconnectTimer) clearTimeout(reconnectTimer);
  const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
  reconnectAttempts++;
  reconnectTimer = setTimeout(connect, delay);
}

export function useWebSocket() {
  function connectToRoom(roomId) {
    disconnect();
    currentRoomId = roomId;
    reconnectAttempts = 0;
    connect();
  }

  function disconnect() {
    currentRoomId = null;
    clearHeartbeatTimer();
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    detachAndClose();
    connected.value = false;
  }

  function onEvent(eventType, callback) {
    if (!listeners.has(eventType)) {
      listeners.set(eventType, new Set());
    }
    listeners.get(eventType).add(callback);
  }

  function offEvent(eventType, callback) {
    if (listeners.has(eventType)) {
      listeners.get(eventType).delete(callback);
    }
  }

  return { connected, connectToRoom, disconnect, onEvent, offEvent };
}
