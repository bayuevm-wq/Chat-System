package com.chat.system.presentation.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.chat.system.domain.model.User
import com.chat.system.domain.repository.ChatRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

sealed class AuthUiState {
    object Idle : AuthUiState()
    object Loading : AuthUiState()
    data class Success(val user: User) : AuthUiState()
    data class Error(val message: String) : AuthUiState()
}

class AuthViewModel(private val repository: ChatRepository) : ViewModel() {

    private val _uiState = MutableStateFlow<AuthUiState>(AuthUiState.Idle)
    val uiState: StateFlow<AuthUiState> = _uiState

    private val _apiHost = MutableStateFlow(repository.getApiHost())
    val apiHost: StateFlow<String> = _apiHost

    init {
        // Auto-login check
        val cached = repository.getCachedUser()
        if (cached != null) {
            _uiState.value = AuthUiState.Success(cached)
        }
    }

    fun setApiHost(host: String) {
        repository.setApiHost(host)
        _apiHost.value = host
    }

    fun login(email: String, password: String) {
        if (email.isBlank() || password.isBlank()) {
            _uiState.value = AuthUiState.Error("Please fill out all credentials.")
            return
        }
        
        _uiState.value = AuthUiState.Loading
        viewModelScope.launch {
            repository.login(email, password)
                .onSuccess { user ->
                    _uiState.value = AuthUiState.Success(user)
                }
                .onFailure { error ->
                    _uiState.value = AuthUiState.Error(error.message ?: "Authentication failed.")
                }
        }
    }

    fun register(username: String, email: String, password: String, displayName: String?) {
        if (username.isBlank() || email.isBlank() || password.isBlank()) {
            _uiState.value = AuthUiState.Error("Please fill out all mandatory fields.")
            return
        }

        _uiState.value = AuthUiState.Loading
        viewModelScope.launch {
            repository.register(username, email, password, displayName)
                .onSuccess { user ->
                    _uiState.value = AuthUiState.Success(user)
                }
                .onFailure { error ->
                    _uiState.value = AuthUiState.Error(error.message ?: "Registration failed.")
                }
        }
    }

    fun resetState() {
        _uiState.value = AuthUiState.Idle
    }

    fun logout() {
        repository.logout()
        _uiState.value = AuthUiState.Idle
    }
}
