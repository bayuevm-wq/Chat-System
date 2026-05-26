package com.chat.system.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.chat.system.data.local.entity.MessageEntity
import com.chat.system.data.local.entity.PendingMessageEntity
import com.chat.system.data.local.entity.RoomEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface ChatDao {

    // ── Rooms ──
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertRooms(rooms: List<RoomEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertRoom(room: RoomEntity)

    @Query("SELECT * FROM rooms")
    fun getRoomsFlow(): Flow<List<RoomEntity>>

    @Query("SELECT * FROM rooms WHERE id = :roomId")
    suspend fun getRoomById(roomId: String): RoomEntity?

    @Query("DELETE FROM rooms WHERE id = :roomId")
    suspend fun deleteRoomById(roomId: String)

    @Query("DELETE FROM rooms")
    suspend fun clearRooms()

    // ── Messages ──
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMessages(messages: List<MessageEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMessage(message: MessageEntity)

    @Query("SELECT * FROM messages WHERE roomId = :roomId ORDER BY timestamp ASC")
    fun getMessagesFlow(roomId: String): Flow<List<MessageEntity>>

    @Query("SELECT * FROM messages WHERE roomId = :roomId ORDER BY timestamp ASC")
    suspend fun getMessagesDirect(roomId: String): List<MessageEntity>

    @Query("DELETE FROM messages WHERE messageId = :messageId")
    suspend fun deleteMessageById(messageId: Int)

    @Query("DELETE FROM messages")
    suspend fun clearMessages()

    // ── Pending Messages (Offline Resilient Queue) ──
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPendingMessage(pending: PendingMessageEntity): Long

    @Query("SELECT * FROM pending_messages")
    suspend fun getAllPendingMessages(): List<PendingMessageEntity>

    @Query("SELECT * FROM pending_messages WHERE roomId = :roomId ORDER BY timestamp ASC")
    fun getPendingMessagesFlow(roomId: String): Flow<List<PendingMessageEntity>>

    @Query("DELETE FROM pending_messages WHERE localId = :localId")
    suspend fun deletePendingMessage(localId: Int)
}
