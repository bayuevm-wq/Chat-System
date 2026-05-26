'use client';

import { useState, useEffect, useRef } from 'react';
import { 
  Search, 
  Users, 
  Hash, 
  AlertTriangle, 
  ArrowDown, 
  X,
  Calendar,
  Lock,
  Loader
} from 'lucide-react';
import { useChatStore } from '@/shared/store';
import { api, Message } from '@/shared/api';
import MessageBubble from './MessageBubble';
import MessageInput from './MessageInput';

export default function ChatWindow() {
  const store = useChatStore();
  const activeRoomId = store.activeRoomId;
  const messages = activeRoomId ? (store.messages[activeRoomId] || []) : [];
  const connectionStatus = store.connectionStatus;
  const currentRoom = store.rooms.find(r => r.id === activeRoomId);
  const typingUsers = activeRoomId ? (store.typingUsers[activeRoomId] || []) : [];
  const roomMembers = activeRoomId ? (store.roomMembers[activeRoomId] || []) : [];

  const [isLoading, setIsLoading] = useState(false);
  const [isPaginationLoading, setIsPaginationLoading] = useState(false);
  const [hasMoreMessages, setHasMoreMessages] = useState(true);
  const [replyToMessage, setReplyToMessage] = useState<Message | null>(null);
  
  // Search state
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Message[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Scroll references
  const chatEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollBottomBtn, setShowScrollBottomBtn] = useState(false);

  // Load initial room data
  useEffect(() => {
    if (!activeRoomId) return;

    setReplyToMessage(null);
    setHasMoreMessages(true);
    setIsSearchOpen(false);
    setSearchQuery('');
    setSearchResults([]);

    const fetchRoomData = async () => {
      setIsLoading(true);
      try {
        // Fetch last 50 messages
        const msgs = await api.getMessages(activeRoomId, 50);
        store.setMessages(activeRoomId, msgs);
        if (msgs.length < 50) {
          setHasMoreMessages(false);
        }

        // Fetch room members
        const members = await api.getRoomMembers(activeRoomId);
        store.setRoomMembers(activeRoomId, members);
      } catch (err: any) {
        store.addToast('Error loading conversation history', 'error');
      } finally {
        setIsLoading(false);
        // Instant scroll to bottom on load
        setTimeout(scrollToBottom, 50);
      }
    };

    fetchRoomData();
  }, [activeRoomId]);

  // Handle scroll detection for loading older history
  const handleScroll = async () => {
    const container = chatContainerRef.current;
    if (!container || !activeRoomId) return;

    // Show or hide "Scroll to bottom" helper button
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 300;
    setShowScrollBottomBtn(!isNearBottom);

    // If scrolled to top and has more history, paginate
    if (container.scrollTop === 0 && hasMoreMessages && !isPaginationLoading && !isLoading) {
      if (messages.length === 0) return;
      
      setIsPaginationLoading(true);
      const beforeTimestamp = messages[0].created_at;
      const originalScrollHeight = container.scrollHeight;

      try {
        const olderMsgs = await api.getMessages(activeRoomId, 50, beforeTimestamp);
        
        if (olderMsgs.length < 50) {
          setHasMoreMessages(false);
        }

        if (olderMsgs.length > 0) {
          store.setMessages(activeRoomId, [...olderMsgs, ...messages]);
          
          // Adjust scroll position so it doesn't jump
          setTimeout(() => {
            if (chatContainerRef.current) {
              chatContainerRef.current.scrollTop = 
                chatContainerRef.current.scrollHeight - originalScrollHeight;
            }
          }, 0);
        }
      } catch (err) {
        store.addToast('Error fetching older messages', 'error');
      } finally {
        setIsPaginationLoading(false);
      }
    }
  };

  // Scroll helpers
  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Auto-scroll on new messages if close to bottom
  useEffect(() => {
    const container = chatContainerRef.current;
    if (!container) return;

    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 200;
    if (isNearBottom || messages.some(m => m.sender_id === store.user?.id && m.isPending)) {
      scrollToBottom();
    }
  }, [messages]);

  // Execute database Full-Text Search
  const handleSearch = async () => {
    if (!searchQuery.trim() || !activeRoomId) return;
    setIsSearching(true);
    try {
      const results = await api.searchMessages(activeRoomId, searchQuery);
      setSearchResults(results);
    } catch (err) {
      store.addToast('Failed to perform chat history search', 'error');
    } finally {
      setIsSearching(false);
    }
  };

  const getSenderName = (senderId: string) => {
    const member = roomMembers.find(m => m.user_id === senderId);
    return member?.username || 'Unknown User';
  };

  // Format typing notice text
  const getTypingText = () => {
    if (typingUsers.length === 0) return '';
    if (typingUsers.length === 1) return `${typingUsers[0]} is typing...`;
    if (typingUsers.length === 2) return `${typingUsers[0]} and ${typingUsers[1]} are typing...`;
    return 'Several people are typing...';
  };

  if (!activeRoomId) {
    return (
      <div className="flex-1 h-full bg-[#0f111a] flex flex-col items-center justify-center text-center p-8 select-none">
        <div className="h-16 w-16 rounded-3xl bg-indigo-500/10 flex items-center justify-center text-indigo-400 mb-6 border border-indigo-500/20 shadow-[0_0_20px_rgba(99,102,241,0.1)]">
          <Hash className="h-8 w-8" />
        </div>
        <h2 className="text-xl font-bold text-white mb-2">Welcome to Node Chat</h2>
        <p className="text-sm text-gray-500 max-w-sm leading-relaxed">
          Select an active server room or query users from the directory on the left to initialize real-time messaging.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 h-full bg-[#0f111a] flex overflow-hidden">
      {/* Main Conversation Pane */}
      <div className="flex-1 h-full flex flex-col min-w-0 bg-[#0e0f17]">
        {/* Header toolbar */}
        <div className="h-16 border-b border-white/5 bg-[#10111a]/40 px-6 flex items-center justify-between shrink-0 select-none">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-indigo-500/15 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Hash className="h-4.5 w-4.5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white truncate max-w-[200px]">
                {currentRoom?.name || 'Conversation'}
              </h2>
              {currentRoom?.description && (
                <p className="text-xs text-gray-400 truncate max-w-[300px] mt-0.5">
                  {currentRoom.description}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Search toggler */}
            <button
              onClick={() => setIsSearchOpen(!isSearchOpen)}
              className={`p-2 rounded-xl border transition-colors cursor-pointer ${
                isSearchOpen 
                  ? 'bg-indigo-600 border-indigo-500 text-white' 
                  : 'bg-[#151724] border-white/5 text-gray-400 hover:text-white hover:bg-white/5'
              }`}
              title="Search Messages"
            >
              <Search className="h-4.5 w-4.5" />
            </button>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#151724] border border-white/5 text-gray-400 text-xs font-semibold">
              <Users className="h-4 w-4" />
              <span>{roomMembers.length} members</span>
            </div>
          </div>
        </div>

        {/* Network connection warnings */}
        {connectionStatus !== 'connected' && (
          <div className={`px-4 py-2 border-b flex items-center justify-center gap-2 text-xs font-semibold select-none ${
            connectionStatus === 'connecting' 
              ? 'bg-amber-500/10 border-amber-500/20 text-amber-300' 
              : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
          }`}>
            <AlertTriangle className="h-4 w-4 animate-pulse shrink-0" />
            <span>
              {connectionStatus === 'connecting' 
                ? 'Lost socket bridge connection. Attempting exponential reconnection...' 
                : 'Connection unavailable. Offline message buffer activated.'}
            </span>
          </div>
        )}

        {/* Messages Stream Timeline */}
        <div 
          ref={chatContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto px-6 py-4 scrollbar-custom"
        >
          {/* Pagination Loader */}
          {isPaginationLoading && (
            <div className="flex justify-center items-center py-4 text-indigo-400">
              <Loader className="h-5 w-5 animate-spin" />
            </div>
          )}

          {isLoading ? (
            <div className="h-full w-full flex items-center justify-center flex-col gap-3 text-indigo-400">
              <Loader className="h-8 w-8 animate-spin" />
              <p className="text-xs text-gray-500 font-semibold tracking-wide">Syncing message history...</p>
            </div>
          ) : (
            <>
              {messages.map((msg, index) => {
                // Find matching reply reference if any
                const replyRef = msg.reply_to 
                  ? messages.find(m => m.message_id === msg.reply_to) 
                  : null;

                return (
                  <MessageBubble
                    key={msg.message_id || msg.created_at}
                    message={msg}
                    senderName={getSenderName(msg.sender_id)}
                    isSelf={msg.sender_id === store.user?.id}
                    onReply={(m) => setReplyToMessage(m)}
                    replyToMessage={replyRef}
                  />
                );
              })}
              
              {messages.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-center p-8 select-none">
                  <p className="text-sm text-gray-500 italic">No messages in this room. Say hello!</p>
                </div>
              )}
              
              <div ref={chatEndRef} />
            </>
          )}
        </div>

        {/* Real-time typing notices banner */}
        <div className="h-5 px-6 text-xs text-indigo-400 italic select-none">
          {getTypingText()}
        </div>

        {/* Floating Scroll Bottom Helper */}
        {showScrollBottomBtn && (
          <button
            onClick={scrollToBottom}
            className="absolute bottom-24 right-8 bg-indigo-600 hover:bg-indigo-500 text-white rounded-full p-2.5 shadow-xl hover:scale-105 transition-all z-10 cursor-pointer border border-indigo-500/20"
          >
            <ArrowDown className="h-5 w-5" />
          </button>
        )}

        {/* Interactive message entry controller */}
        <MessageInput 
          replyToMessage={replyToMessage}
          onClearReply={() => setReplyToMessage(null)}
        />
      </div>

      {/* Collapsible database Search Results Panel */}
      {isSearchOpen && (
        <div className="w-80 border-l border-white/5 bg-[#12131e] flex flex-col h-full shrink-0 select-none">
          <div className="h-16 border-b border-white/5 bg-[#10111a]/40 px-4 flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
              <Search className="h-4 w-4 text-indigo-400" />
              <span>Full-Text Search</span>
            </h3>
            <button 
              onClick={() => setIsSearchOpen(false)}
              className="text-gray-400 hover:text-white p-1 rounded-lg transition"
            >
              <X className="h-4.5 w-4.5" />
            </button>
          </div>

          <div className="p-4 border-b border-white/5 flex gap-2">
            <input
              type="text"
              placeholder="Search chat history..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="flex-1 bg-[#0e0f17] text-xs text-white rounded-lg px-3 py-2 border border-white/5 focus:outline-none focus:border-indigo-500/50"
            />
            <button
              onClick={handleSearch}
              className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition"
            >
              Go
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
            {isSearching ? (
              <div className="flex flex-col gap-2 items-center justify-center py-8 text-indigo-400">
                <Loader className="h-5 w-5 animate-spin" />
                <span className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider">Searching node DB...</span>
              </div>
            ) : searchResults.length > 0 ? (
              searchResults.map((result) => {
                const isEnc = result.message_type === 'encrypted';
                let content = result.content;
                if (isEnc && content.startsWith('E2E::')) {
                  try {
                    content = atob(content.substring(5));
                  } catch (e) {}
                }
                return (
                  <div key={result.message_id} className="p-3 bg-[#151724]/90 border border-white/5 rounded-xl flex flex-col gap-1.5">
                    <div className="flex justify-between items-center text-[10px] text-gray-500">
                      <span className="font-semibold text-indigo-300">{getSenderName(result.sender_id)}</span>
                      <span>{new Date(result.created_at).toLocaleDateString()}</span>
                    </div>
                    <p className="text-xs text-gray-200 leading-normal line-clamp-3">{content}</p>
                    {isEnc && (
                      <span className="flex items-center gap-0.5 text-[9px] text-indigo-400 font-semibold self-end">
                        <Lock className="h-2.5 w-2.5" />
                        <span>Decrypted</span>
                      </span>
                    )}
                  </div>
                );
              })
            ) : searchQuery ? (
              <p className="text-xs text-gray-500 text-center py-8 italic">No records match your query.</p>
            ) : (
              <p className="text-xs text-gray-500 text-center py-8">
                Enter keywords above to query matching message content via index search.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
