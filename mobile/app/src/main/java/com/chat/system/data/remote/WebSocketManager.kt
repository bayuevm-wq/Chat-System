package com.chat.system.data.remote

import android.util.Log
import com.google.gson.Gson
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import okhttp3.*
import java.util.concurrent.TimeUnit

enum class ConnectionStatus { CONNECTED, CONNECTING, DISCONNECTED }

class WebSocketManager(
    private val client: OkHttpClient,
    private val gson: Gson
) {
    private var webSocket: WebSocket? = null
    private var heartbeatJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    
    private val _connectionStatus = MutableStateFlow(ConnectionStatus.DISCONNECTED)
    val connectionStatus: StateFlow<ConnectionStatus> = _connectionStatus

    private val _eventFlow = MutableSharedFlow<Map<String, Any>>(extraBufferCapacity = 100)
    val eventFlow: SharedFlow<Map<String, Any>> = _eventFlow

    private var reconnectAttempts = 0
    private val maxReconnectAttempts = 10
    private var isReconnecting = false
    private var cachedToken: String? = null
    private var cachedHost: String? = null

    fun connect(host: String, wsToken: String) {
        cachedHost = host
        cachedToken = wsToken
        
        if (_connectionStatus.value == ConnectionStatus.CONNECTED || _connectionStatus.value == ConnectionStatus.CONNECTING) {
            return
        }

        _connectionStatus.value = ConnectionStatus.CONNECTING
        val wsUrl = "ws://$host/ws?token=$wsToken"
        Log.d("WebSocketManager", "Connecting to WebSocket: $wsUrl")

        val request = Request.Builder().url(wsUrl).build()
        webSocket = client.newWebSocket(request, SocketListener())
    }

    fun disconnect() {
        Log.d("WebSocketManager", "Disconnecting WebSocket manually")
        stopHeartbeat()
        webSocket?.close(1000, "Graceful disconnect")
        webSocket = null
        _connectionStatus.value = ConnectionStatus.DISCONNECTED
        reconnectAttempts = 0
        isReconnecting = false
    }

    fun send(type: String, payload: Map<String, Any?>) {
        val messageMap = mutableMapOf<String, Any?>("type" to type)
        messageMap.putAll(payload)
        val json = gson.toJson(messageMap)
        
        if (_connectionStatus.value == ConnectionStatus.CONNECTED && webSocket != null) {
            webSocket?.send(json)
        } else {
            Log.w("WebSocketManager", "Cannot send socket message. Socket status: ${_connectionStatus.value}")
        }
    }

    private fun startHeartbeat() {
        stopHeartbeat()
        heartbeatJob = scope.launch {
            while (isActive) {
                delay(30000) // 30s heartbeat loop
                if (_connectionStatus.value == ConnectionStatus.CONNECTED) {
                    send("presence.heartbeat", emptyMap())
                    Log.d("WebSocketManager", "Heartbeat ping sent")
                }
            }
        }
    }

    private fun stopHeartbeat() {
        heartbeatJob?.cancel()
        heartbeatJob = null
    }

    private fun scheduleReconnect() {
        if (isReconnecting || reconnectAttempts >= maxReconnectAttempts) return
        isReconnecting = true
        reconnectAttempts++
        
        // Exponential backoff
        val delayMs = (Math.pow(2.0, reconnectAttempts.toDouble()) * 1000).toLong() + (Math.random() * 1000).toLong()
        Log.i("WebSocketManager", "Scheduling reconnect attempt $reconnectAttempts in ${delayMs}ms")
        
        scope.launch {
            delay(delayMs)
            isReconnecting = false
            val host = cachedHost
            val token = cachedToken
            if (host != null && token != null && _connectionStatus.value == ConnectionStatus.DISCONNECTED) {
                connect(host, token)
            }
        }
    }

    private inner class SocketListener : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            Log.i("WebSocketManager", "WebSocket connection opened successfully.")
            _connectionStatus.value = ConnectionStatus.CONNECTED
            reconnectAttempts = 0
            isReconnecting = false
            startHeartbeat()
        }

        override fun onMessage(webSocket: WebSocket, text: String) {
            Log.d("WebSocketManager", "Received text event: $text")
            try {
                @Suppress("UNCHECKED_CAST")
                val eventMap = gson.fromJson(text, Map::class.java) as Map<String, Any>
                scope.launch {
                    _eventFlow.emit(eventMap)
                }
            } catch (e: Exception) {
                Log.e("WebSocketManager", "Error parsing WebSocket message: $text", e)
            }
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            Log.i("WebSocketManager", "WebSocket connection closed: $code / $reason")
            _connectionStatus.value = ConnectionStatus.DISCONNECTED
            stopHeartbeat()
            if (code != 1000) {
                scheduleReconnect()
            }
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
            Log.e("WebSocketManager", "WebSocket failure encountered", t)
            _connectionStatus.value = ConnectionStatus.DISCONNECTED
            stopHeartbeat()
            scheduleReconnect()
        }
    }
}
