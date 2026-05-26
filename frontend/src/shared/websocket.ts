import { api } from './api';
import { useChatStore } from './store';

class WebSocketManager {
  private socket: WebSocket | null = null;
  private heartbeatInterval: any = null;
  private reconnectTimeout: any = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private isConnecting = false;
  private offlineQueue: string[] = [];

  // Connect to the WebSocket gateway
  async connect() {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    if (this.isConnecting) return;
    this.isConnecting = true;
    useChatStore.getState().setConnectionStatus('connecting');

    try {
      // 1. Fetch short-lived WS credentials from REST api
      const { ws_token } = await api.getWsToken();

      // 2. Resolve target WS URL
      let wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      let wsHost = window.location.hostname + ':8000'; // Default local dev port
      if (
        window.location.port === '' ||
        window.location.port === '80' ||
        window.location.port === '8080'
      ) {
        wsHost = window.location.host; // Behind load balancer / Docker Compose
      }
      
      const wsUrl = `${wsProtocol}//${wsHost}/ws?token=${ws_token}`;

      // 3. Open Socket connection
      this.socket = new WebSocket(wsUrl);
      this.isConnecting = false;

      this.socket.onopen = () => {
        this.reconnectAttempts = 0;
        useChatStore.getState().setConnectionStatus('connected');
        useChatStore.getState().addToast('Connected to chat server', 'success');
        this.startHeartbeat();
        this.flushOfflineQueue();
      };

      this.socket.onmessage = (event) => {
        try {
          const rawData = JSON.parse(event.data);
          this.handleEvent(rawData);
        } catch (e) {
          console.error('Failed to parse WebSocket message', e);
        }
      };

      this.socket.onclose = (event) => {
        this.cleanup();
        useChatStore.getState().setConnectionStatus('disconnected');
        
        if (event.code !== 1000) {
          // Unexpected close, schedule reconnect
          useChatStore.getState().addToast('Connection lost. Reconnecting...', 'warning');
          this.scheduleReconnect();
        }
      };

      this.socket.onerror = (error) => {
        console.error('WebSocket connection error', error);
      };

    } catch (err) {
      this.isConnecting = false;
      useChatStore.getState().setConnectionStatus('disconnected');
      this.scheduleReconnect();
    }
  }

  // Gracefully close connection
  disconnect() {
    this.cleanup();
    if (this.socket) {
      this.socket.close(1000, 'Graceful disconnect');
      this.socket = null;
    }
  }

  // Send an event or buffer it if offline
  send(type: string, payload: Record<string, any>) {
    const rawPayload = JSON.stringify({ type, ...payload });
    
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(rawPayload);
    } else {
      // Buffer messages to queue if socket is offline (resilience buffering)
      this.offlineQueue.push(rawPayload);
      useChatStore.getState().addToast('Offline. Message queued for delivery.', 'info');
      
      // Optimistically insert message into UI if it's a message send
      if (type === 'message.send') {
        const store = useChatStore.getState();
        const activeRoomId = store.activeRoomId;
        const user = store.user;
        if (activeRoomId && user) {
          const tempMsgId = -Math.floor(Math.random() * 1000000); // Negative temporary ID
          store.addMessage(activeRoomId, {
            message_id: tempMsgId,
            room_id: activeRoomId,
            sender_id: user.id,
            content: payload.content,
            message_type: payload.message_type || 'text',
            reply_to: payload.reply_to,
            is_edited: false,
            created_at: new Date().toISOString(),
            isPending: true
          });
        }
      }
    }
  }

  // ── Private Helper Loops ──

  private startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      this.send('presence.heartbeat', {});
    }, 30000); // Send heartbeat event every 30s
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimeout || this.reconnectAttempts >= this.maxReconnectAttempts) return;
    this.reconnectAttempts++;
    
    // Exponential backoff with jitter
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts) + Math.random() * 1000, 30000);
    
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectTimeout = null;
      this.connect();
    }, delay);
  }

  private cleanup() {
    this.stopHeartbeat();
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  private flushOfflineQueue() {
    if (this.offlineQueue.length === 0) return;
    useChatStore.getState().addToast(`Flushing ${this.offlineQueue.length} queued offline messages...`, 'info');
    
    while (this.offlineQueue.length > 0 && this.socket && this.socket.readyState === WebSocket.OPEN) {
      const msg = this.offlineQueue.shift();
      if (msg) this.socket.send(msg);
    }
  }

  // Route incoming WebSocket events to Zustand state mutations
  private handleEvent(event: Record<string, any>) {
    const store = useChatStore.getState();
    const { type, ...data } = event;

    switch (type) {
      case 'connected':
        // Session successfully established on node
        break;

      case 'message.new':
        // New real-time message broadcast
        // Remove temporary pending message if it matches sender content (optimistic update resolution)
        const isFromSelf = data.sender_id === store.user?.id;
        if (isFromSelf) {
          const roomMsgs = store.messages[data.room_id] || [];
          const tempMsg = roomMsgs.find(m => m.isPending && m.content === data.content);
          if (tempMsg) {
            // Remove the temporary message first
            store.removeMessage(data.room_id, tempMsg.message_id);
          }
        }
        
        store.addMessage(data.room_id, {
          message_id: data.message_id,
          room_id: data.room_id,
          sender_id: data.sender_id,
          content: data.content,
          message_type: data.message_type,
          reply_to: data.reply_to,
          is_edited: false,
          created_at: data.created_at
        });
        
        // Show popup if not currently focused on the room
        if (store.activeRoomId !== data.room_id && data.sender_id !== store.user?.id) {
          const room = store.rooms.find(r => r.id === data.room_id);
          const roomName = room ? room.name : 'Direct Message';
          store.addToast(`New message in ${roomName}`, 'info');
        }
        break;

      case 'message.ack':
        // Acknowledge message delivery
        // If we find an optimistic pending message, update its ID and remove pending state
        if (store.activeRoomId) {
          const roomMsgs = store.messages[store.activeRoomId] || [];
          const pending = roomMsgs.find(m => m.isPending);
          if (pending) {
            store.updateMessage(store.activeRoomId, pending.message_id, {
              message_id: data.message_id,
              isPending: false
            });
          }
        }
        break;

      case 'message.read_receipt':
        // Message read update
        if (store.activeRoomId === data.room_id) {
          // Simply update the message's delivery status indicator locally
        }
        break;

      case 'typing.indicator':
        // A user starts/stops typing in a room
        if (store.user && data.user_id !== store.user.id) {
          // Find user profile name
          const members = store.roomMembers[data.room_id] || [];
          const member = members.find(m => m.user_id === data.user_id);
          const name = member?.username || 'Someone';
          store.setTyping(data.room_id, name, data.is_typing);
        }
        break;

      case 'presence.change':
        // A user changed their status (online, away, busy, offline)
        store.updateUserPresence(data.user_id, data.status, data.last_seen_at);
        break;

      case 'room.updated':
        // Users join or leave notifications
        if (data.event === 'user_joined' && store.activeRoomId === data.room_id) {
          // Re-fetch room members to keep list in sync
          api.getRoomMembers(data.room_id).then(members => {
            store.setRoomMembers(data.room_id, members);
          });
        }
        break;

      case 'pong':
        // Keep-alive heartbeat confirmation
        break;

      case 'error':
        // Error from socket logic
        store.addToast(`Socket error: ${data.message}`, 'error');
        break;

      default:
        console.warn('Unhandled WebSocket event type', type, event);
    }
  }
}

export const ws = new WebSocketManager();
export default ws;
