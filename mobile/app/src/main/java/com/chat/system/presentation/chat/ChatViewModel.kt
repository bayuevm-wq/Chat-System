package com.chat.system.presentation.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.chat.system.data.remote.ConnectionStatus
import com.chat.system.domain.model.Message
import com.chat.system.domain.model.Room
import com.chat.system.domain.model.User
import com.chat.system.domain.repository.ChatRepository
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

class ChatViewModel(private val repository: ChatRepository) : ViewModel() {

    val connectionStatus: StateFlow<ConnectionStatus> = repository.connectionStatus

    val rooms: StateFlow<List<Room>> = repository.getRooms()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    private val _activeRoomId = MutableStateFlow<String?>(null)
    val activeRoomId: StateFlow<String?> = _activeRoomId

    @OptIn(ExperimentalCoroutinesApi::class)
    val messages: StateFlow<List<Message>> = _activeRoomId
        .flatMapLatest { roomId ->
            if (roomId != null) repository.getMessages(roomId) else flowOf(emptyList())
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    private val _roomMembers = MutableStateFlow<List<User>>(emptyList())
    val roomMembers: StateFlow<List<User>> = _roomMembers

    private val _typingUsers = MutableStateFlow<Map<String, List<String>>>(emptyMap())
    val typingUsers: StateFlow<Map<String, List<String>>> = _typingUsers

    private val _searchResults = MutableStateFlow<List<Message>>(emptyList())
    val searchResults: StateFlow<List<Message>> = _searchResults

    // Cache to map userId to displayNames for typing notifications
    private val memberNamesCache = mutableMapOf<String, String>()

    // E2E UI Toggle state
    private val _isE2EActive = MutableStateFlow(false)
    val isE2EActive: StateFlow<Boolean> = _isE2EActive

    init {
        // Connect WS on init
        viewModelScope.launch {
            repository.connectWebSocket()
            repository.syncRooms()
        }

        // React to room switching
        viewModelScope.launch {
            _activeRoomId.collect { roomId ->
                if (roomId != null) {
                    repository.syncMessages(roomId)
                    fetchMembers(roomId)
                    _searchResults.value = emptyList()
                }
            }
        }

        // React to typing socket events
        viewModelScope.launch {
            repository.wsEventFlow.collect { event ->
                val type = event["type"] as? String ?: return@collect
                if (type == "typing.indicator") {
                    val roomId = event["room_id"] as? String ?: return@collect
                    val userId = event["user_id"] as? String ?: return@collect
                    val isTyping = event["is_typing"] as? Boolean ?: false

                    val name = memberNamesCache[userId] ?: "Someone"
                    val currentTyping = _typingUsers.value[roomId] ?: emptyList()
                    val updatedTyping = if (isTyping) {
                        if (currentTyping.contains(name)) currentTyping else currentTyping + name
                    } else {
                        currentTyping - name
                    }
                    _typingUsers.value = _typingUsers.value + (roomId to updatedTyping)
                }
            }
        }
    }

    fun setActiveRoom(roomId: String?) {
        _activeRoomId.value = roomId
    }

    fun toggleE2E() {
        _isE2EActive.value = !_isE2EActive.value
    }

    fun sendMessage(content: String, replyTo: Int? = null) {
        val roomId = _activeRoomId.value ?: return
        viewModelScope.launch {
            repository.sendMessage(roomId, content, _isE2EActive.value, replyTo)
            repository.syncMessages(roomId) // Update local flow
        }
    }

    fun editMessage(messageId: Int, content: String) {
        val roomId = _activeRoomId.value ?: return
        viewModelScope.launch {
            repository.editMessage(roomId, messageId, content)
        }
    }

    fun deleteMessage(messageId: Int) {
        val roomId = _activeRoomId.value ?: return
        viewModelScope.launch {
            repository.deleteMessage(roomId, messageId)
        }
    }

    fun createRoom(name: String, type: String, description: String?, onComplete: () -> Unit) {
        viewModelScope.launch {
            repository.createRoom(name, type, description)
                .onSuccess { newRoom ->
                    _activeRoomId.value = newRoom.id
                    onComplete()
                }
        }
    }

    fun searchMessages(query: String) {
        val roomId = _activeRoomId.value ?: return
        viewModelScope.launch {
            repository.searchMessages(roomId, query)
                .onSuccess {
                    _searchResults.value = it
                }
        }
    }

    fun sendTypingIndicator(isTyping: Boolean) {
        val roomId = _activeRoomId.value ?: return
        repository.sendTypingIndicator(roomId, isTyping)
    }

    fun setPresence(status: String) {
        repository.sendPresenceUpdate(status)
    }

    fun syncHistory() {
        val roomId = _activeRoomId.value ?: return
        viewModelScope.launch {
            val oldestTimestamp = messages.value.firstOrNull()?.timestamp
            repository.syncMessages(roomId, oldestTimestamp)
        }
    }

    private fun fetchMembers(roomId: String) {
        viewModelScope.launch {
            repository.getRoomMembers(roomId).onSuccess { membersList ->
                _roomMembers.value = membersList
                membersList.forEach {
                    memberNamesCache[it.id] = it.displayName
                }
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        repository.disconnectWebSocket()
    }
}
