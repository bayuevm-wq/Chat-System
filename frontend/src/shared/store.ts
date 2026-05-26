import { create } from 'zustand';
import { User, Room, Message, getStoredAuth, setStoredAuth } from './api';

export interface ToastMessage {
  id: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
}

interface ChatStore {
  // ── Authentication ──
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticating: boolean;
  login: (user: User, accessToken: string, refreshToken: string) => void;
  logout: () => void;

  // ── Connection ──
  connectionStatus: 'connected' | 'disconnected' | 'connecting';
  setConnectionStatus: (status: 'connected' | 'disconnected' | 'connecting') => void;

  // ── Rooms ──
  rooms: Room[];
  activeRoomId: string | null;
  roomMembers: Record<string, Array<{ user_id: string; role: string; username?: string; display_name?: string }>>;
  setRooms: (rooms: Room[]) => void;
  addRoom: (room: Room) => void;
  setActiveRoomId: (roomId: string | null) => void;
  setRoomMembers: (roomId: string, members: any[]) => void;

  // ── Messages ──
  messages: Record<string, Message[]>; // roomId -> messages
  setMessages: (roomId: string, messages: Message[]) => void;
  addMessage: (roomId: string, message: Message) => void;
  updateMessage: (roomId: string, messageId: number, updates: Partial<Message>) => void;
  removeMessage: (roomId: string, messageId: number) => void;
  addReaction: (roomId: string, messageId: number, emoji: string, userId: string) => void;

  // ── Typing ──
  typingUsers: Record<string, string[]>; // roomId -> list of usernames
  setTyping: (roomId: string, username: string, isTyping: boolean) => void;

  // ── Presence ──
  presenceState: Record<string, { status: 'online' | 'away' | 'busy' | 'offline'; last_seen_at?: string | null }>;
  updateUserPresence: (userId: string, status: 'online' | 'away' | 'busy' | 'offline', lastSeen?: string | null) => void;

  // ── Toasts ──
  toasts: ToastMessage[];
  addToast: (message: string, type?: ToastMessage['type']) => void;
  removeToast: (id: string) => void;

  // ── Advanced Options ──
  isE2EActive: boolean;
  toggleE2E: () => void;
}

const initialAuth = getStoredAuth();

export const useChatStore = create<ChatStore>((set, get) => ({
  // Auth state
  user: initialAuth.user,
  accessToken: initialAuth.accessToken,
  refreshToken: initialAuth.refreshToken,
  isAuthenticating: false,
  login: (user, accessToken, refreshToken) => {
    setStoredAuth(user, accessToken, refreshToken);
    set({ user, accessToken, refreshToken });
  },
  logout: () => {
    setStoredAuth(null, null, null);
    set({ user: null, accessToken: null, refreshToken: null, activeRoomId: null, rooms: [], messages: {} });
  },

  // Connection state
  connectionStatus: 'disconnected',
  setConnectionStatus: (status) => set({ connectionStatus: status }),

  // Rooms state
  rooms: [],
  activeRoomId: null,
  roomMembers: {},
  setRooms: (rooms) => set({ rooms }),
  addRoom: (room) => set((state) => {
    // Avoid duplicates
    if (state.rooms.some(r => r.id === room.id)) return {};
    return { rooms: [...state.rooms, room] };
  }),
  setActiveRoomId: (roomId) => set({ activeRoomId: roomId }),
  setRoomMembers: (roomId, members) => set((state) => ({
    roomMembers: { ...state.roomMembers, [roomId]: members }
  })),

  // Messages state
  messages: {},
  setMessages: (roomId, msgs) => set((state) => ({
    messages: { ...state.messages, [roomId]: msgs }
  })),
  addMessage: (roomId, message) => set((state) => {
    const roomMsgs = state.messages[roomId] || [];
    // Prevent duplicate entries
    if (roomMsgs.some(m => m.message_id === message.message_id && message.message_id > 0)) {
      return {};
    }
    return {
      messages: {
        ...state.messages,
        [roomId]: [...roomMsgs, message]
      }
    };
  }),
  updateMessage: (roomId, messageId, updates) => set((state) => {
    const roomMsgs = state.messages[roomId] || [];
    return {
      messages: {
        ...state.messages,
        [roomId]: roomMsgs.map(m => m.message_id === messageId ? { ...m, ...updates } : m)
      }
    };
  }),
  removeMessage: (roomId, messageId) => set((state) => {
    const roomMsgs = state.messages[roomId] || [];
    return {
      messages: {
        ...state.messages,
        [roomId]: roomMsgs.filter(m => m.message_id !== messageId)
      }
    };
  }),
  addReaction: (roomId, messageId, emoji, userId) => set((state) => {
    const roomMsgs = state.messages[roomId] || [];
    const updated = roomMsgs.map(m => {
      if (m.message_id !== messageId) return m;
      const reactions = { ...(m.reactions || {}) };
      const users = [...(reactions[emoji] || [])];
      
      if (users.includes(userId)) {
        // Toggle off if already reacted
        reactions[emoji] = users.filter(u => u !== userId);
        if (reactions[emoji].length === 0) delete reactions[emoji];
      } else {
        reactions[emoji] = [...users, userId];
      }
      return { ...m, reactions };
    });
    return {
      messages: { ...state.messages, [roomId]: updated }
    };
  }),

  // Typing state
  typingUsers: {},
  setTyping: (roomId, username, isTyping) => set((state) => {
    const current = state.typingUsers[roomId] || [];
    const updated = isTyping
      ? current.includes(username) ? current : [...current, username]
      : current.filter(name => name !== username);
    return {
      typingUsers: { ...state.typingUsers, [roomId]: updated }
    };
  }),

  // Presence state
  presenceState: {},
  updateUserPresence: (userId, status, lastSeen = null) => set((state) => ({
    presenceState: {
      ...state.presenceState,
      [userId]: { status, last_seen_at: lastSeen }
    }
  })),

  // Toast state
  toasts: [],
  addToast: (message, type = 'info') => set((state) => {
    const id = Math.random().toString(36).substring(7);
    return {
      toasts: [...state.toasts, { id, message, type }]
    };
  }),
  removeToast: (id) => set((state) => ({
    toasts: state.toasts.filter(t => t.id !== id)
  })),

  // E2E encryption toggle
  isE2EActive: false,
  toggleE2E: () => set((state) => ({ isE2EActive: !state.isE2EActive }))
}));
