<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DiscussionGraph from '../components/graph/DiscussionGraph.vue'
import TelegramChat from '../components/chat/TelegramChat.vue'
import FileSelectorModal from '../components/shared/FileSelectorModal.vue'
import { useUsers } from '../composables/useUsers'
import { useGraphData } from '../composables/useGraphData'

interface ChatMessage {
  id: number
  referenceId: string
  speaker: string
  text: string
  addressees?: string[]
}

const { loadUsers } = useUsers()
const { loadDiscussionData, discussionRoot } = useGraphData()

const thesisAuthor = ref<{ name: string }>({ name: 'Thesis' })

// Initialize messages empty; we'll place the thesis statement in the input for editing
const messages = ref<ChatMessage[]>([])

// Router/route and modal state
const route = useRoute()
const router = useRouter()
const showFileSelector = ref(false)

// Determine the active file using route params first, then query string.
const currentFile = computed(() => {
  const p = route.params.file as string | undefined
  const q = route.query.file as string | undefined
  return p || q || undefined
})

// Load personas from backend and create the initial thesis message
onMounted(async () => {
  // Ensure users/personas are loaded so the thesis statement is valid
  try {
    if (currentFile.value) {
      await loadUsers(currentFile.value)
    }
  } catch (e) {
    // If loading fails, continue — we'll still try to get a thesis statement
    // (keep app resilient to backend issues)
    console.warn('loadUsers failed in DiscussionPage onMounted', e)
  }

  // If there's an active file, load the discussion tree and use the first node as the initial input
  let firstNodeText: string | null = null
  try {
    if (currentFile.value) {
      await loadDiscussionData(currentFile.value)
      // discussionRoot may be an object, or an array, or have children
      const root = discussionRoot.value
      let firstNode: any = null
      if (!root) {
        firstNode = null
      } else if (Array.isArray(root)) {
        firstNode = root.length > 0 ? root[0] : null
      } else if (root.text) {
        firstNode = root
      } else if (root.children && root.children.length > 0) {
        firstNode = root.children[0]
      }

      if (firstNode && firstNode.text) {
        firstNodeText = String(firstNode.text)
        // set thesis author from the speaker if available
        if (firstNode.speaker) thesisAuthor.value.name = String(firstNode.speaker)
      }
    }
  } catch (e) {
    console.warn('loadDiscussionData failed in DiscussionPage onMounted', e)
  }

  // Fallback: if we couldn't retrieve a first node, leave the input empty so the user can type
  chatInputValue.value = firstNodeText || ''

  // After child mounts, set the speaker in the TelegramChat (if it exposes setSpeaker)
  await nextTick()
  if (telegramChatRef.value && telegramChatRef.value.setSpeaker) {
    telegramChatRef.value.setSpeaker(thesisAuthor.value.name)
  }

  // Show selector if no file param or query
  if (!currentFile.value) showFileSelector.value = true
})

const chatInputValue = ref('')

const handleSendMessage = (message: {
  speaker: string
  text: string
  addressees: string[]
  referenceId?: string
}) => {
  // Map the incoming 'speaker' field from TelegramChat to our internal 'speaker' property.
  messages.value.push({
    id: messages.value.length + 1,
    referenceId: message.referenceId || '',
    speaker: message.speaker,
    text: message.text,
    addressees: Array.isArray(message.addressees) ? message.addressees : [],
  })
}

const handleUpdateInput = (value: string) => {
  chatInputValue.value = value
}

const telegramChatRef = ref()
const handleAddFromGraph = (messageData: any) => {
  chatInputValue.value = messageData.text
  // Try to find the node in the loaded discussion tree and use its speaker as speaker
  const findNodeById = (referenceId: string, node: any = discussionRoot.value): any | null => {
    if (!node) return null
    if (node.id === referenceId) return node
    if (node.children && node.children.length > 0) {
      for (const child of node.children) {
        const found = findNodeById(referenceId, child)
        if (found) return found
      }
    }
    return null
  }

  let speakerToSet = thesisAuthor.value.name
  try {
    const node = messageData.referenceId ? findNodeById(messageData.referenceId) : null
    if (node && node.speaker) {
      speakerToSet = String(node.speaker)
      thesisAuthor.value.name = speakerToSet
    }
  } catch (e) {
    // keep fallback
  }

  // Set the speaker in the chat input via the child component (if available)
  if (telegramChatRef.value && telegramChatRef.value.setSpeaker) {
    telegramChatRef.value.setSpeaker(speakerToSet)
  }
  // Also set the referenceId in the chat so outgoing messages include the node id
  if (telegramChatRef.value && telegramChatRef.value.setReferenceId) {
    telegramChatRef.value.setReferenceId(messageData.referenceId || null)
  }
}

// Collapse state for left graph panel
const graphCollapsed = ref(false)
const toggleGraphCollapsed = () => {
  graphCollapsed.value = !graphCollapsed.value
}
</script>

<template>
  <div class="discussion-page">
    <!-- Navigation Header -->
    <div class="nav-header">
      <router-link to="/" class="back-button"> ← Back to Home </router-link>
      <h1 class="page-title">Discussion Interface</h1>
      <button class="open-file-button" @click="showFileSelector = true">Choose file</button>
      <!-- Collapse toggle moved into the graph container -->
      <div class="nav-spacer"></div>
    </div>

    <!-- Main Discussion Container -->
    <div class="discussion-container">
      <!-- Left side - Graph representation (collapsible) -->
      <div :class="['graph-wrapper', { collapsed: graphCollapsed }]">
        <DiscussionGraph
          @add-message="handleAddFromGraph"
          :collapsed="graphCollapsed"
          @toggle-collapse="toggleGraphCollapsed"
        />
      </div>

      <!-- Right side - Telegram chat simulation (1/4 width) -->
      <div class="chat-wrapper" :class="{ expanded: graphCollapsed }">
        <TelegramChat
          ref="telegramChatRef"
          :messages="messages"
          :input-value="chatInputValue"
          :file="currentFile"
          @send-message="handleSendMessage"
          @update-input="handleUpdateInput"
          title="Discussion Chat"
          current-user="You"
          input-placeholder="Type a message..."
        />
      </div>
    </div>

    <FileSelectorModal
      v-if="showFileSelector"
      @select="
        (name) => {
          showFileSelector = false
          // Navigate using the named route and param so URL becomes /discussion/:file
          router.push({ name: 'discussion', params: { file: name } })
        }
      "
      @close="() => (showFileSelector = false)"
    />
  </div>
