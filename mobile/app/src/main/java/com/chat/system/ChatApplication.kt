package com.chat.system

import android.app.Application
import android.util.Log

class ChatApplication : Application() {
    
    override fun onCreate() {
        super.onCreate()
        Log.i("ChatApplication", "Distributed Chat Native Android application initialized.")
    }
}
