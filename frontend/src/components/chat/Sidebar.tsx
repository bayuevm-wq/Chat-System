'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  LogOut, 
  Settings, 
  User as UserIcon, 
  MessageSquare, 
  Circle, 
  ChevronDown, 
  Globe, 
  UserCheck 
} from 'lucide-react';
import { useChatStore } from '@/shared/store';
import { ws } from '@/shared/websocket';

interface SidebarProps {
  onOpenSettings: () => void;
  onOpenCreateRoom: () => void;
  onOpenSearch: () => void;
}

export default function Sidebar({ onOpenSettings, onOpenCreateRoom, onOpenSearch }: SidebarProps) {
  const user = useChatStore((state) => state.user);
  const logout = useChatStore((state) => state.logout);
  const rooms = useChatStore((state) => state.rooms);
  const activeRoomId = useChatStore((state) => state.activeRoomId);
  const setActiveRoomId = useChatStore((state) => state.setActiveRoomId);
  const connectionStatus = useChatStore((state) => state.connectionStatus);

  const [statusOpen, setStatusOpen] = useState(false);
  const [currentStatus, setCurrentStatus] = useState<'online' | 'away' | 'busy' | 'offline'>('online');

  const handleStatusChange = (status: 'online' | 'away' | 'busy' | 'offline') => {
    setCurrentStatus(status);
    setStatusOpen(false);
    // Send presence.update WebSocket event
    ws.send('presence.update', { status });
  };

  const handleLogout = () => {
    ws.disconnect();
    logout();
  };

  const statusConfig = {
    online: { color: 'text-emerald-500', bg: 'bg-emerald-500', label: 'Online' },
    away: { color: 'text-amber-500', bg: 'bg-amber-500', label: 'Away' },
    busy: { color: 'text-rose-500', bg: 'bg-rose-500', label: 'Do Not Disturb' },
    offline: { color: 'text-gray-400', bg: 'bg-gray-400', label: 'Invisible' },
  };

  return (
    <div className="flex flex-col w-72 h-full bg-[#131520] border-r border-white/5 shrink-0 select-none">
      {/* 1. Header node info */}
      <div className="flex items-center justify-between p-4 border-b border-white/5 bg-[#10111a]/40">
        <div className="flex items-center gap-2.5">
          <div className="h-2.5 w-2.5 rounded-full bg-indigo-500 shadow-[0_0_10px_rgba(99,102,241,0.5)]"></div>
          <h1 className="font-bold tracking-wider text-white text-sm">CHAT NODECLUSTER</h1>
        </div>
        <div className="flex items-center gap-1.5">
          {/* Connection Status indicator */}
          <span className={`h-2 w-2 rounded-full ${
            connectionStatus === 'connected' ? 'bg-emerald-500' :
            connectionStatus === 'connecting' ? 'bg-amber-500 animate-pulse' : 'bg-rose-500'
          }`} />
          <span className="text-[10px] text-gray-400 font-semibold tracking-wider uppercase">{connectionStatus}</span>
        </div>
      </div>

      {/* 2. Chat Rooms List */}
      <div className="flex-1 overflow-y-auto px-3 py-4 flex flex-col gap-6">
        <div>
          <div className="flex items-center justify-between px-2 mb-2 text-xs font-bold text-gray-500 tracking-wider uppercase">
            <span>Rooms / Channels</span>
            <button 
              onClick={onOpenCreateRoom}
              className="text-gray-400 hover:text-white transition-colors cursor-pointer text-base font-normal"
            >
              +
            </button>
          </div>
          <div className="flex flex-col gap-0.5">
            {rooms.filter(r => r.type !== 'direct').map((room) => {
              const isActive = room.id === activeRoomId;
              return (
                <button
                  key={room.id}
                  onClick={() => setActiveRoomId(room.id)}
                  className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 cursor-pointer ${
                    isActive 
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/10' 
                      : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                  }`}
                >
                  <Globe className={`h-4.5 w-4.5 ${isActive ? 'text-white' : 'text-gray-500'}`} />
                  <span className="truncate">{room.name}</span>
                </button>
              );
            })}
            {rooms.filter(r => r.type !== 'direct').length === 0 && (
              <p className="text-xs text-gray-500 text-center py-4 italic">No rooms joined yet.</p>
            )}
          </div>
        </div>

        {/* 3. Direct Messages */}
        <div>
          <div className="flex items-center justify-between px-2 mb-2 text-xs font-bold text-gray-500 tracking-wider uppercase">
            <span>Direct Messages</span>
            <button 
              onClick={onOpenSearch}
              className="text-gray-400 hover:text-white transition-colors cursor-pointer text-xs font-normal"
            >
              Find
            </button>
          </div>
          <div className="flex flex-col gap-0.5">
            {rooms.filter(r => r.type === 'direct').map((room) => {
              const isActive = room.id === activeRoomId;
              return (
                <button
                  key={room.id}
                  onClick={() => setActiveRoomId(room.id)}
                  className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 cursor-pointer ${
                    isActive 
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/10' 
                      : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                  }`}
                >
                  <UserCheck className={`h-4.5 w-4.5 ${isActive ? 'text-white' : 'text-gray-500'}`} />
                  <span className="truncate">{room.name || 'Direct Chat'}</span>
                </button>
              );
            })}
            {rooms.filter(r => r.type === 'direct').length === 0 && (
              <p className="text-xs text-gray-500 text-center py-4 italic">No direct chats started.</p>
            )}
          </div>
        </div>
      </div>

      {/* 4. User Footer Profile card */}
      <div className="relative border-t border-white/5 p-4 bg-[#0d0e16]/60">
        <div className="flex items-center justify-between gap-3">
          {/* Avatar with dynamic status indicator */}
          <div className="relative cursor-pointer" onClick={() => setStatusOpen(!statusOpen)}>
            <div className="h-10 w-10 rounded-full bg-indigo-500/10 border border-white/10 flex items-center justify-center text-indigo-400 font-bold uppercase text-sm">
              {user?.username?.substring(0, 2)}
            </div>
            {/* Status dot */}
            <span className={`absolute bottom-0 right-0 h-3 w-3 rounded-full border-2 border-[#131520] ${statusConfig[currentStatus].bg}`} />
          </div>

          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-white truncate">{user?.display_name || user?.username}</p>
            <button 
              onClick={() => setStatusOpen(!statusOpen)}
              className="flex items-center gap-1 text-[11px] font-medium text-gray-400 hover:text-gray-200 cursor-pointer mt-0.5"
            >
              <span>{statusConfig[currentStatus].label}</span>
              <ChevronDown className="h-3 w-3" />
            </button>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-1 text-gray-400">
            <button 
              onClick={onOpenSettings}
              className="p-1.5 rounded-lg hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
              title="Settings"
            >
              <Settings className="h-4.5 w-4.5" />
            </button>
            <button 
              onClick={handleLogout}
              className="p-1.5 rounded-lg hover:text-rose-400 hover:bg-rose-500/5 transition-colors cursor-pointer"
              title="Logout"
            >
              <LogOut className="h-4.5 w-4.5" />
            </button>
          </div>
        </div>

        {/* Status Dropdown Modal */}
        {statusOpen && (
          <>
            <div className="fixed inset-0 z-20" onClick={() => setStatusOpen(false)} />
            <div className="absolute bottom-16 left-4 z-30 w-48 rounded-xl border border-white/5 bg-[#171926] p-1.5 shadow-2xl animate-slide-up">
              <p className="text-[10px] font-bold text-gray-500 px-3 py-1.5 uppercase tracking-wide">Set Status</p>
              {(Object.keys(statusConfig) as Array<keyof typeof statusConfig>).map((status) => (
                <button
                  key={status}
                  onClick={() => handleStatusChange(status)}
                  className="flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-xs font-medium text-gray-300 hover:text-white hover:bg-white/5 transition-all text-left cursor-pointer"
                >
                  <Circle className={`h-3 w-3 fill-current ${statusConfig[status].color}`} />
                  <span>{statusConfig[status].label}</span>
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