</template>

<style scoped>
.discussion-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.nav-header {
  display: flex;
  align-items: center;
  padding: 1rem 1.5rem;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  min-height: 60px;
  box-sizing: border-box;
}

.back-button {
  color: #6c757d;
  text-decoration: none;
  font-weight: 500;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.back-button:hover {
  background: #e9ecef;
  color: #495057;
}

.page-title {
  flex: 1;
  text-align: center;
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #495057;
}

.nav-spacer {
  width: 120px; /* Same width as back button to center the title */
}

.discussion-container {
  display: flex;
  flex: 1;
  min-height: 0; /* Allow flex children to shrink */
  background-color: #f8f9fa; /* unified page background */
}

/* Give the graph section flexible width */
.discussion-container > :first-child {
  flex: 1;
  min-width: 0; /* Allow shrinking below content width */
  overflow: hidden; /* Prevent content from breaking layout */
}

.discussion-container > .chat-wrapper,
.discussion-container > :last-child {
  flex: 0 0 320px; /* Fixed width for chat, but allow it to shrink on very small screens */
  min-width: 280px;
}

.chat-wrapper {
  display: flex;
  flex-direction: column; /* ensure children stack and flex correctly */
  min-width: 0;
  min-height: 0; /* allow children (chat card) to shrink inside flex container */
  padding: 20px 20px 20px 0px;
  background-color: #f8f9fa; /* same surrounding background as graph-section */
  box-sizing: border-box;
}

.chat-wrapper.expanded {
  flex: 1 1 auto !important; /* force the chat to grow when graph is collapsed */
  min-width: 0 !important;
  width: auto !important;
}

/* Extra safety: when collapsed, make the chat occupy remaining space explicitly */
.discussion-container .chat-wrapper.expanded {
  flex-basis: 0 !important;
}

/* Wrapper for the left graph section so it can be collapsed */
.graph-wrapper {
  position: relative;
  display: flex;
  flex: 1;
  min-width: 0;
  transition:
    width 220ms ease,
    margin 220ms ease;
  overflow: hidden;
  background-color: #f8f9fa; /* unified page background */
}

.graph-wrapper.collapsed {
  /* shrink wrapper to a narrow strip but render a visible vertical box via a pseudo-element
     so the user sees a clear affordance to expand. Keep component mounted. */
  width: 64px; /* a bit wider so the visual box can have a right margin */
  min-width: 64px;
  margin-right: 40px;
  flex: 0 0 64px; /* collapse to narrow strip */
  padding: 0;
  overflow: visible; /* allow the pseudo-element shadow to show */
  background-color: #f8f9fa; /* unified page background */
  height: auto; /* Let it maintain the same height as when expanded */
}

/* Reduce inner padding of the graph-section when the wrapper is collapsed so
   elements positioned relative to it (toggle) stay inside the narrow strip. */
.graph-wrapper.collapsed .graph-section {
  padding: 6px !important;
}

/* draw a vertical rounded box inside the collapsed wrapper to match the reference
   (white box with subtle shadow containing the toggle). We use a pseudo-element so
   the DOM structure remains unchanged. */

.collapse-toggle {
  position: absolute;
  right: 12px;
  bottom: 12px;
  z-index: 40;
  width: 36px;
  height: 36px;
  border-radius: 6px;
  border: 1px solid #e3e6ea;
  background: #ffffffcc;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.graph-wrapper.collapsed .collapse-toggle {
  right: 4px;
  bottom: 4px;
  padding: 10px;
}

.graph-wrapper .collapse-toggle:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(100, 150, 250, 0.12);
}

/* Show the in-graph toggle (positioned bottom-right) */
.graph-wrapper .collapse-toggle {
  display: flex; /* show the in-graph toggle inside the graph box */
}

.collapse-header-button {
  margin-left: 8px;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid #dfe4e8;
  background: white;
  cursor: pointer;
  color: #343a40;
  font-weight: 600;
}

.collapse-header-button:hover {
  background: #f1f5f8;
}

/* Responsive design */
@media (max-width: 1200px) {
  .discussion-container > :last-child {
    flex: 0 0 280px;
  }
}

@media (max-width: 768px) {
  .nav-header {
    padding: 0.75rem 1rem;
  }

  .page-title {
    font-size: 1.1rem;
  }

  .discussion-container {
    flex-direction: column;
  }

  .discussion-container > :first-child {
    flex: 1;
    min-height: 60vh;
  }

  .discussion-container > :last-child {
    flex: 0 0 40vh;
    min-width: auto;
  }
}

@media (max-width: 480px) {
  .nav-header {
    padding: 0.5rem;
  }

  .back-button {
    padding: 0.5rem;
    font-size: 0.9rem;
  }

  .page-title {
    font-size: 1rem;
  }

  .nav-spacer {
    width: 80px;
  }

  .discussion-container > :first-child {
    min-height: 50vh;
  }

  .discussion-container > :last-child {
    flex: 0 0 50vh;
  }
}
</style>
