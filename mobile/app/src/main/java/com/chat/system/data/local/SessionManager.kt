package com.chat.system.data.local

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKeys
import com.google.gson.Gson
import com.chat.system.domain.model.User

class SessionManager(context: Context) {
    
    private val masterKeyAlias = MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC)
    
    private val prefs: SharedPreferences = EncryptedSharedPreferences.create(
        "secure_chat_session",
        masterKeyAlias,
        context,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )
    
    private val gson = Gson()

    fun saveAuthSession(user: User, accessToken: String, refreshToken: String) {
        prefs.edit().apply {
            putString(KEY_USER, gson.toJson(user))
            putString(KEY_ACCESS_TOKEN, accessToken)
            putString(KEY_REFRESH_TOKEN, refreshToken)
            apply()
        }
    }

    fun getCachedUser(): User? {
        val userJson = prefs.getString(KEY_USER, null) ?: return null
        return try {
            gson.fromJson(userJson, User::class.java)
        } catch (e: Exception) {
            null
        }
    }

    fun getAccessToken(): String? = prefs.getString(KEY_ACCESS_TOKEN, null)

    fun getRefreshToken(): String? = prefs.getString(KEY_REFRESH_TOKEN, null)

    fun clearSession() {
        prefs.edit().apply {
            remove(KEY_USER)
            remove(KEY_ACCESS_TOKEN)
            remove(KEY_REFRESH_TOKEN)
            apply()
        }
    }

    // Helper configuration to override local IP during testing
    fun saveApiEndpoint(endpoint: String) {
        prefs.edit().putString(KEY_API_ENDPOINT, endpoint).apply()
    }

    fun getApiEndpoint(): String {
        return prefs.getString(KEY_API_ENDPOINT, "10.0.2.2:8000") ?: "10.0.2.2:8000"
    }

    companion object {
        private const val KEY_USER = "auth_user"
        private const val KEY_ACCESS_TOKEN = "access_token"
        private const val KEY_REFRESH_TOKEN = "refresh_token"
        private const val KEY_API_ENDPOINT = "api_endpoint"
    }
}
