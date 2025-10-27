<template>
  <div :class="['graph-section', { 'wrapper-collapsed': propsCollapsed }]">
    <div class="graph-container has-right-panel" ref="graphContainer">
      <!-- Only render content when not collapsed -->
      <template v-if="!propsCollapsed">
        <div v-if="loading" class="loading">Loading discussion data...</div>
        <div v-else-if="error" class="error">{{ error }}</div>
        <div v-else class="graph-visualization">
          <!-- D3Tree visualization for testing -->
          <D3Tree
            :treeData="treeForRender"
            :width="800"
            :height="600"
            @addToChat="handleAddToChat"
          />
        </div>
      </template>
    </div>

    <!-- Right fixed vertical panel (full-height, not scrollable) -->
    <aside class="right-fixed-panel" aria-hidden="false">
      <button
        class="collapse-toggle"
        @click="toggleLocal"
        :aria-pressed="propsCollapsed"
        title="Collapse / Expand graph"
      >
        <span v-if="!propsCollapsed">◀</span>
        <span v-else>▶</span>
      </button>
    </aside>

    <!-- Node detail modal -->
    <Modal
      :is-visible="!!selectedNode"
      :title="selectedNode ? `${selectedNode.type.toUpperCase()} - ${selectedNode.id}` : ''"
      :content="selectedNode?.text || ''"
      @close="handleCloseModal"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
// GraphControls removed — header controls not needed
import Modal from '../shared/Modal.vue'
import { useGraphData } from '../../composables/useGraphData'
import { useGraphPositions } from '../../composables/useGraphPositions'
import type { ArgumentNode, ChatMessage } from '../../types/graph'
import D3Tree from './D3Tree.vue'

interface Props {
  title?: string
}

interface Emits {
  addMessage: [message: ChatMessage]
  'toggle-collapse': []
}

// accept collapsed prop from parent so the button can reflect state
interface ExtendedProps extends Props {
  collapsed?: boolean
}

const props = withDefaults(defineProps<ExtendedProps>(), {
  title: 'Climate Change Discussion',
  collapsed: false,
})

// local alias to use inside template expression (scoped template refs don't allow direct props access in <script setup> expressions in older setups)
const propsCollapsed = computed(() => props.collapsed)

const route = useRoute()
const displayedTitle = computed(() => {
  const q = (route.query.file as string) || ''
  return q ? `Discussion: ${q}` : props.title
})

const emit = defineEmits<Emits>()

const toggleLocal = () => {
  emit('toggle-collapse')
}

// Graph container ref
const graphContainer = ref<HTMLElement>()

// Use composables
const {
  discussionBranches,
  selectedBranch,
  loading,
  error,
  currentBranchNodes,
  thesisNode,
  loadDiscussionData,
  expandBranch,
  isBranchExpanded,
  expandedBranches,
  discussionRoot,
  getBranchChain,
} = useGraphData()

const {
  getBranchColor,
  getThesisConnectionStart,
  getBranchConnectionEnd,
  getSingleBranchPosition,
  getSingleConnectionStart,
  getSingleConnectionEnd,
} = useGraphPositions(graphContainer)

// Local state
const selectedNode = ref<ArgumentNode | null>(null)

const treeForRender = computed(() => {
  return discussionRoot.value || { id: 'empty', text: 'No data', children: [] }
})

const handleSelectNode = (node: ArgumentNode) => {
  selectedNode.value = node
}

const handleCloseModal = () => {
  selectedNode.value = null
}

const handleAddToChat = (node: ArgumentNode, branchIndex: number) => {
  // Create a message from the selected node
  const message: ChatMessage = {
    text: node.text,
    type: 'user',
    nodeId: node.id,
    nodeType: node.type,
  }

  // Emit the message to the parent component
  emit('addMessage', message)

  // Expand this branch to show the next layer
  expandBranch(branchIndex)

  // Optional: Show a brief confirmation
  console.log(`Added to chat: ${node.type} - ${node.text.substring(0, 50)}...`)
  console.log(`Expanded branch ${branchIndex + 1}`)
}

// Initialize data
onMounted(() => {
  const fname = (route.query.file as string) || undefined
  loadDiscussionData(fname)
})

// Reload when route query changes (select another file)
watch(
  () => route.query.file,
  (nv, ov) => {
    const fname = (nv as string) || undefined
    console.log('Route file changed:', fname)
    loadDiscussionData(fname)
  },
)
</script>

