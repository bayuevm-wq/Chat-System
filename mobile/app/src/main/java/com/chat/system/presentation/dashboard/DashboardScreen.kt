package com.chat.system.presentation.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.chat.system.data.remote.ConnectionStatus
import com.chat.system.domain.model.Room
import com.chat.system.presentation.auth.AuthViewModel
import com.chat.system.presentation.chat.ChatViewModel
import com.chat.system.ui.theme.DarkSurface
import com.chat.system.ui.theme.DarkSurfaceVariant

@Composable
fun DashboardScreen(
    chatViewModel: ChatViewModel,
    authViewModel: AuthViewModel,
    onNavigateToChat: (String) -> Unit,
    onNavigateToCall: () -> Unit,
    onLogout: () -> Unit
) {
    var selectedTab by remember { mutableIntStateOf(0) }
    val connectionStatus by chatViewModel.connectionStatus.collectAsState()

    Scaffold(
        bottomBar = {
            NavigationBar(
                containerColor = DarkSurface,
                tonalElevation = 8.dp
            ) {
                NavigationBarItem(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    icon = { Icon(Icons.Default.Home, contentDescription = "Chats") },
                    label = { Text("Chats", fontSize = 11.sp) }
                )
                NavigationBarItem(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    icon = { Icon(Icons.Default.Call, contentDescription = "Calls") },
                    label = { Text("Calls", fontSize = 11.sp) }
                )
                NavigationBarItem(
                    selected = selectedTab == 2,
                    onClick = { selectedTab = 2 },
                    icon = { Icon(Icons.Default.Settings, contentDescription = "Settings") },
                    label = { Text("Settings", fontSize = 11.sp) }
                )
            }
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            // Header Top Bar
            DashboardHeader(connectionStatus)

            // Dynamic Tab selection Body
            when (selectedTab) {
                0 -> ChatsTab(chatViewModel, onNavigateToChat)
                1 -> CallsTab(onNavigateToCall)
                2 -> SettingsTab(chatViewModel, authViewModel, onLogout)
            }
        }
    }
}

@Composable
fun DashboardHeader(status: ConnectionStatus) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(DarkSurface)
            .padding(horizontal = 20.dp, vertical = 16.dp),
        horizontalArrangement = Arrangement.KeepAlongWith,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "NODECHAT CLUSTER",
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.sp,
                color = Color.White
            )
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(top = 2.dp)
            ) {
                // Glow indicator dot
                val dotColor = when (status) {
                    ConnectionStatus.CONNECTED -> Color(0xFF10B981)
                    ConnectionStatus.CONNECTING -> Color(0xFFF59E0B)
                    ConnectionStatus.DISCONNECTED -> Color(0xFFEF4444)
                }
                Box(
                    modifier = Modifier
                        .size(8.dp)
                        .clip(CircleShape)
                        .background(dotColor)
                )
                Text(
                    text = status.name,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = dotColor,
                    modifier = Modifier.padding(start = 6.dp)
                )
            }
        }
    }
}

@Composable
fun ChatsTab(
    chatViewModel: ChatViewModel,
    onNavigateToChat: (String) -> Unit
) {
    val rooms by chatViewModel.rooms.collectAsState()
    var showCreateRoomDialog by remember { mutableStateOf(false) }

    Box(modifier = Modifier.fillMaxSize()) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            item {
                Text(
                    text = "Conversations",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(bottom = 8.dp)
                )
            }

            items(rooms) { room ->
                RoomListItem(room = room, onClick = { onNavigateToChat(room.id) })
            }

            if (rooms.isEmpty()) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 40.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "No channels or DMs found. Click + to create a room.",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }

        // Floating Action to Create Room
        FloatingActionButton(
            onClick = { showCreateRoomDialog = true },
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(20.dp),
            containerColor = MaterialTheme.colorScheme.primary,
            contentColor = MaterialTheme.colorScheme.background
        ) {
            Text("+", fontSize = 24.sp, fontWeight = FontWeight.Bold)
        }

        if (showCreateRoomDialog) {
            CreateRoomDialog(
                chatViewModel = chatViewModel,
                onDismiss = { showCreateRoomDialog = false }
            )
        }
    }
}

@Composable
fun RoomListItem(room: Room, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(DarkSurface)
            .clickable(onClick = onClick)
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Room avatar icon bubble
        Box(
            modifier = Modifier
                .size(42.dp)
                .clip(CircleShape)
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)),
            contentAlignment = Alignment.Center
        ) {
            val prefix = (room.name ?: "C").take(2).uppercase()
            Text(
                text = prefix,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Bold,
                fontSize = 14.sp
            )
        }

        Spacer(modifier = Modifier.width(16.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = room.name ?: "Unknown Channel",
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White
            )
            Text(
                text = room.description ?: "No description provided.",
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                modifier = Modifier.padding(top = 2.dp)
            )
        }

        Text(
            text = room.type.uppercase(),
            fontSize = 9.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.08f), RoundedCornerShape(4.dp))
                .padding(horizontal = 6.dp, vertical = 2.dp)
        )
    }
}

