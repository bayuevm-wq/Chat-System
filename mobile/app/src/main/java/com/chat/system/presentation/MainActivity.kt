package com.chat.system.presentation

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.chat.system.data.local.ChatDatabase
import com.chat.system.data.local.SessionManager
import com.chat.system.data.repository.ChatRepositoryImpl
import com.chat.system.domain.repository.ChatRepository
import com.chat.system.presentation.auth.*
import com.chat.system.presentation.chat.ChatRoomScreen
import com.chat.system.presentation.chat.ChatViewModel
import com.chat.system.presentation.dashboard.DashboardScreen
import com.chat.system.presentation.call.CallScreen
import com.chat.system.ui.theme.DistributedChatTheme
import com.google.gson.Gson

class MainActivity : ComponentActivity() {

    private lateinit var repository: ChatRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState);

        // 1. Initialize Singletons for Local Storage and API wiring
        val db = ChatDatabase.getDatabase(this)
        val sessionManager = SessionManager(this)
        val gson = Gson()
        repository = ChatRepositoryImpl(db.chatDao(), sessionManager, gson)

        // 2. Set content view using Jetpack Compose
        setContent {
            DistributedChatTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    ChatAppNavHost(repository)
                }
            }
        }
    }
}

class CustomViewModelFactory(private val repository: ChatRepository) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(AuthViewModel::class.java)) {
            return AuthViewModel(repository) as T
        }
        if (modelClass.isAssignableFrom(ChatViewModel::class.java)) {
            return ChatViewModel(repository) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}

@Composable
fun ChatAppNavHost(repository: ChatRepository) {
    val navController = rememberNavController()
    val factory = CustomViewModelFactory(repository)

    val authViewModel: AuthViewModel = viewModel(factory = factory)
    val chatViewModel: ChatViewModel = viewModel(factory = factory)

    NavHost(
        navController = navController,
        startDestination = "splash"
    ) {
        // Splash view route
        composable("splash") {
            SplashScreen(
                onNavigateNext = {
                    val user = repository.getCachedUser()
                    if (user != null) {
                        navController.navigate("dashboard") {
                            popUpTo("splash") { inclusive = true }
                        }
                    } else {
                        navController.navigate("login") {
                            popUpTo("splash") { inclusive = true }
                        }
                    }
                }
            )
        }

        // Login Screen route
        composable("login") {
            LoginScreen(
                viewModel = authViewModel,
                onNavigateToRegister = { navController.navigate("register") },
                onNavigateToDashboard = {
                    navController.navigate("dashboard") {
                        popUpTo("login") { inclusive = true }
                    }
                }
            )
        }

        // Register Screen route
        composable("register") {
            RegisterScreen(
                viewModel = authViewModel,
                onNavigateToLogin = { navController.popBackStack() },
                onNavigateToDashboard = {
                    navController.navigate("dashboard") {
                        popUpTo("register") { inclusive = true }
                        popUpTo("login") { inclusive = true }
                    }
                }
            )
        }

        // Main Dashboard Screen route
        composable("dashboard") {
            DashboardScreen(
                chatViewModel = chatViewModel,
                authViewModel = authViewModel,
                onNavigateToChat = { roomId ->
                    chatViewModel.setActiveRoom(roomId)
                    navController.navigate("chat_room")
                },
                onNavigateToCall = {
                    navController.navigate("call_screen")
                },
                onLogout = {
                    authViewModel.logout()
                    navController.navigate("login") {
                        popUpTo("dashboard") { inclusive = true }
                    }
                }
            )
        }

        // Chat Timeline Screen route
        composable("chat_room") {
            ChatRoomScreen(
                viewModel = chatViewModel,
                onNavigateBack = { navController.popBackStack() },
                onNavigateToCall = { navController.navigate("call_screen") }
            )
        }

        // Audio Call Simulation Screen route
        composable("call_screen") {
            CallScreen(
                onNavigateBack = { navController.popBackStack() }
            )
        }
    }
}

@Composable
fun SplashScreen(onNavigateNext: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
        contentAlignment = Alignment.Center
    ) {
        LaunchedEffect(key1 = true) {
            delay(1500) // Display splash logo for 1.5s
            onNavigateNext()
        }

        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            // Elegant modern loader animation
            CircularProgressIndicator(
                color = MaterialTheme.colorScheme.primary,
                strokeWidth = 3.dp,
                modifier = Modifier.size(48.dp)
            )
            Spacer(modifier = Modifier.height(24.dp))
            Text(
                text = "NODECHAT MOBILE",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 2.5.sp,
                color = MaterialTheme.colorScheme.primary
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Secured Distributed Communication",
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                letterSpacing = 1.sp
            )
        }
    }
}
