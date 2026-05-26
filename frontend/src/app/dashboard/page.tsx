'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Users, 
  Settings, 
  Globe, 
  Lock, 
  Key,
  Shield,
  Circle,
  Clock,
  Plus,
  Compass,
  User,
  Hash
} from 'lucide-react';
import { useChatStore } from '@/shared/store';
import { ws } from '@/shared/websocket';
import { api, Room } from '@/shared/api';
import Sidebar from '@/components/chat/Sidebar';
import ChatWindow from '@/components/chat/ChatWindow';
import Modal from '@/components/ui/Modal';

export default function Dashboard() {
  const router = useRouter();
  const store = useChatStore();
  const user = store.user;
  const accessToken = store.accessToken;
  const activeRoomId = store.activeRoomId;
  const roomMembers = activeRoomId ? (store.roomMembers[activeRoomId] || []) : [];
  const presenceState = store.presenceState;

  // Modal visibility states
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isCreateRoomOpen, setIsCreateRoomOpen] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  // Form states
  const [newRoomName, setNewRoomName] = useState('');
  const [newRoomType, setNewRoomType] = useState('public');
  const [newRoomDesc, setNewRoomDesc] = useState('');

  const [dmTargetName, setDmTargetName] = useState('');
  const [joinRoomId, setJoinRoomId] = useState('');
  const [publicRooms, setPublicRooms] = useState<Room[]>([]);
  const [isLoadingPublicRooms, setIsLoadingPublicRooms] = useState(false);

  // Authenticate and initialize connection
  useEffect(() => {
    if (!accessToken) {
      router.push('/auth/login');
      return;
    }

    // 1. Fetch initial rooms list
    const initRooms = async () => {
      try {
        const rooms = await api.getRooms();
        store.setRooms(rooms);
        
        // Auto-select first room
        if (rooms.length > 0 && !store.activeRoomId) {
          store.setActiveRoomId(rooms[0].id);
        }
      } catch (err) {
        store.addToast('Failed to fetch rooms', 'error');
      }
    };

    initRooms();

    // 2. Open WebSocket link
    ws.connect();

    return () => {
      ws.disconnect();
    };
  }, [accessToken, router]);

  // Load public rooms directory when search/find modal opens
  const loadPublicRooms = async () => {
    setIsLoadingPublicRooms(true);
    try {
      // Fetch rooms from backend to join
      const rooms = await api.getRooms();
      setPublicRooms(rooms);
    } catch (e) {
      store.addToast('Error fetching rooms directory', 'error');
    } finally {
      setIsLoadingPublicRooms(false);
    }
  };

  useEffect(() => {
    if (isSearchOpen) {
      loadPublicRooms();
    }
  }, [isSearchOpen]);

  // Handle Room creation submission
  const handleCreateRoom = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRoomName.trim()) return;

    try {
      const room = await api.createRoom({
        name: newRoomName.trim(),
        type: newRoomType,
        description: newRoomDesc.trim() || undefined
      });

      store.addRoom(room);
      store.setActiveRoomId(room.id);
      store.addToast(`Room #${room.name} created!`, 'success');
      
      // Notify cluster via socket
      ws.send('room.created', { room_id: room.id });

      // Reset
      setNewRoomName('');
      setNewRoomDesc('');
      setNewRoomType('public');
      setIsCreateRoomOpen(false);
    } catch (err: any) {
      store.addToast(err.message || 'Failed to create room', 'error');
    }
  };

  // Start Direct Message channel
  const handleStartDM = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dmTargetName.trim()) return;

    try {
      // In our distributed chat backend, creating a DM uses the same `/rooms/` endpoint with type='direct'
      const room = await api.createRoom({
        name: dmTargetName.trim(),
        type: 'direct',
        description: `Direct message channel with ${dmTargetName.trim()}`
      });

      store.addRoom(room);
      store.setActiveRoomId(room.id);
      store.addToast(`DM session started with ${dmTargetName.trim()}`, 'success');
      
      setDmTargetName('');
      setIsSearchOpen(false);
    } catch (err: any) {
      store.addToast(err.message || 'Failed to initiate DM session', 'error');
    }
  };

  // Join existing room
  const handleJoinRoom = async (roomIdToJoin: string) => {
    try {
      await api.joinRoom(roomIdToJoin);
      const rooms = await api.getRooms();
      store.setRooms(rooms);
      store.setActiveRoomId(roomIdToJoin);
      store.addToast('Successfully joined room', 'success');
      
      // Notify websocket peers
      ws.send('room.join', { room_id: roomIdToJoin });
      setIsSearchOpen(false);
    } catch (err: any) {
      store.addToast(err.message || 'Failed to join room', 'error');
    }
  };

  const statusColors = {
    online: 'bg-emerald-500',
    away: 'bg-amber-500',
    busy: 'bg-rose-500',
    offline: 'bg-gray-500'
  };

  return (
    <div className="flex h-screen w-screen bg-[#0f111a] overflow-hidden font-inter select-none">
      {/* Sidebar navigation */}
      <Sidebar 
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenCreateRoom={() => setIsCreateRoomOpen(true)}
        onOpenSearch={() => setIsSearchOpen(true)}
      />

      {/* Main chat interface panel */}
      <ChatWindow />

      {/* Collapsible right-hand sidebar for room members list */}
      {activeRoomId && (
        <div className="w-64 border-l border-white/5 bg-[#11131f] flex flex-col h-full shrink-0 select-none hidden lg:flex">
          <div className="h-16 border-b border-white/5 bg-[#10111a]/40 px-4 flex items-center gap-2 text-sm font-bold text-white shrink-0">
            <Users className="h-4 w-4 text-indigo-400" />
            <span>Room Members</span>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3 scrollbar-custom">
            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wide mb-1">
              Active Participants ({roomMembers.length})
            </p>
            {roomMembers.map((member) => {
              const presence = presenceState[member.user_id] || { status: 'offline' };
              const isSelf = member.user_id === user?.id;

              return (
                <div key={member.user_id} className="flex items-center gap-3 p-2 rounded-xl bg-white/[0.02] border border-white/5">
                  <div className="relative">
                    <div className="h-8 w-8 rounded-full bg-indigo-500/10 flex items-center justify-center text-indigo-400 text-xs font-bold uppercase border border-white/5">
                      {(member.username || 'U').substring(0, 2)}
                    </div>
                    {/* Presence status dot */}
                    <span className={`absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full border border-[#11131f] ${statusColors[presence.status as keyof typeof statusColors] || 'bg-gray-500'}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-gray-200 truncate flex items-center gap-1">
                      <span>{member.username || `User #${member.user_id.substring(0, 4)}`}</span>
                      {isSelf && <span className="text-[9px] text-indigo-400 font-bold bg-indigo-500/10 px-1 py-0.5 rounded">You</span>}
                    </p>
                    <p className="text-[9px] text-gray-500 font-medium capitalize mt-0.5">
                      {member.role || 'Member'}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ───── MODALS OVERLAYS ───── */}

      {/* Settings Modal (Shows Client Profile + Mock Cryptographic RSA Keypair) */}
      <Modal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} title="Security & Client Settings">
        <div className="flex flex-col gap-5 text-left">
          {/* User profile */}
          <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5 flex items-center gap-4">
            <div className="h-12 w-12 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300 font-bold text-lg uppercase">
              {user?.username?.substring(0, 2)}
            </div>
            <div>
              <h4 className="text-sm font-bold text-white">{user?.display_name || user?.username}</h4>
              <p className="text-xs text-gray-400 mt-0.5">{user?.email}</p>
              <span className="inline-block mt-2 text-[9px] font-bold bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full">
                Encrypted Client Node verified
              </span>
            </div>
          </div>

          {/* E2EE RSA Simulation detail */}
          <div className="flex flex-col gap-2.5 border-t border-white/5 pt-4">
            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
              <Shield className="h-4.5 w-4.5 text-indigo-400" />
              <span>Simulated E2E Cryptography Key-Pairs</span>
            </h4>
            <p className="text-xs text-gray-500 leading-relaxed">
              To guarantee zero-knowledge persistence in the PostgreSQL backend, client nodes simulate RSA public-private keys. Encrypted toggled messages are enciphered using Base64/RSA representation prior to socket transit.
            </p>
            
            {/* Keys Display */}
            <div className="flex flex-col gap-2 mt-2">
              <div className="bg-[#0b0c13] rounded-xl p-3 border border-white/5">
                <div className="flex items-center justify-between mb-1.5 text-[10px] text-gray-500 font-bold uppercase tracking-wider">
                  <span className="flex items-center gap-1"><Key className="h-3.5 w-3.5 text-indigo-400" /> Public RSA Key</span>
                  <span className="text-emerald-500">2048 bit</span>
                </div>
                <code className="text-[10px] text-indigo-300 break-all leading-normal font-mono select-all block h-10 overflow-y-auto pr-1">
                  ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC3eRk6Yq+VjX2lG7o8b+rL4F/WnQ99k2dM6Vl3U9p7m7t7t/y9m9m1z2w2/4... (Mock Verified Client Public Key)
                </code>
              </div>

              <div className="bg-[#0b0c13] rounded-xl p-3 border border-white/5">
                <div className="flex items-center justify-between mb-1.5 text-[10px] text-gray-500 font-bold uppercase tracking-wider">
                  <span className="flex items-center gap-1"><Lock className="h-3.5 w-3.5 text-rose-400" /> Private Decryption Key</span>
                  <span className="text-rose-400">Strictly Local</span>
                </div>
                <code className="text-[10px] text-rose-300 break-all leading-normal font-mono select-all block h-10 overflow-y-auto pr-1">
                  -----BEGIN RSA PRIVATE KEY-----&#10;MIIEowIBAAKCAQEAt3kZOmKl9pV9o... (Client Local Decryptor Key)&#10;-----END RSA PRIVATE KEY-----
                </code>
              </div>
            </div>
          </div>

          <div className="flex justify-end pt-2 border-t border-white/5">
            <button
              onClick={() => setIsSettingsOpen(false)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold cursor-pointer transition shadow-md shadow-indigo-600/10"
            >
              Close Panel
            </button>
          </div>
        </div>
      </Modal>

      {/* Create Room Modal */}
      <Modal isOpen={isCreateRoomOpen} onClose={() => setIsCreateRoomOpen(false)} title="Create New Channel">
        <form onSubmit={handleCreateRoom} className="flex flex-col gap-4 text-left">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Channel Name</label>
            <input
              type="text"
              required
              placeholder="e.g. general-chat"
              value={newRoomName}
              onChange={(e) => setNewRoomName(e.target.value)}
              className="w-full bg-[#131520] border border-white/5 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500/50 placeholder:text-gray-600"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Channel Privacy</label>
            <select
              value={newRoomType}
              onChange={(e) => setNewRoomType(e.target.value)}
              className="w-full bg-[#131520] border border-white/5 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500/50"
            >
              <option value="public">🌐 Public (Visible to all users)</option>
              <option value="private">🔒 Private (Invitation required)</option>
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Description</label>
            <textarea
              placeholder="Describe what this channel is about..."
              value={newRoomDesc}
              onChange={(e) => setNewRoomDesc(e.target.value)}
              className="w-full bg-[#131520] border border-white/5 rounded-xl px-4 py-2.5 text-sm text-white h-20 resize-none focus:outline-none focus:border-indigo-500/50 placeholder:text-gray-600"
            />
          </div>

          <div className="flex justify-end gap-2 border-t border-white/5 pt-4 mt-2">
            <button
              type="button"
              onClick={() => setIsCreateRoomOpen(false)}
              className="px-4 py-2 bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white rounded-xl text-xs font-semibold cursor-pointer transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold cursor-pointer transition shadow-md shadow-indigo-600/10"
            >
              Create Channel
            </button>
          </div>
        </form>
      </Modal>

      {/* Directory & DM modal */}
      <Modal isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} title="Explore Directory & DMs" maxWidth="max-w-lg">
        <div className="flex flex-col gap-6 text-left">
          {/* Section 1: Start DM */}
          <form onSubmit={handleStartDM} className="flex flex-col gap-2">
            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Initiate Direct Message</h4>
            <div className="flex gap-2">
              <input
                type="text"
                required
                placeholder="Enter target username..."
                value={dmTargetName}
                onChange={(e) => setDmTargetName(e.target.value)}
                className="flex-1 bg-[#131520] border border-white/5 rounded-xl px-4 py-2 text-xs text-white focus:outline-none focus:border-indigo-500/50 placeholder:text-gray-600"
              />
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition cursor-pointer"
              >
                Start DM
              </button>
            </div>
          </form>

          {/* Section 2: Rooms Directory */}
          <div className="flex flex-col gap-3 border-t border-white/5 pt-4">
            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
              <Compass className="h-4.5 w-4.5 text-indigo-400" />
              <span>Available Public Channels</span>
            </h4>
            
            <div className="max-h-60 overflow-y-auto pr-1 flex flex-col gap-2">
              {isLoadingPublicRooms ? (
                <p className="text-xs text-gray-500 text-center py-6">Loading network directory...</p>
              ) : publicRooms.filter(r => r.type === 'public').length > 0 ? (
                publicRooms.filter(r => r.type === 'public').map((room) => {
                  const isJoined = store.rooms.some(r => r.id === room.id);
                  return (
                    <div key={room.id} className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/5">
                      <div className="min-w-0">
                        <p className="text-xs font-bold text-white flex items-center gap-1">
                          <Hash className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
                          <span className="truncate">{room.name}</span>
                        </p>
                        {room.description && (
                          <p className="text-[10px] text-gray-400 truncate mt-0.5">{room.description}</p>
                        )}
                      </div>
                      <button
                        onClick={() => handleJoinRoom(room.id)}
                        disabled={isJoined}
                        className={`px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wide cursor-pointer transition ${
                          isJoined 
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 cursor-default'
                            : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm'
                        }`}
                      >
                        {isJoined ? 'Joined' : 'Join'}
                      </button>
                    </div>
                  );
                })
              ) : (
                <p className="text-xs text-gray-500 text-center py-6 italic">No public channels found.</p>
              )}
            </div>
          </div>

          <div className="flex justify-end border-t border-white/5 pt-4">
            <button
              onClick={() => setIsSearchOpen(false)}
              className="px-4 py-2 bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white rounded-xl text-xs font-semibold cursor-pointer transition"
            >
              Close
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
