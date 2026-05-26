// API integration layer matching backend endpoints

const API_BASE_URL = typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8000/api` // Direct to FastAPI port 8000
  : 'http://localhost:8000/api';

export interface User {
  id: string;
  username: string;
  email: string;
  display_name: string;
  avatar_url?: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
}

export interface Room {
  id: string;
  name: string | null;
  type: 'public' | 'private' | 'direct';
  description: string | null;
  max_members: number;
  created_by?: string;
}

export interface Message {
  message_id: number;
  room_id: string;
  sender_id: string;
  content: string;
  message_type: string;
  reply_to?: number | null;
  is_edited: boolean;
  created_at: string;
  // Local UI-only properties
  isPending?: boolean;
  isFailed?: boolean;
  reactions?: Record<string, string[]>; // emoji -> list of userIds
  isEncrypted?: boolean;
}

// Helpers for localStorage tokens
export const getStoredAuth = (): AuthState => {
  if (typeof window === 'undefined') return { user: null, accessToken: null, refreshToken: null };
  try {
    const user = localStorage.getItem('chat_user');
    const accessToken = localStorage.getItem('chat_access_token');
    const refreshToken = localStorage.getItem('chat_refresh_token');
    return {
      user: user ? JSON.parse(user) : null,
      accessToken,
      refreshToken
    };
  } catch {
    return { user: null, accessToken: null, refreshToken: null };
  }
};

export const setStoredAuth = (user: User | null, accessToken: string | null, refreshToken: string | null) => {
  if (typeof window === 'undefined') return;
  if (user) localStorage.setItem('chat_user', JSON.stringify(user));
  else localStorage.removeItem('chat_user');

  if (accessToken) localStorage.setItem('chat_access_token', accessToken);
  else localStorage.removeItem('chat_access_token');

  if (refreshToken) localStorage.setItem('chat_refresh_token', refreshToken);
  else localStorage.removeItem('chat_refresh_token');
};

const getHeaders = (token?: string | null): HeadersInit => {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  const activeToken = token || (typeof window !== 'undefined' ? localStorage.getItem('chat_access_token') : null);
  if (activeToken) {
    headers['Authorization'] = `Bearer ${activeToken}`;
  }
  return headers;
};

// Generic Fetch Wrapper
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, options);
  
  if (response.status === 204) {
    return {} as T;
  }
  
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'API request failed');
  }
  return data as T;
}

export const api = {
  // ── Authentication ──
  async register(payload: { username: string; email: string; password: string; display_name?: string }): Promise<any> {
    return request<any>('/auth/register', {
      method: 'POST',
      headers: getHeaders(null),
      body: JSON.stringify(payload)
    });
  },

  async login(payload: { email: string; password: string }): Promise<any> {
    return request<any>('/auth/login', {
      method: 'POST',
      headers: getHeaders(null),
      body: JSON.stringify(payload)
    });
  },

  async refreshToken(refreshToken: string): Promise<{ access_token: string }> {
    return request<{ access_token: string }>('/auth/refresh', {
      method: 'POST',
      headers: getHeaders(null),
      body: JSON.stringify({ refresh_token: refreshToken })
    });
  },

  async getWsToken(): Promise<{ ws_token: string }> {
    return request<{ ws_token: string }>('/auth/ws-token', {
      method: 'POST',
      headers: getHeaders()
    });
  },

  // ── Rooms ──
  async getRooms(): Promise<Room[]> {
    return request<Room[]>('/rooms/', {
      method: 'GET',
      headers: getHeaders()
    });
  },

  async createRoom(payload: { name: string; type: string; description?: string }): Promise<Room> {
    return request<Room>('/rooms/', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(payload)
    });
  },

  async joinRoom(roomId: string): Promise<any> {
    return request<any>(`/rooms/${roomId}/join`, {
      method: 'POST',
      headers: getHeaders()
    });
  },

  async leaveRoom(roomId: string): Promise<void> {
    return request<void>(`/rooms/${roomId}/leave`, {
      method: 'POST',
      headers: getHeaders()
    });
  },

  async getRoomMembers(roomId: string): Promise<Array<{ user_id: string; role: string; joined_at: string }>> {
    return request<Array<{ user_id: string; role: string; joined_at: string }>>(`/rooms/${roomId}/members`, {
      method: 'GET',
      headers: getHeaders()
    });
  },

  // ── Messages ──
  async getMessages(roomId: string, limit = 50, before?: string): Promise<Message[]> {
    let query = `?limit=${limit}`;
    if (before) query += `&before=${encodeURIComponent(before)}`;
    return request<Message[]>(`/messages/${roomId}${query}`, {
      method: 'GET',
      headers: getHeaders()
    });
  },

  async searchMessages(roomId: string, queryText: string, limit = 50): Promise<Message[]> {
    return request<Message[]>(`/messages/${roomId}/search?q=${encodeURIComponent(queryText)}&limit=${limit}`, {
      method: 'GET',
      headers: getHeaders()
    });
  },

  async editMessage(messageId: number, content: string): Promise<Message> {
    return request<Message>(`/messages/${messageId}`, {
      method: 'PATCH',
      headers: getHeaders(),
      body: JSON.stringify({ content })
    });
  },

  async deleteMessage(messageId: number): Promise<void> {
    return request<void>(`/messages/${messageId}`, {
      method: 'DELETE',
      headers: getHeaders()
    });
  }
};
