package com.chat.system.domain.repository

import com.chat.system.data.remote.ConnectionStatus
import com.chat.system.domain.model.Message
import com.chat.system.domain.model.Room
import com.chat.system.domain.model.User
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.StateFlow

interface ChatRepository {

    // ── Authentication ──
    suspend fun register(username: String, email: String, password: String, displayName: String?): Result<User>
    suspend fun login(email: String, password: String): Result<User>
    fun getCachedUser(): User?
    fun logout()

    // ── Rooms ──
    fun getRooms(): Flow<List<Room>>
    suspend fun syncRooms(): Result<Unit>
    suspend fun createRoom(name: String, type: String, description: String?): Result<Room>
    suspend fun getRoomMembers(roomId: String): Result<List<User>>

    // ── Messages ──
    fun getMessages(roomId: String): Flow<List<Message>>
    suspend fun syncMessages(roomId: String, before: String? = null): Result<Unit>
    suspend fun sendMessage(roomId: String, content: String, isEncrypted: Boolean, replyTo: Int? = null): Result<Unit>
    suspend fun editMessage(roomId: String, messageId: Int, content: String): Result<Unit>
    suspend fun deleteMessage(roomId: String, messageId: Int): Result<Unit>
    suspend fun searchMessages(roomId: String, query: String): Result<List<Message>>

    // ── WebSockets & Sync ──
    val connectionStatus: StateFlow<ConnectionStatus>
    val wsEventFlow: kotlinx.coroutines.flow.SharedFlow<Map<String, Any>>
    suspend fun connectWebSocket(): Result<Unit>
    fun disconnectWebSocket()
    fun sendTypingIndicator(roomId: String, isTyping: Boolean)
    fun sendPresenceUpdate(status: String)

    // ── Config ──
    fun setApiHost(host: String)
    fun getApiHost(): String
}
