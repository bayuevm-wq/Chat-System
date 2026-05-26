package com.chat.system.data.remote.dto

import com.google.gson.annotations.SerializedName

data class RegisterRequest(
    val username: String,
    val email: String,
    val password: String,
    @SerializedName("display_name") val displayName: String? = null
)

data class LoginRequest(
    val email: String,
    val password: String
)

data class UserDto(
    val id: String,
    val username: String,
    val email: String,
    @SerializedName("display_name") val displayName: String,
    @SerializedName("avatar_url") val avatarUrl: String? = null
)

data class AuthResponse(
    val user: UserDto,
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("refresh_token") val refreshToken: String
)

data class WsTokenResponse(
    @SerializedName("ws_token") val wsToken: String
)

data class CreateRoomRequest(
    val name: String,
    val type: String, // "public" | "private" | "direct"
    val description: String? = null
)

data class RoomResponse(
    val id: String,
    val name: String?,
    val type: String,
    val description: String?,
    @SerializedName("max_members") val maxMembers: Int,
    @SerializedName("created_by") val createdBy: String?
)

data class MessageResponse(
    @SerializedName("message_id") val messageId: Int,
    @SerializedName("room_id") val roomId: String,
    @SerializedName("sender_id") val senderId: String,
    val content: String,
    @SerializedName("message_type") val messageType: String,
    @SerializedName("reply_to") val replyTo: Int?,
    @SerializedName("is_edited") val isEdited: Boolean,
    @SerializedName("created_at") val createdAt: String
)

data class MemberResponse(
    @SerializedName("user_id") val userId: String,
    val role: String,
    val username: String?,
    @SerializedName("display_name") val displayName: String?
)
