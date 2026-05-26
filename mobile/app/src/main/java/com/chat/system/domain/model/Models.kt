package com.chat.system.domain.model

data class User(
    val id: String,
    val username: String,
    val email: String,
    val displayName: String,
    val avatarUrl: String? = null,
    val status: String = "offline"
)

data class Room(
    val id: String,
    val name: String?,
    val type: String, // "public", "private", "direct"
    val description: String?,
    val maxMembers: Int,
    val createdBy: String?
)

data class Message(
    val messageId: Int,
    val roomId: String,
    val senderId: String,
    val content: String,
    val type: String, // "text" | "encrypted"
    val replyTo: Int?,
    val isEdited: Boolean,
    val timestamp: String,
    val isPending: Boolean = false,
    val isFailed: Boolean = false
)
