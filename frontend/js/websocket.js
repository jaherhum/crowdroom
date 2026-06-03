let socket = null;
let roomId = null;
let reconnectAttempts = 0;
let reconnectTimer = null;
const listeners = new Map();

export function connectToRoom(targetRoomId) {
  disconnect();
  roomId = targetRoomId;
  reconnectAttempts = 0;
  connect();
}

function connect() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  socket = new WebSocket(`${protocol}//${location.host}/ws/${roomId}`);

  socket.addEventListener('open', () => {
    reconnectAttempts = 0;
  });

  socket.addEventListener('message', (event) => {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch {
      return;
    }

    if (msg.type === 'ping') {
      socket.send(JSON.stringify({ type: 'pong' }));
      return;
    }

    const eventType = msg.type || msg.event;
    if (eventType && listeners.has(eventType)) {
      for (const callback of listeners.get(eventType)) {
        callback(msg);
      }
    }
  });

  socket.addEventListener('close', () => {
    scheduleReconnect();
  });

  socket.addEventListener('error', () => {
    socket.close();
  });
}

function scheduleReconnect() {
  if (!roomId) return;
  const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
  reconnectAttempts++;
  reconnectTimer = setTimeout(connect, delay);
}

export function disconnect() {
  roomId = null;
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (socket) {
    socket.close();
    socket = null;
  }
}

export function onEvent(eventType, callback) {
  if (!listeners.has(eventType)) {
    listeners.set(eventType, new Set());
  }
  listeners.get(eventType).add(callback);
}

export function offEvent(eventType, callback) {
  if (listeners.has(eventType)) {
    listeners.get(eventType).delete(callback);
  }
}

export function isConnected() {
  return socket && socket.readyState === WebSocket.OPEN;
}
