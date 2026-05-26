package com.chat.system.presentation.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.chat.system.data.remote.ConnectionStatus
import com.chat.system.domain.model.Message
import com.chat.system.ui.theme.DarkSurface
import com.chat.system.ui.theme.DarkSurfaceVariant
import kotlinx.coroutines.delay

@Composable
fun ChatRoomScreen(
    viewModel: ChatViewModel,
    onNavigateBack: () -> Unit,
    onNavigateToCall: () -> Unit
) {
    val messages by viewModel.messages.collectAsState()
    val roomMembers by viewModel.roomMembers.collectAsState()
    val typingUsersMap by viewModel.typingUsers.collectAsState()
    val activeRoomId by viewModel.activeRoomId.collectAsState()
    val isE2EActive by viewModel.isE2EActive.collectAsState()
    val connectionStatus by viewModel.connectionStatus.collectAsState()

    var text by remember { mutableStateOf("") }
    var isTyping by remember { mutableStateOf(false) }

    // Search overlay triggers
    var isSearchActive by remember { mutableStateOf(false) }
    var searchQuery by remember { mutableStateOf("") }
    val searchResults by viewModel.searchResults.collectAsState()

    // Scroll state
    val listState = rememberLazyListState()

    // Auto-scroll to bottom on new messages
    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    // Debounce typing status
    LaunchedEffect(text) {
        if (text.isNotBlank() && !isTyping) {
            isTyping = true
            viewModel.sendTypingIndicator(true)
        }
        
        if (text.isBlank() && isTyping) {
            isTyping = false
            viewModel.sendTypingIndicator(false)
        }

        delay(2000)
        if (isTyping) {
            isTyping = false
            viewModel.sendTypingIndicator(false)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            text = "Channel Room",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                        Text(
                            text = "${roomMembers.size} participants",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = Color.White)
                    }
                },
                actions = {
                    IconButton(onClick = { isSearchActive = !isSearchActive }) {
                        Icon(Icons.Default.Search, contentDescription = "Search", tint = Color.White)
                    }
                    IconButton(onClick = onNavigateToCall) {
                        Icon(Icons.Default.Call, contentDescription = "Call", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = DarkSurface
                )
            )
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            Column(modifier = Modifier.fillMaxSize()) {
                
                // Network Alert banner
                if (connectionStatus != ConnectionStatus.CONNECTED) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(MaterialTheme.colorScheme.error.copy(alpha = 0.1f))
                            .padding(vertical = 6.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "Offline Mode — Messages enqueued for sync",
                            color = MaterialTheme.colorScheme.error,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }

                // Search Results Panel Overlay
                if (isSearchActive) {
                    SearchOverlay(
                        query = searchQuery,
                        onQueryChange = { 
                            searchQuery = it
                            viewModel.searchMessages(it)
                        },
                        results = searchResults,
                        onClose = {
                            isSearchActive = false
                            searchQuery = ""
                        }
                    )
                }

                // Chat Messages stream
                LazyColumn(
                    state = listState,
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(messages) { message ->
                        val isSelf = message.senderId == viewModel.rooms.value.firstOrNull()?.createdBy // Mock self representation
                        MessageBubbleItem(message = message, isSelf = isSelf)
                    }
                }

                // Typing Status banner
                val activeTypingList = typingUsersMap[activeRoomId] ?: emptyList()
                if (activeTypingList.isNotEmpty()) {
                    val typingText = when (activeTypingList.size) {
                        1 -> "${activeTypingList[0]} is typing..."
                        2 -> "${activeTypingList[0]} and ${activeTypingList[1]} are typing..."
                        else -> "Several people are typing..."
                    }
                    Text(
                        text = typingText,
                        fontSize = 11.sp,
                        fontStyle = FontStyle.Italic,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(start = 20.dp, bottom = 4.dp)
                    )
                }

                // Message Input Panel Layout
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(DarkSurface)
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Lock icon toggle for E2EE simulation
                    IconButton(
                        onClick = { viewModel.toggleE2E() },
                        modifier = Modifier
                            .background(
                                if (isE2EActive) MaterialTheme.colorScheme.primary.copy(alpha = 0.2f) else Color.Transparent,
                                RoundedCornerShape(10.dp)
                            )
                    ) {
                        Text(
                            text = if (isE2EActive) "🔒" else "🔓",
                            fontSize = 18.sp
                        )
                    }

                    Spacer(modifier = Modifier.width(8.dp))

                    OutlinedTextField(
                        value = text,
                        onValueChange = { text = it },
                        placeholder = { Text(if (isE2EActive) "Send encrypted message..." else "Send message...", fontSize = 13.sp) },
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(24.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedContainerColor = DarkSurfaceVariant,
                            unfocusedContainerColor = DarkSurfaceVariant,
                            focusedBorderColor = Color.Transparent,
                            unfocusedBorderColor = Color.Transparent
                        )
                    )

                    Spacer(modifier = Modifier.width(8.dp))

                    Button(
                        onClick = {
                            if (text.isNotBlank()) {
                                viewModel.sendMessage(text)
                                text = ""
                            }
                        },
                        shape = RoundedCornerShape(24.dp),
                        contentPadding = PaddingValues(horizontal = 16.dp)
                    ) {
                        Text("Send", fontSize = 13.sp)
                    }
                }
            }
        }
    }
}

