package com.chat.system.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "rooms")
data class RoomEntity(
    @PrimaryKey val id: String,
    val name: String?,
    val type: String, // "public", "private", "direct"
    val description: String?,
    val maxMembers: Int,
    val createdBy: String?
)

@Entity(tableName = "messages")
data class MessageEntity(
    @PrimaryKey val messageId: Int, // Remote message ID from server (negative for optimistic pending inserts)
    val roomId: String,
    val senderId: String,
    val content: String,
    val type: String, // "text", "encrypted", etc.
    val replyTo: Int?,
    val isEdited: Boolean,
    val timestamp: String,
    val isPending: Boolean = false,
    val isFailed: Boolean = false
)

@Entity(tableName = "pending_messages")
data class PendingMessageEntity(
    @PrimaryKey(autoGenerate = true) val localId: Int = 0,
    val roomId: String,
    val content: String,
    val type: String, // "text", "encrypted"
    val replyTo: Int?,
    val timestamp: String = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", java.util.Locale.US).apply {
        timeZone = java.util.TimeZone.getTimeZone("UTC")
    }.format(java.util.Date())
)
