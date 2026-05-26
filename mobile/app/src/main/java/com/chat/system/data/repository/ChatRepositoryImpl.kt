package com.chat.system.data.repository

import android.util.Log
import com.chat.system.data.local.SessionManager
import com.chat.system.data.local.dao.ChatDao
import com.chat.system.data.local.entity.MessageEntity
import com.chat.system.data.local.entity.PendingMessageEntity
import com.chat.system.data.local.entity.RoomEntity
import com.chat.system.data.remote.ChatApi
import com.chat.system.data.remote.ConnectionStatus
import com.chat.system.data.remote.WebSocketManager
import com.chat.system.data.remote.dto.CreateRoomRequest
import com.chat.system.data.remote.dto.LoginRequest
import com.chat.system.data.remote.dto.RegisterRequest
import com.chat.system.domain.model.Message
import com.chat.system.domain.model.Room
import com.chat.system.domain.model.User
import com.chat.system.domain.repository.ChatRepository
import com.google.gson.Gson
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class ChatRepositoryImpl(
    private val chatDao: ChatDao,
    private val sessionManager: SessionManager,
    private val gson: Gson
) : ChatRepository {

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var api: ChatApi
    private var webSocketManager: WebSocketManager

    override val connectionStatus: StateFlow<ConnectionStatus>
        get() = webSocketManager.connectionStatus

    override val wsEventFlow: SharedFlow<Map<String, Any>>
        get() = webSocketManager.eventFlow

    init {
        // Construct API and WS instances
        val host = sessionManager.getApiEndpoint()
        val client = OkHttpClient.Builder()
            .readTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
            .writeTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
            .build()

        val retrofit = Retrofit.Builder()
            .baseUrl("http://$host/api/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()

        api = retrofit.create(ChatApi::class.java)
        webSocketManager = WebSocketManager(client, gson)

        // 1. Observe WS events and synchronize to Room cache
        scope.launch {
            webSocketManager.eventFlow.collect { event ->
                handleIncomingWsEvent(event)
            }
        }

        // 2. Flush offline queue when connection establishes
        scope.launch {
            webSocketManager.connectionStatus.collect { status ->
                if (status == ConnectionStatus.CONNECTED) {
                    flushOfflineQueue()
                }
            }
        }
    }

    override fun setApiHost(host: String) {
        sessionManager.saveApiEndpoint(host)
        
        // Rebuild Retrofit & WS instances
        val client = OkHttpClient.Builder().build()
        val retrofit = Retrofit.Builder()
            .baseUrl("http://$host/api/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()
        api = retrofit.create(ChatApi::class.java)
        
        webSocketManager.disconnect()
        webSocketManager = WebSocketManager(client, gson)
        
        // Re-subscribe events
        scope.launch {
            webSocketManager.eventFlow.collect { event ->
                handleIncomingWsEvent(event)
            }
        }
    }

    override fun getApiHost(): String = sessionManager.getApiEndpoint()

    // ── Authentication ──

    override suspend fun register(username: String, email: String, password: String, displayName: String?): Result<User> {
        return try {
            val response = api.register(RegisterRequest(username, email, password, displayName))
            val domainUser = User(
                id = response.user.id,
                username = response.user.username,
                email = response.user.email,
                displayName = response.user.displayName,
                avatarUrl = response.user.avatarUrl
            )
            sessionManager.saveAuthSession(domainUser, response.accessToken, response.refreshToken)
            Result.success(domainUser)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun login(email: String, password: String): Result<User> {
        return try {
            val response = api.login(LoginRequest(email, password))
            val domainUser = User(
                id = response.user.id,
                username = response.user.username,
                email = response.user.email,
                displayName = response.user.displayName,
                avatarUrl = response.user.avatarUrl
            )
            sessionManager.saveAuthSession(domainUser, response.accessToken, response.refreshToken)
            Result.success(domainUser)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override fun getCachedUser(): User? = sessionManager.getCachedUser()

    override fun logout() {
        disconnectWebSocket()
        sessionManager.clearSession()
        scope.launch {
            chatDao.clearRooms()
            chatDao.clearMessages()
        }
    }

    // ── Rooms ──

    override fun getRooms(): Flow<List<Room>> {
        return chatDao.getRoomsFlow().map { entities ->
            entities.map { it.toDomain() }
        }
    }

    override suspend fun syncRooms(): Result<Unit> {
        val token = sessionManager.getAccessToken() ?: return Result.failure(Exception("Not authenticated"))
        return try {
            val roomsResponse = api.getRooms("Bearer $token")
            val entities = roomsResponse.map {
                RoomEntity(
                    id = it.id,
                    name = it.name,
                    type = it.type,
                    description = it.description,
                    maxMembers = it.maxMembers,
                    createdBy = it.createdBy
                )
            }
            chatDao.insertRooms(entities)
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun createRoom(name: String, type: String, description: String?): Result<Room> {
        val token = sessionManager.getAccessToken() ?: return Result.failure(Exception("Not authenticated"))
        return try {
            val response = api.createRoom("Bearer $token", CreateRoomRequest(name, type, description))
            val entity = RoomEntity(
                id = response.id,
                name = response.name,
                type = response.type,
                description = response.description,
                maxMembers = response.maxMembers,
                createdBy = response.createdBy
            )
            chatDao.insertRoom(entity)
            Result.success(entity.toDomain())
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun getRoomMembers(roomId: String): Result<List<User>> {
        val token = sessionManager.getAccessToken() ?: return Result.failure(Exception("Not authenticated"))
        return try {
            val members = api.getRoomMembers("Bearer $token", roomId)
            val users = members.map {
                User(
                    id = it.userId,
                    username = it.username ?: "User",
                    displayName = it.displayName ?: it.username ?: "User",
                    email = ""
                )
            }
            Result.success(users)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    // ── Messages ──

    override fun getMessages(roomId: String): Flow<List<Message>> {
        return chatDao.getMessagesFlow(roomId).map { entities ->
            entities.map { it.toDomain() }
        }
    }

    override suspend fun syncMessages(roomId: String, before: String?): Result<Unit> {
        val token = sessionManager.getAccessToken() ?: return Result.failure(Exception("Not authenticated"))
        return try {
            val messagesResponse = api.getMessages("Bearer $token", roomId, 50, before)
            val entities = messagesResponse.map {
                MessageEntity(
                    messageId = it.messageId,
                    roomId = it.roomId,
                    senderId = it.senderId,
                    content = it.content,
                    type = it.messageType,
                    replyTo = it.replyTo,
                    isEdited = it.isEdited,
                    timestamp = it.createdAt
                )
            }
            chatDao.insertMessages(entities)
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun sendMessage(roomId: String, content: String, isEncrypted: Boolean, replyTo: Int?): Result<Unit> {
        val user = sessionManager.getCachedUser() ?: return Result.failure(Exception("Session expired"))
        
        // 1. Client-Side Cryptographic E2EE Simulation
        val messageType = if (isEncrypted) "encrypted" else "text"
        val payloadContent = if (isEncrypted) {
            // Cipher representation: Base64 encoding prefixed with secure E2E string
            "E2E::" + android.util.Base64.encodeToString(content.toByteArray(), android.util.Base64.NO_WRAP)
        } else {
            content
        }

        // 2. Perform Send logic depending on Network Connectivity
        if (webSocketManager.connectionStatus.value == ConnectionStatus.CONNECTED) {
            // Network is active, transmit immediately
            webSocketManager.send("message.send", mapOf(
                "room_id" to roomId,
                "content" to payloadContent,
                "message_type" to messageType,
                "reply_to" to replyTo
            ))
            
            // Insert optimistic pending message into DB
            val tempId = -((100000..999999).random())
            chatDao.insertMessage(
                MessageEntity(
                    messageId = tempId,
                    roomId = roomId,
                    senderId = user.id,
                    content = payloadContent,
                    type = messageType,
                    replyTo = replyTo,
                    isEdited = false,
                    timestamp = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", java.util.Locale.US).apply {
                        timeZone = java.util.TimeZone.getTimeZone("UTC")
                    }.format(java.util.Date()),
                    isPending = true
                )
            )
        } else {
            // Network is offline, place into SQLite queue
            val pending = PendingMessageEntity(
                roomId = roomId,
                content = payloadContent,
                type = messageType,
                replyTo = replyTo
            )
            chatDao.insertPendingMessage(pending)

            // Show optimistically in UI as pending
            val tempId = -((100000..999999).random())
            chatDao.insertMessage(
                MessageEntity(
                    messageId = tempId,
                    roomId = roomId,
                    senderId = user.id,
                    content = payloadContent,
                    type = messageType,
                    replyTo = replyTo,
                    isEdited = false,
                    timestamp = pending.timestamp,
                    isPending = true
                )
            )
            Log.d("ChatRepository", "Offline message buffered locally in SQLite queue.")
        }
        return Result.success(Unit)
    }

    override suspend fun editMessage(roomId: String, messageId: Int, content: String): Result<Unit> {
        val token = sessionManager.getAccessToken() ?: return Result.failure(Exception("Not authenticated"))
        return try {
            api.editMessage("Bearer $token", messageId, mapOf("content" to content))
            
            // Update local DB
            val messages = chatDao.getMessagesDirect(roomId)
            val local = messages.find { it.messageId == messageId }
            if (local != null) {
                chatDao.insertMessage(local.copy(content = content, isEdited = true))
            }
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun deleteMessage(roomId: String, messageId: Int): Result<Unit> {
        val token = sessionManager.getAccessToken() ?: return Result.failure(Exception("Not authenticated"))
        return try {
            api.deleteMessage("Bearer $token", messageId)
            chatDao.deleteMessageById(messageId)
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun searchMessages(roomId: String, query: String): Result<List<Message>> {
        val token = sessionManager.getAccessToken() ?: return Result.failure(Exception("Not authenticated"))
        return try {
            val response = api.searchMessages("Bearer $token", roomId, query)
            val domainMessages = response.map {
                Message(
                    messageId = it.messageId,
                    roomId = it.roomId,
                    senderId = it.senderId,
                    content = it.content,
                    type = it.messageType,
                    replyTo = it.replyTo,
                    isEdited = it.isEdited,
                    timestamp = it.createdAt
                )
            }
            Result.success(domainMessages)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    // ── WebSocket Manager hooks ──

    override suspend fun connectWebSocket(): Result<Unit> {
        val token = sessionManager.getAccessToken() ?: return Result.failure(Exception("Not authenticated"))
        return try {
            val wsTokenResponse = api.getWsToken("Bearer $token")
            val host = sessionManager.getApiEndpoint()
            webSocketManager.connect(host, wsTokenResponse.wsToken)
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override fun disconnectWebSocket() {
        webSocketManager.disconnect()
    }

    override fun sendTypingIndicator(roomId: String, isTyping: Boolean) {
        webSocketManager.send("typing.indicator", mapOf("room_id" to roomId, "is_typing" to isTyping))
    }

    override fun sendPresenceUpdate(status: String) {
        webSocketManager.send("presence.update", mapOf("status" to status))
    }

    // ── Helper flusher and events router ──

    private suspend fun flushOfflineQueue() {
        val pending = chatDao.getAllPendingMessages()
        if (pending.isEmpty()) return

        Log.i("ChatRepository", "Connection recovered! Flushing ${pending.size} offline enqueued messages.")
        for (msg in pending) {
            try {
                webSocketManager.send("message.send", mapOf(
                    "room_id" to msg.roomId,
                    "content" to msg.content,
                    "message_type" to msg.type,
                    "reply_to" to msg.replyTo
                ))
                chatDao.deletePendingMessage(msg.localId)
            } catch (e: Exception) {
                Log.e("ChatRepository", "Error sending queued offline message: ${msg.localId}", e)
            }
        }
    }

    private suspend fun handleIncomingWsEvent(event: Map<String, Any>) {
        val type = event["type"] as? String ?: return
        when (type) {
            "message.new" -> {
                val msgId = (event["message_id"] as? Number)?.toInt() ?: return
                val roomId = event["room_id"] as? String ?: return
                val senderId = event["sender_id"] as? String ?: return
                val content = event["content"] as? String ?: return
                val msgType = event["message_type"] as? String ?: "text"
                val replyTo = (event["reply_to"] as? Number)?.toInt()
                val isEdited = event["is_edited"] as? Boolean ?: false
                val createdAt = event["created_at"] as? String ?: ""

                // 1. Optimistic removal: if this new message is from us, delete the temporary negative pending message
                if (senderId == sessionManager.getCachedUser()?.id) {
                    val locals = chatDao.getMessagesDirect(roomId)
                    val temp = locals.find { it.isPending && it.content == content }
                    if (temp != null) {
                        chatDao.deleteMessageById(temp.messageId)
                    }
                }

                // 2. Insert validated database entry
                chatDao.insertMessage(
                    MessageEntity(
                        messageId = msgId,
                        roomId = roomId,
                        senderId = senderId,
                        content = content,
                        type = msgType,
                        replyTo = replyTo,
                        isEdited = isEdited,
                        timestamp = createdAt
                    )
                )
            }
            "message.ack" -> {
                val msgId = (event["message_id"] as? Number)?.toInt() ?: return
                val roomId = event["room_id"] as? String ?: return
                
                // Remove pending flag for first found pending message in Room
                val locals = chatDao.getMessagesDirect(roomId)
                val pending = locals.find { it.isPending }
                if (pending != null) {
                    chatDao.deleteMessageById(pending.messageId)
                    chatDao.insertMessage(pending.copy(messageId = msgId, isPending = false))
                }
            }
        }
    }

    // ── Extension mappings ──

    private fun RoomEntity.toDomain() = Room(
        id = id,
        name = name,
        type = type,
        description = description,
        maxMembers = maxMembers,
        createdBy = createdBy
    )

    private fun MessageEntity.toDomain() = Message(
        messageId = messageId,
        roomId = roomId,
        senderId = senderId,
        content = content,
        type = type,
        replyTo = replyTo,
        isEdited = isEdited,
        timestamp = timestamp,
        isPending = isPending,
        isFailed = isFailed
    )
}