@Composable
fun MessageBubbleItem(message: Message, isSelf: Boolean) {
    // Client-Side Dynamic E2EE Decrypter representation
    val isEncrypted = message.type == "encrypted"
    val decryptedContent = remember(message.content) {
        if (isEncrypted && message.content.startsWith("E2E::")) {
            try {
                val cipherBytes = android.util.Base64.decode(message.content.substring(5), android.util.Base64.NO_WRAP)
                String(cipherBytes)
            } catch (e: Exception) {
                message.content
            }
        } else {
            message.content
        }
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        horizontalAlignment = if (isSelf) Alignment.End else Alignment.Start
    ) {
        Box(
            modifier = Modifier
                .clip(
                    RoundedCornerShape(
                        topStart = 16.dp,
                        topEnd = 16.dp,
                        bottomStart = if (isSelf) 16.dp else 2.dp,
                        bottomEnd = if (isSelf) 2.dp else 16.dp
                    )
                )
                .background(
                    if (isSelf) MaterialTheme.colorScheme.primary else DarkSurface
                )
                .padding(horizontal = 14.dp, vertical = 10.dp)
        ) {
            Column {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    if (isEncrypted) {
                        Text("🔒", fontSize = 11.sp)
                    }
                    Text(
                        text = decryptedContent,
                        color = Color.White,
                        fontSize = 14.sp,
                        lineHeight = 18.sp
                    )
                }
                
                // Timestamp and delivery indicators
                Row(
                    modifier = Modifier
                        .align(Alignment.End)
                        .padding(top = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = message.timestamp.takeLast(9).take(5), // Simple time extract
                        color = Color.White.copy(alpha = 0.5f),
                        fontSize = 9.sp
                    )
                    if (isSelf) {
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text = if (message.isPending) "⏳" else "✓✓",
                            color = Color.White.copy(alpha = 0.5f),
                            fontSize = 8.sp
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun SearchOverlay(
    query: String,
    onQueryChange: (String) -> Unit,
    results: List<Message>,
    onClose: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = DarkSurface)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth()
            ) {
                OutlinedTextField(
                    value = query,
                    onValueChange = onQueryChange,
                    placeholder = { Text("Search logs...", fontSize = 12.sp) },
                    modifier = Modifier.weight(1f),
                    singleLine = true
                )
                TextButton(onClick = onClose) {
                    Text("Close")
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 200.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                items(results) { msg ->
                    val isEnc = msg.type == "encrypted"
                    val content = if (isEnc && msg.content.startsWith("E2E::")) {
                        try {
                            String(android.util.Base64.decode(msg.content.substring(5), android.util.Base64.NO_WRAP))
                        } catch (e: Exception) { msg.content }
                    } else msg.content

                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(DarkSurfaceVariant, RoundedCornerShape(8.dp))
                            .padding(8.dp)
                    ) {
                        Text(
                            text = "${if (isEnc) "🔒 " else ""}$content",
                            fontSize = 12.sp,
                            color = Color.White
                        )
                    }
                }
                
                if (results.isEmpty() && query.isNotBlank()) {
                    item {
                        Text("No matching records.", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
    }
}
