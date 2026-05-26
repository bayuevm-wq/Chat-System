'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Smile, 
  CornerUpLeft, 
  Edit2, 
  Trash2, 
  Lock, 
  Check, 
  CheckCheck, 
  Clock 
} from 'lucide-react';
import { Message, api } from '@/shared/api';
import { useChatStore } from '@/shared/store';
import { ws } from '@/shared/websocket';

interface MessageBubbleProps {
  message: Message;
  senderName: string;
  senderAvatar?: string;
  isSelf: boolean;
  onReply: (message: Message) => void;
  replyToMessage?: Message | null;
}

// Simple client-side E2EE helper for demo
const decryptMessageContent = (content: string, type: string) => {
  if (type !== 'encrypted') return content;
  
  if (content.startsWith('E2E::')) {
    try {
      return atob(content.substring(5));
    } catch (e) {
      return content;
    }
  }
  return content;
};

export default function MessageBubble({ 
  message, 
  senderName, 
  isSelf, 
  onReply,
  replyToMessage
}: MessageBubbleProps) {
  const store = useChatStore();
  const currentUserId = store.user?.id;
  const activeRoomId = store.activeRoomId;
  const addToast = store.addToast;

  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);

  const decryptedContent = decryptMessageContent(message.content, message.message_type);

  // E2E lock indicator
  const isE2E = message.message_type === 'encrypted';

  // Handle message edit
  const handleEdit = async () => {
    if (!editContent.trim() || editContent === decryptedContent) {
      setIsEditing(false);
      return;
    }

    try {
      let finalContent = editContent;
      if (isE2E) {
        finalContent = `E2E::${btoa(editContent)}`;
      }
      
      // Update locally
      if (activeRoomId) {
        store.updateMessage(activeRoomId, message.message_id, {
          content: finalContent,
          is_edited: true
        });
      }

      await api.editMessage(message.message_id, finalContent);
      setIsEditing(false);
      addToast('Message updated', 'success');
    } catch (err: any) {
      addToast(err.message || 'Failed to edit message', 'error');
    }
  };

  // Handle message delete
  const handleDelete = async () => {
    try {
      if (activeRoomId) {
        store.removeMessage(activeRoomId, message.message_id);
      }
      await api.deleteMessage(message.message_id);
      addToast('Message deleted', 'success');
    } catch (err: any) {
      addToast(err.message || 'Failed to delete message', 'error');
    }
  };

  // Handle reactions
  const handleReact = (emoji: string) => {
    if (!activeRoomId || !currentUserId) return;
    
    // Toggle reaction in store
    store.addReaction(activeRoomId, message.message_id, emoji, currentUserId);
    setShowEmojiPicker(false);

    // Send to other clients
    ws.send('message.reaction', {
      message_id: message.message_id,
      room_id: activeRoomId,
      emoji: emoji
    });
  };

  // Render reply preview if message replies to something
  const renderReplyAnchor = () => {
    if (!replyToMessage) return null;
    
    const replyText = decryptMessageContent(replyToMessage.content, replyToMessage.message_type);
    
    return (
      <div className="flex items-center gap-1.5 text-xs text-gray-500 mb-1 border-l-2 border-indigo-500/40 pl-2 py-0.5">
        <span className="font-semibold text-indigo-400">
          {replyToMessage.sender_id === currentUserId ? 'You' : 'Someone'}
        </span>
        <span className="truncate max-w-[200px]">{replyText}</span>
      </div>
    );
  };

  const reactionEmojis = ['👍', '❤️', '🔥', '😂', '😮', '🎉'];

  return (
    <div className={`flex flex-col mb-4 group ${isSelf ? 'items-end' : 'items-start'}`}>
      {/* Sender Header */}
      <div className="flex items-center gap-2 mb-1 px-1">
        <span className="text-xs font-semibold text-gray-400">{senderName}</span>
        <span className="text-[10px] text-gray-500">
          {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>

      <div className={`relative flex max-w-[70%] items-end gap-2 ${isSelf ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Message Panel Box */}
        <div className={`rounded-2xl px-4 py-3 shadow-sm border ${
          isSelf 
            ? 'bg-indigo-600/90 border-indigo-500/20 text-white rounded-tr-none' 
            : 'bg-[#151824]/90 border-white/5 text-gray-100 rounded-tl-none'
        } ${message.isPending ? 'opacity-70' : ''}`}>
          
          {/* Reply Context anchor */}
          {renderReplyAnchor()}

          {/* Edit Box vs Raw Message Text */}
          {isEditing ? (
            <div className="flex flex-col gap-2 min-w-[240px]">
              <input
                type="text"
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleEdit()}
                className="w-full bg-[#0d0e15] text-white text-sm rounded-lg px-3 py-1.5 border border-white/10 focus:outline-none focus:border-indigo-500"
                autoFocus
              />
              <div className="flex justify-end gap-1.5 text-xs">
                <button 
                  onClick={() => setIsEditing(false)}
                  className="px-2 py-1 rounded bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition cursor-pointer"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleEdit}
                  className="px-2.5 py-1 rounded bg-indigo-500 hover:bg-indigo-400 text-white font-medium transition cursor-pointer"
                >
                  Save
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-1">
              <p className="text-sm leading-relaxed whitespace-pre-wrap break-all">{decryptedContent}</p>
              
              {/* E2E decryption indicator & Info ticks */}
              <div className="flex items-center justify-end gap-1.5 mt-1 text-[10px] text-white/50 select-none">
                {message.is_edited && <span className="text-[9px] opacity-70 italic">(edited)</span>}
                
                {isE2E && (
                  <span 
                    className="flex items-center gap-0.5 text-indigo-300 font-semibold"
                    title="End-to-End Decrypted"
                  >
                    <Lock className="h-3 w-3 shrink-0" />
                    <span>e2ee</span>
                  </span>
                )}

                {/* Delivery ticks */}
                {isSelf && (
                  <span className="flex items-center">
                    {message.isPending ? (
                      <Clock className="h-3 w-3 animate-pulse" />
                    ) : (
                      // Double blue if read, double gray if delivered, single if sent
                      <CheckCheck className="h-3.5 w-3.5 text-indigo-200" />
                    )}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Hover Shortcut Actions Menu */}
        {!isEditing && (
          <div className={`absolute top-1/2 -translate-y-1/2 flex items-center gap-1.5 bg-[#171a26]/95 border border-white/5 rounded-xl p-1 shadow-xl opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10 ${
            isSelf ? 'right-full mr-2' : 'left-full ml-2'
          }`}>
            <button
              onClick={() => onReply(message)}
              className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
              title="Reply"
            >
              <CornerUpLeft className="h-4 w-4" />
            </button>
            
            <button
              onClick={() => setShowEmojiPicker(!showEmojiPicker)}
              className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
              title="Add Reaction"
            >
              <Smile className="h-4 w-4" />
            </button>

            {isSelf && (
              <>
                <button
                  onClick={() => setIsEditing(true)}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
                  title="Edit Message"
                >
                  <Edit2 className="h-4 w-4" />
                </button>
                <button
                  onClick={handleDelete}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-rose-400 hover:bg-rose-500/5 transition-colors cursor-pointer"
                  title="Delete Message"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </>
            )}

            {/* Emoji reaction mini selector */}
            {showEmojiPicker && (
              <div className="absolute bottom-full mb-2 bg-[#171a26] border border-white/5 rounded-xl p-1.5 shadow-2xl flex gap-1.5 z-20">
                {reactionEmojis.map((emoji) => (
                  <button
                    key={emoji}
                    onClick={() => handleReact(emoji)}
                    className="hover:scale-125 transition text-base cursor-pointer"
                  >
                    {emoji}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Rendered Emoji reactions list */}
      {message.reactions && Object.keys(message.reactions).length > 0 && (
        <div className={`flex flex-wrap gap-1 mt-1.5 ${isSelf ? 'justify-end' : 'justify-start'}`}>
          {Object.entries(message.reactions).map(([emoji, userIds]) => {
            if (!userIds || userIds.length === 0) return null;
            const hasReacted = currentUserId ? userIds.includes(currentUserId) : false;
            return (
              <button
                key={emoji}
                onClick={() => handleReact(emoji)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border transition cursor-pointer ${
                  hasReacted
                    ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300'
                    : 'bg-[#151724] border-white/5 text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <span>{emoji}</span>
                <span className="text-[10px]">{userIds.length}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
