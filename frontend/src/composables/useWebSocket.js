import { ref } from 'vue';

let socket = null;
let currentRoomId = null;
let reconnectAttempts = 0;
let reconnectTimer = null;
const listeners = new Map();
const connected = ref(false);

function connect() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  socket = new WebSocket(`${protocol}//${location.host}/ws/${currentRoomId}`);

  socket.addEventListener('open', () => {
    reconnectAttempts = 0;
    connected.value = true;
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
    connected.value = false;
    scheduleReconnect();
  });

  socket.addEventListener('error', () => {
    socket.close();
  });
}

function scheduleReconnect() {
  if (!currentRoomId) return;
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
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (socket) {
      socket.close();
      socket = null;
    }
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
