'use client';

import { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Smile, 
  Lock, 
  LockOpen, 
  X, 
  Paperclip 
} from 'lucide-react';
import { Message } from '@/shared/api';
import { useChatStore } from '@/shared/store';
import { ws } from '@/shared/websocket';

interface MessageInputProps {
  replyToMessage: Message | null;
  onClearReply: () => void;
}

export default function MessageInput({ replyToMessage, onClearReply }: MessageInputProps) {
  const store = useChatStore();
  const roomId = store.activeRoomId;
  const isE2EActive = store.isE2EActive;
  const toggleE2E = store.toggleE2E;

  const [text, setText] = useState('');
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const typingTimeoutRef = useRef<any>(null);
  const isTypingRef = useRef(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when room changes or replying
  useEffect(() => {
    inputRef.current?.focus();
  }, [roomId, replyToMessage]);

  // Handle typing status notification
  const handleKeyDown = () => {
    if (!roomId) return;

    if (!isTypingRef.current) {
      isTypingRef.current = true;
      ws.send('typing.indicator', { room_id: roomId, is_typing: true });
    }

    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    typingTimeoutRef.current = setTimeout(() => {
      isTypingRef.current = false;
      ws.send('typing.indicator', { room_id: roomId, is_typing: false });
    }, 2000);
  };

  // Clean up typing timeout
  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, []);

  const handleSend = () => {
    if (!text.trim() || !roomId) return;

    // Encrypt content locally if E2E simulation is active
    let finalContent = text;
    let messageType = 'text';

    if (isE2EActive) {
      finalContent = `E2E::${btoa(text)}`;
      messageType = 'encrypted';
    }

    // Send payload over WebSocket
    ws.send('message.send', {
      room_id: roomId,
      content: finalContent,
      message_type: messageType,
      reply_to: replyToMessage?.message_id || null
    });

    // Reset fields
    setText('');
    onClearReply();
    setShowEmojiPicker(false);

    // Stop typing indicator
    if (isTypingRef.current) {
      isTypingRef.current = false;
      ws.send('typing.indicator', { room_id: roomId, is_typing: false });
      if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
    }
  };

  const handleEmojiClick = (emoji: string) => {
    setText((prev) => prev + emoji);
    setShowEmojiPicker(false);
    inputRef.current?.focus();
  };

  const popularEmojis = ['👍', '❤️', '🔥', '😂', '😮', '🎉', '💡', '✅', '🚀', '✨'];

  if (!roomId) return null;

  return (
    <div className="flex flex-col border-t border-white/5 bg-[#10111a]/40 p-4 shrink-0 select-none">
      {/* 1. Reply to banner indicator */}
      {replyToMessage && (
        <div className="flex items-center justify-between bg-indigo-500/10 border border-indigo-500/20 rounded-xl px-4 py-2 mb-3 text-xs">
          <div className="flex items-center gap-1.5 text-gray-300">
            <span>Replying to message:</span>
            <span className="font-semibold text-indigo-400">
              {replyToMessage.content.startsWith('E2E::') ? '🔒 (Encrypted)' : replyToMessage.content.substring(0, 40)}
            </span>
          </div>
          <button 
            onClick={onClearReply}
            className="text-gray-400 hover:text-white transition cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* 2. Controls & Form Input */}
      <div className="flex items-center gap-3 relative">
        {/* Toggle E2EE Simulation lock button */}
        <button
          onClick={toggleE2E}
          className={`flex items-center justify-center h-10 w-10 rounded-xl border transition-all cursor-pointer ${
            isE2EActive
              ? 'bg-indigo-600/20 border-indigo-500/50 text-indigo-400 shadow-[0_0_12px_rgba(99,102,241,0.2)]'
              : 'bg-[#151724] border-white/5 text-gray-500 hover:text-gray-300'
          }`}
          title={isE2EActive ? 'E2EE client-encryption active (Stored as cipher)' : 'Activate E2EE client-encryption'}
        >
          {isE2EActive ? <Lock className="h-5 w-5" /> : <LockOpen className="h-5 w-5" />}
        </button>

        {/* Emoji Button */}
        <div className="relative">
          <button
            onClick={() => setShowEmojiPicker(!showEmojiPicker)}
            className="flex items-center justify-center h-10 w-10 rounded-xl bg-[#151724] border border-white/5 text-gray-400 hover:text-white transition cursor-pointer"
            title="Insert Emoji"
          >
            <Smile className="h-5 w-5" />
          </button>

          {/* Inline Emoji Selector Popup */}
          {showEmojiPicker && (
            <>
              <div className="fixed inset-0 z-20" onClick={() => setShowEmojiPicker(false)} />
              <div className="absolute bottom-12 left-0 z-30 bg-[#161825] border border-white/5 rounded-2xl p-3 shadow-2xl flex flex-wrap gap-2 w-48 animate-slide-up">
                {popularEmojis.map((emoji) => (
                  <button
                    key={emoji}
                    onClick={() => handleEmojiClick(emoji)}
                    className="hover:scale-125 transition text-lg cursor-pointer p-1"
                  >
                    {emoji}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Text Input area */}
        <div className="flex-1 relative">
          <input
            ref={inputRef}
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              handleKeyDown();
              if (e.key === 'Enter') handleSend();
            }}
            placeholder={
              isE2EActive
                ? 'Send encrypted chat message (E2EE)...'
                : 'Send general chat message...'
            }
            className="w-full bg-[#131520]/80 glass-input text-sm text-white pl-4 pr-10 py-3 rounded-xl border border-white/5 focus:outline-none focus:border-indigo-500/50 placeholder:text-gray-500"
          />
        </div>

        {/* Send Button */}
        <button
          onClick={handleSend}
          disabled={!text.trim()}
          className={`flex items-center justify-center h-10 w-10 rounded-xl transition-all cursor-pointer ${
            text.trim()
              ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20'
              : 'bg-[#151724] border border-white/5 text-gray-600 cursor-not-allowed'
          }`}
        >
          <Send className="h-4.5 w-4.5" />
        </button>
      </div>
    </div>
  );
}