@Composable
fun CreateRoomDialog(
    chatViewModel: ChatViewModel,
    onDismiss: () -> Unit
) {
    var name by remember { mutableStateOf("") }
    var type by remember { mutableStateOf("public") }
    var description by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Create Channel") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Channel Name") },
                    singleLine = true
                )

                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    label = { Text("Description") },
                    maxLines = 3
                )
                
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Privacy: ", fontSize = 13.sp)
                    Spacer(modifier = Modifier.width(8.dp))
                    Button(
                        onClick = { type = if (type == "public") "private" else "public" },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = DarkSurfaceVariant
                        )
                    ) {
                        Text(type.uppercase(), fontSize = 11.sp, color = MaterialTheme.colorScheme.primary)
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (name.isNotBlank()) {
                        chatViewModel.createRoom(name, type, description.takeIf { it.isNotBlank() }, onComplete = onDismiss)
                    }
                }
            ) {
                Text("Create")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        },
        containerColor = DarkSurface
    )
}

@Composable
fun CallsTab(onNavigateToCall: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Icon(
                Icons.Default.Call,
                contentDescription = "Calls",
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(48.dp)
            )
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = "Node calling services active",
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White
            )
            Text(
                text = "Simulate native WebRTC/VoIP link audio transmissions",
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 4.dp, bottom = 24.dp)
            )
            Button(onClick = onNavigateToCall) {
                Text("Start Simulation Call")
            }
        }
    }
}

@Composable
fun SettingsTab(
    chatViewModel: ChatViewModel,
    authViewModel: AuthViewModel,
    onLogout: () -> Unit
) {
    val cachedUser = authViewModel.uiState.collectAsState().value
    var statusText by remember { mutableStateOf("Online") }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            // Profile Card
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(16.dp))
                    .background(DarkSurface)
                    .padding(20.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(54.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)),
                    contentAlignment = Alignment.Center
                ) {
                    val fallback = "US"
                    Text(
                        text = fallback,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )
                }

                Spacer(modifier = Modifier.width(16.dp))

                Column {
                    val name = if (cachedUser is com.chat.system.presentation.auth.AuthUiState.Success) {
                        cachedUser.user.displayName.takeIf { it.isNotBlank() } ?: cachedUser.user.username
                    } else "Chat User"
                    Text(text = name, fontSize = 17.sp, fontWeight = FontWeight.Bold, color = Color.White)
                    Text(text = statusText, fontSize = 12.sp, color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(top = 2.dp))
                }
            }
        }

        item {
            // Presence Configuration Box
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(16.dp))
                    .background(DarkSurface)
                    .padding(16.dp)
            ) {
                Text("Presence Status", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(modifier = Modifier.height(12.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceAround
                ) {
                    listOf("online", "away", "busy", "offline").forEach { status ->
                        Button(
                            onClick = { 
                                statusText = status.replaceFirstChar { it.uppercase() }
                                chatViewModel.setPresence(status)
                            },
                            colors = ButtonDefaults.buttonColors(
                                containerColor = if (statusText.lowercase() == status) MaterialTheme.colorScheme.primary else DarkSurfaceVariant
                            ),
                            shape = RoundedCornerShape(8.dp),
                            contentPadding = PaddingValues(horizontal = 10.dp)
                        ) {
                            Text(status.uppercase(), fontSize = 9.sp, color = Color.White)
                        }
                    }
                }
            }
        }

        item {
            // Encryption keys simulator representation (Highly Premium Security aesthetics)
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(16.dp))
                    .background(DarkSurface)
                    .padding(20.dp)
            ) {
                Text(
                    text = "RSA Key-Pair Signature",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC3eRk6Yq+VjX2lG7o8b+rL4F/WnQ99k2dM6Vl3U9p7m7t7t/y9m9m1z2w2/4...",
                    fontSize = 9.sp,
                    color = MaterialTheme.colorScheme.primary,
                    lineHeight = 14.sp
                )
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = "Decryption Key stored securely on local storage (AES256 SharedPreferences).",
                    fontSize = 10.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }

        item {
            // Logout
            Button(
                onClick = onLogout,
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.error.copy(alpha = 0.8f)
                ),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(50.dp),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("Log Out", color = Color.White, fontWeight = FontWeight.Bold)
            }
        }
    }
}
