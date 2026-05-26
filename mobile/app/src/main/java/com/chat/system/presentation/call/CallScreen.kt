package com.chat.system.presentation.call

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.chat.system.ui.theme.DarkSurface
import com.chat.system.ui.theme.DarkSurfaceVariant

@Composable
fun CallScreen(
    onNavigateBack: () -> Unit
) {
    var isMuted by remember { mutableStateOf(false) }
    var isSpeakerOn by remember { mutableStateOf(false) }

    // Pulsing Infinite Soundwave Animation Setup
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    
    val pulseScale1 by infiniteTransition.animateFloat(
        initialValue = 1.0f,
        targetValue = 2.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(1500, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "scale1"
    )
    val pulseAlpha1 by infiniteTransition.animateFloat(
        initialValue = 0.4f,
        targetValue = 0.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(1500, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "alpha1"
    )

    val pulseScale2 by infiniteTransition.animateFloat(
        initialValue = 1.0f,
        targetValue = 2.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(1500, delayMillis = 750, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "scale2"
    )
    val pulseAlpha2 by infiniteTransition.animateFloat(
        initialValue = 0.4f,
        targetValue = 0.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(1500, delayMillis = 750, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "alpha2"
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier.fillMaxHeight()
        ) {
            // Calling details
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.padding(top = 60.dp)
            ) {
                Text(
                    text = "Node Peer Server 2",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White
                )
                Text(
                    text = "Distributed Sync Call active",
                    fontSize = 13.sp,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(top = 8.dp)
                )
            }

            // Pulsing Avatar Core (WebRTC Soundwaves simulator)
            Box(
                modifier = Modifier.size(240.dp),
                contentAlignment = Alignment.Center
            ) {
                // Wave 1
                Box(
                    modifier = Modifier
                        .size(100.dp)
                        .background(
                            MaterialTheme.colorScheme.primary.copy(alpha = pulseAlpha1),
                            CircleShape
                        )
                        .align(Alignment.Center)
                        .fillMaxSize(pulseScale1)
                )
                // Wave 2
                Box(
                    modifier = Modifier
                        .size(100.dp)
                        .background(
                            MaterialTheme.colorScheme.primary.copy(alpha = pulseAlpha2),
                            CircleShape
                        )
                        .align(Alignment.Center)
                        .fillMaxSize(pulseScale2)
                )

                // Avatar Container
                Box(
                    modifier = Modifier
                        .size(110.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.primary),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "NP",
                        fontSize = 32.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.background
                    )
                }
            }

            // Calls controls footer
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.padding(bottom = 40.dp)
            ) {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(20.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Mute Toggle Button
                    Button(
                        onClick = { isMuted = !isMuted },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = if (isMuted) Color.White else DarkSurface
                        ),
                        shape = RoundedCornerShape(14.dp),
                        modifier = Modifier.size(54.dp),
                        contentPadding = PaddingValues(0.dp)
                    ) {
                        Text(
                            text = if (isMuted) "🔇" else "🎙️",
                            fontSize = 18.sp
                        )
                    }

                    // Hang up button
                    Button(
                        onClick = onNavigateBack,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.error
                        ),
                        shape = CircleShape,
                        modifier = Modifier.size(72.dp),
                        contentPadding = PaddingValues(0.dp)
                    ) {
                        Icon(
                            Icons.Default.Call,
                            contentDescription = "Hang Up",
                            tint = Color.White,
                            modifier = Modifier.size(28.dp)
                        )
                    }

                    // Speaker Toggle Button
                    Button(
                        onClick = { isSpeakerOn = !isSpeakerOn },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = if (isSpeakerOn) Color.White else DarkSurface
                        ),
                        shape = RoundedCornerShape(14.dp),
                        modifier = Modifier.size(54.dp),
                        contentPadding = PaddingValues(0.dp)
                    ) {
                        Text(
                            text = if (isSpeakerOn) "🔊" else "🔈",
                            fontSize = 18.sp
                        )
                    }
                }
            }
        }
    }
}
