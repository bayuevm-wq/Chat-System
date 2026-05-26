package com.chat.system.data.remote

import com.chat.system.data.remote.dto.*
import retrofit2.http.*

interface ChatApi {

    // ── Authentication ──
    @POST("auth/register")
    suspend fun register(@Body request: RegisterRequest): AuthResponse

    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): AuthResponse

    @POST("auth/ws-token")
    suspend fun getWsToken(@Header("Authorization") token: String): WsTokenResponse

    // ── Rooms ──
    @GET("rooms/")
    suspend fun getRooms(@Header("Authorization") token: String): List<RoomResponse>

    @POST("rooms/")
    suspend fun createRoom(
        @Header("Authorization") token: String,
        @Body request: CreateRoomRequest
    ): RoomResponse

    @POST("rooms/{id}/join")
    suspend fun joinRoom(
        @Header("Authorization") token: String,
        @Path("id") roomId: String
    )

    @POST("rooms/{id}/leave")
    suspend fun leaveRoom(
        @Header("Authorization") token: String,
        @Path("id") roomId: String
    )

    @GET("rooms/{id}/members")
    suspend fun getRoomMembers(
        @Header("Authorization") token: String,
        @Path("id") roomId: String
    ): List<MemberResponse>

    // ── Messages ──
    @GET("messages/{roomId}")
    suspend fun getMessages(
        @Header("Authorization") token: String,
        @Path("roomId") roomId: String,
        @Query("limit") limit: Int = 50,
        @Query("before") before: String? = null
    ): List<MessageResponse>

    @GET("messages/{roomId}/search")
    suspend fun searchMessages(
        @Header("Authorization") token: String,
        @Path("roomId") roomId: String,
        @Query("q") query: String,
        @Query("limit") limit: Int = 50
    ): List<MessageResponse>

    @PATCH("messages/{id}")
    suspend fun editMessage(
        @Header("Authorization") token: String,
        @Path("id") messageId: Int,
        @Body body: Map<String, String> // content -> value
    ): MessageResponse

    @DELETE("messages/{id}")
    suspend fun deleteMessage(
        @Header("Authorization") token: String,
        @Path("id") messageId: Int
    )
}
