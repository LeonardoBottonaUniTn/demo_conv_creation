<template>
  <div class="chat-header">
    <div class="user-info">
      <div class="profile-icon">
        {{ otherUser.name[0].toUpperCase() }}
      </div>
      <div class="user-details">
        <div class="user-name">{{ otherUser.name }}</div>
        <div class="status">
          {{ isTyping ? 'typing...' : getStatus() }}
        </div>
        <div v-if="otherUser.description" class="user-description">
          {{ otherUser.description }}
        </div>
      </div>
    </div>
    <div class="header-actions">
      <div v-if="otherUser.stance" class="stance-badge" :class="otherUser.stance">
        {{ otherUser.stance }}
      </div>
      <button @click="handleClearChat" class="clear-btn">Clear</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ChatUser } from '../../../types/chat'

interface Props {
  currentUser: ChatUser
  otherUser: ChatUser
  isTyping?: boolean
}

interface Emits {
  clearChat: []
}

const props = withDefaults(defineProps<Props>(), {
  isTyping: false,
})

const emit = defineEmits<Emits>()

const getStatus = () => {
  if (props.otherUser.isOnline) {
    return 'online'
  } else if (props.otherUser.lastSeen) {
    const timeDiff = Date.now() - props.otherUser.lastSeen.getTime()
    const minutes = Math.floor(timeDiff / 60000)
    if (minutes < 1) return 'last seen just now'
    if (minutes < 60) return `last seen ${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    return `last seen ${hours}h ago`
  }
  return 'offline'
}

const handleClearChat = () => {
  emit('clearChat')
}
</script>

<style scoped>
.chat-header {
  background-color: #0088cc;
  color: white;
  padding: 15px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.profile-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #ffffff;
  color: #0088cc;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 16px;
  flex-shrink: 0;
}

.user-details {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.user-name {
  font-weight: 600;
  font-size: 16px;
}

.status {
  font-size: 12px;
  opacity: 0.8;
}

.user-description {
  font-size: 10px;
  opacity: 0.7;
  margin-top: 2px;
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.stance-badge {
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
}

.stance-badge.positive {
  background-color: #4caf50;
  color: white;
}

.stance-badge.negative {
  background-color: #f44336;
  color: white;
}

.clear-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  padding: 6px 12px;
  border-radius: 15px;
  cursor: pointer;
  font-size: 12px;
}

.clear-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>