<style scoped>
.graph-section {
  flex: 1;
  padding: 20px;
  background-color: #f8f9fa;
  overflow: hidden;
  position: relative;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

/* When collapsed, remove the background color to match the unified background */
.graph-section.wrapper-collapsed {
  background-color: transparent;
}

.graph-header {
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 15px;
  flex-shrink: 0;
}

.graph-header h2 {
  margin: 0;
  color: #343a40;
  font-size: 24px;
}

.graph-container {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  position: relative;
  overflow: auto;
  flex: 1;
  min-height: 0;
}

/* Hide the graph container when collapsed - only show the dark panel */
.graph-section.wrapper-collapsed .graph-container {
  background: transparent;
  box-shadow: none;
  padding: 0;
}

/* When a right-side fixed panel is present we add extra right padding so content doesn't hide underneath it */
.graph-container.has-right-panel {
  /* Add extra right padding so the content doesn't hide underneath the fixed right panel. */
  /* Keep some breathing room for larger panel widths on collapse. */
  padding-right: 110px;
}

/* Right-side fixed vertical panel: full height of the graph card, fixed (not scrollable) */
.right-fixed-panel {
  /* Position the fixed panel along the right edge and span the full height
     of the graph card. Using top/bottom avoids translateY and ensures a
     continuous vertical strip. */
  position: absolute;
  right: 6px; /* small inset from the wrapper edge */
  top: 12px;
  bottom: 12px;
  width: 44px; /* narrow vertical strip */
  height: auto; /* let top/bottom determine height */
  background: transparent;
  border-radius: 10px;
  box-shadow: none;
  z-index: 60;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: visible;
  padding: 6px 4px;
  transition:
    background 180ms ease,
    box-shadow 180ms ease,
    padding 180ms ease;
}

/* no hover effect on the panel itself; interactions are on the button only */

.right-fixed-panel .panel-header {
  font-weight: 600;
  margin-bottom: 8px;
  color: #222;
}

.right-fixed-panel .panel-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* When the graph component is in collapsed state we render a compact dark vertical
   box inside the graph card and center the collapse toggle inside it. The parent
   controls the collapsed state via the `collapsed` prop; we mirror that state
   as the local class `wrapper-collapsed` on the root .graph-section. */
.graph-section.wrapper-collapsed .right-fixed-panel {
  /* When the graph-component is collapsed, present a solid dark rounded
     vertical box that runs nearly the full height of the card to match
     the visual reference. Keep a small top/bottom inset for breathing room. */
  background: white;
  border-radius: 10px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
  padding: 8px 6px;
  right: 6px;
  top: 12px;
  bottom: 12px;
  width: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.graph-section.wrapper-collapsed .right-fixed-panel .collapse-toggle {
  background: transparent;
  border: none;
  width: 28px;
  height: 28px;
  padding: 0;
  color: #495057; /* Dark color for visibility on white background */
}

/* move the panel slightly left when the outer wrapper (page-level) also shrinks so
   the toggle aligns with the pseudo-element box drawn on the wrapper */
.graph-wrapper.collapsed .graph-section.wrapper-collapsed .right-fixed-panel {
  /* When the page-level wrapper shrinks (collapsed state), nudge the panel
     left so it aligns with the visible pseudo-element box on the wrapper. Keep
     full-height insets so it visually matches. */
  left: 10px;
  right: auto;
  position: absolute;
  top: 12px;
  bottom: 12px;
  z-index: 70; /* above wrapper pseudo-element so the button is clickable */
}

.loading,
.error {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  font-size: 18px;
  color: #6c757d;
}

.error {
  color: #dc3545;
}

.graph-visualization {
  position: relative;
  min-height: 100%;
  width: 100%;
}

/* Responsive design */
@media (max-width: 1200px) {
  .graph-container {
    padding: 15px;
  }

  .graph-header h2 {
    font-size: 20px;
  }
}

/* Collapse toggle inside graph card */
.collapse-toggle {
  position: absolute;
  right: 16px;
  bottom: 16px;
  z-index: 50;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: rgba(255, 255, 255, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  cursor: pointer;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
  transition:
    transform 160ms ease,
    box-shadow 160ms ease,
    opacity 160ms ease;
  opacity: 0.7;
}

/* When the collapse toggle is placed inside the right fixed panel, override absolute positioning
   so it flows inside the panel and sits at the bottom centered. */
.right-fixed-panel .collapse-toggle {
  position: relative;
  right: auto;
  bottom: auto;
  margin-top: auto; /* push to bottom */
  align-self: center; /* center horizontally */
  /* icon-only appearance */
  width: auto;
  height: auto;
  padding: 4px;
  background: transparent;
  border: none;
  box-shadow: none;
  opacity: 1;
}

/* give the toggle button its circular surface only when the button itself is hovered/focused */
.right-fixed-panel .collapse-toggle:hover,
.right-fixed-panel .collapse-toggle:focus {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(0, 0, 0, 0.06);
  width: 40px;
  height: 40px;
  border-radius: 50%;
}

/* Slight lift on hover/focus - appear more visible when interacting */
.collapse-toggle:hover,
.collapse-toggle:focus {
  transform: translateY(-3px);
  opacity: 1;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.12);
}

/* Make the control subtle until the user hovers the graph card */
.graph-section .collapse-toggle {
  opacity: 0.5;
}
.graph-section:hover .collapse-toggle {
  opacity: 1;
}

.collapse-toggle svg {
  display: block;
}

/* Rotate the chevron when collapsed */
.collapse-toggle[data-collapsed='true'] {
  transform: rotate(180deg);
}

@media (max-width: 768px) {
  .graph-section {
    padding: 15px;
  }

  .graph-header {
    flex-direction: column;
    align-items: stretch;
    margin-bottom: 15px;
  }

  .graph-container {
    padding: 10px;
  }

  .graph-header h2 {
    font-size: 18px;
  }
}

@media (max-width: 480px) {
  .graph-section {
    padding: 10px;
  }

  .graph-container {
    padding: 8px;
  }
}
</style>
