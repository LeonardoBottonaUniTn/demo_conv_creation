<template>
  <div style="position: relative; width: 100%; height: 100%">
    <svg
      ref="svgRef"
      :width="width"
      :height="height"
      :viewBox="`0 0 ${width} ${height}`"
      preserveAspectRatio="xMinYMin meet"
      style="width: 100%; height: 100%; display: block"
    >
      <!-- Tree will be rendered here by d3 -->
    </svg>
    <div v-if="focusedNodeId" class="minitree-box">
      <svg
        ref="miniSvgRef"
        :width="200"
        :height="150"
        :viewBox="'0 0 200 150'"
        class="minitree-svg"
        @click="restoreFullTree"
      >
        <!-- Mini tree rendered by d3 -->
      </svg>
      <div class="minitree-label">
        <span>Mini tree <span style="font-weight: 400">(click to restore)</span></span>
      </div>
    </div>
    <Modal
      v-if="modalVisible"
      :isVisible="modalVisible"
      :title="modalTitle"
      :content="modalContent"
      @close="modalVisible = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import Modal from '@/components/shared/Modal.vue'
import * as d3 from 'd3'

const props = defineProps({
  treeData: { type: Object, required: true }, // d3-compatible tree
  width: { type: Number, default: 800 },
  height: { type: Number, default: 600 },
})

const svgRef = ref(null)
const miniSvgRef = ref(null)

const focusedNodeId = ref(null)
const focusedSubtree = ref(null)

const htmlButtons = ref([])
const emit = defineEmits(['addToChat'])

const modalVisible = ref(false)
const modalContent = ref('')
const modalTitle = ref('Details')

function handleExpand(fullText, nodeId) {
  modalContent.value = fullText
  modalTitle.value = nodeId ? `Node ${nodeId}` : 'Details'
  modalVisible.value = true
}

onMounted(() => {
  renderTree()
  renderMiniTree()
})

watch(
  () => props.treeData,
  () => {
    renderTree()
    renderMiniTree()
  },
)

watch(focusedNodeId, async () => {
  renderTree()
  await nextTick()
  renderMiniTree()
})

function renderTree() {
  const svg = d3.select(svgRef.value)
  svg.selectAll('*').remove() // Clear previous
  // Remove previous HTML buttons
  htmlButtons.value.forEach((btn) => btn.remove())
  htmlButtons.value = []

  let treeDataToRender = props.treeData
  if (focusedNodeId.value && focusedSubtree.value) {
    treeDataToRender = focusedSubtree.value
  }

  const root = d3.hierarchy(treeDataToRender)
  // Center tree vertically: reduce height and increase top margin
  const verticalPadding = 80
  const treeLayout = d3.tree().size([props.width, props.height - verticalPadding * 2])
  treeLayout(root)

  const nodes = root.descendants()
  const minX = d3.min(nodes, (d) => d.x)
  const maxX = d3.max(nodes, (d) => d.x)
  const treeWidth = maxX - minX
  const centerX = props.width / 2 - (minX + treeWidth / 2)

  // Center tree vertically in SVG
  const treeGroup = svg.append('g').attr('transform', `translate(${centerX}, ${verticalPadding})`)

  // Draw links
  treeGroup
    .append('g')
    .selectAll('path')
    .data(root.links())
    .join('path')
    .attr('fill', 'none')
    .attr('stroke', '#555')
    .attr('stroke-width', 2)
    .attr(
      'd',
      d3
        .linkVertical()
        .x((d) => d.x)
        .y((d) => d.y),
    )

  // Draw nodes
  treeGroup
    .append('g')
    .selectAll('g.node')
    .data(root.descendants())
    .join('g')
    .attr('class', 'node')
    .each(function (d) {
      const isFocusedTree = focusedNodeId.value && focusedSubtree.value
      const group = d3.select(this)
      if (isFocusedTree) {
        // Modern, clean node box using reference style
        const boxWidth = 260
        const boxHeight = 110
        let nodeTypeClass = ''
        switch (d.data.type) {
          case 'thesis':
            nodeTypeClass = 'node-thesis'
            break
          case 'pro':
            nodeTypeClass = 'node-pro'
            break
          case 'con':
            nodeTypeClass = 'node-con'
            break
          default:
            nodeTypeClass = ''
        }
        group
          .append('rect')
          .attr('x', d.x - boxWidth / 2)
          .attr('y', d.y - boxHeight / 2)
          .attr('width', boxWidth)
          .attr('height', boxHeight)
          .attr('rx', 15)
          .attr('class', `argument-node ${nodeTypeClass}`)
          .attr('fill', 'white')
          .attr('stroke', () => {
            switch (d.data.type) {
              case 'thesis':
                return '#28a745'
              case 'pro':
                return '#007bff'
              case 'con':
                return '#dc3545'
              default:
                return '#dee2e6'
            }
          })
          .attr('stroke-width', 3)
          .style('filter', 'drop-shadow(0 4px 15px rgba(0,0,0,0.1))')

        // Header: id (left), type (right)
        group
          .append('text')
          .attr('x', d.x - boxWidth / 2 + 12)
          .attr('y', d.y - boxHeight / 2 + 22)
          .attr('text-anchor', 'start')
          .attr('font-size', '12px')
          .attr('font-weight', '600')
          .attr('fill', '#6c757d')
          .text(d.data.id || '')

        group
          .append('text')
          .attr('x', d.x + boxWidth / 2 - 12)
          .attr('y', d.y - boxHeight / 2 + 22)
          .attr('text-anchor', 'end')
          .attr('font-size', '12px')
          .attr('font-weight', '600')
          .attr('fill', '#333')
          .attr('background-color', 'rgba(0,0,0,0.1)')
          .text((d.data.type || '').toUpperCase())

        // Main text
        const text = d.data.text || ''
        const wrap = (str, maxLen) => {
          const words = str.split(' ')
          const lines = []
          let line = ''
          words.forEach((word) => {
            if ((line + ' ' + word).trim().length > maxLen) {
              lines.push(line)
              line = word
            } else {
              line += (line ? ' ' : '') + word
            }
          })
          if (line) lines.push(line)
          return lines
        }
        // Only show 3 lines in the box
        const wrapped = wrap(text, 42)
        let textY = d.y - boxHeight / 2 + 38
        let lastTextY = textY
        // Show up to 2 lines, and if truncated, show 'Expand' as the third line
        let displayLines = wrapped.slice(0, 2)
        let isTruncated = wrapped.length > 3
        displayLines.forEach((line, i) => {
          lastTextY = textY + i * 16
          group
            .append('text')
            .attr('x', d.x)
            .attr('y', lastTextY)
            .attr('text-anchor', 'middle')
            .attr('font-size', '13px')
            .attr('font-weight', 'normal')
            .attr('fill', '#333')
            .text(line)
        })
        lastTextY = textY + 2 * 16
        if (isTruncated) {
          group
            .append('text')
            .attr('x', d.x)
            .attr('y', lastTextY)
            .attr('text-anchor', 'middle')
            .attr('font-size', '12px')
            .attr('fill', '#007bff')
            .attr('cursor', 'pointer')
            .text('Expand')
            .on('click', function (event) {
              event.stopPropagation()
              handleExpand(text, d.data.id)
            })
        } else if (wrapped.length >= 3) {
          // If not truncated but exactly 3 lines, show the third line
          group
            .append('text')
            .attr('x', d.x)
            .attr('y', lastTextY)
            .attr('text-anchor', 'middle')
            .attr('font-size', '13px')
            .attr('font-weight', 'normal')
            .attr('fill', '#333')
            .text(wrapped[2])
        }

        // Button centered inside box, below text, never overlapping and always inside box
        let buttonY = lastTextY + 18
        if (buttonY > d.y + boxHeight / 2 - 32) {
          buttonY = d.y + boxHeight / 2 - 32
        }
        // Button container for both buttons
        const buttonContainer = group
          .append('foreignObject')
          .attr('x', d.x - 110)
          .attr('y', buttonY)
          .attr('width', 220)
          .attr('height', 24)
          .append('xhtml:div')
          .style('display', 'flex')
          .style('gap', '8px')
          .style('justify-content', 'center')
          .style('align-items', 'center')

        // Add to chat button
        buttonContainer
          .append('xhtml:button')
          .attr('class', 'add-to-chat-hint')
          .style('width', '110px')
          .style('height', '24px')
          .style('border-radius', '12px')
          .style('background', 'rgba(0,123,255,0.15)')
          .style('color', '#007bff')
          .style('border', '1px solid rgba(0,123,255,0.3)')
          .style('font-size', '11px')
          .style('font-weight', '600')
          .style('cursor', 'pointer')
          .style('user-select', 'none')
          .style('transition', 'all 0.2s ease')
          .text('Add to chat')
          .on('click', function (event) {
            event.stopPropagation()
            emit('addToChat', d.data)
          })

        // Only show 'Focus this node' for parent and children of focused node
        let showFocusButton = false
        if (focusedNodeId.value && focusedSubtree.value) {
          // Parent
          if (d.parent && d.parent.data.id === focusedNodeId.value) {
            showFocusButton = true
          }
          // Children
          if (d.parent && d.data.id === focusedNodeId.value) {
            showFocusButton = false // Don't show for the focused node itself
          } else if (d.parent && d.parent.data.id === focusedNodeId.value) {
            showFocusButton = true
          } else if (d.children && d.parent && d.parent.data.id !== focusedNodeId.value) {
            // Check if focused node is parent of this node
            if (
              focusedSubtree.value.children &&
              focusedSubtree.value.children.some((child) => child.id === d.data.id)
            ) {
              showFocusButton = true
            }
          }
        }
        if (showFocusButton) {
          buttonContainer
            .append('xhtml:button')
            .attr('class', 'focus-node-hint')
            .style('width', '110px')
            .style('height', '24px')
            .style('border-radius', '12px')
            .style('background', 'rgba(40,167,69,0.15)')
            .style('color', '#28a745')
            .style('border', '1px solid rgba(40,167,69,0.3)')
            .style('font-size', '11px')
            .style('font-weight', '600')
            .style('cursor', 'pointer')
            .style('user-select', 'none')
            .style('transition', 'all 0.2s ease')
            .text('Focus this node')
            .on('click', function (event) {
              event.stopPropagation()
              focusedNodeId.value = d.data.id
              focusedSubtree.value = d.data
            })
        }
      } else {
        // Draw normal circle for non-focused tree
        group
          .append('circle')
          .attr('cx', d.x)
          .attr('cy', d.y)
          .attr('r', 20)
          .attr('fill', () => {
            const type = d.data.speaker
            switch (type) {
              case 'OG':
                return '#ea5c2d'
              case 'CG':
                return '#ff7f3f'
              case 'CO':
                return '#95cd41'
              case 'OO':
                return '#007f4e'
              default:
                return '#69b3a2'
            }
          })
          .attr('stroke', (d) => {
            if (focusedNodeId.value && d.data.id === focusedNodeId.value) return '#1976d2'
            return '#333'
          })
          .attr('stroke-width', 2)
          .style('cursor', 'pointer')
          .on('click', (event, d) => {
            if (!focusedNodeId.value) {
              focusedNodeId.value = d.data.id
              focusedSubtree.value = getFocusedSubtree(d)
            }
          })

        // Add labels
        group
          .append('text')
          .attr('x', d.x)
          .attr('y', d.y)
          .attr('dy', '0.35em')
          .attr('text-anchor', 'middle')
          .text(d.data.speaker || d.data.id)
          .style('font-size', '12px')
      }
    })
}

function renderMiniTree() {
  if (!miniSvgRef.value) return
  const svg = d3.select(miniSvgRef.value)
  svg.selectAll('*').remove()
  // Always show the entire discussion tree
  const treeDataToRender = props.treeData
  const root = d3.hierarchy(treeDataToRender)
  const treeLayout = d3.tree().size([180, 110])
  treeLayout(root)

  const nodes = root.descendants()
  const minX = d3.min(nodes, (d) => d.x)
  const maxX = d3.max(nodes, (d) => d.x)
  const treeWidth = maxX - minX
  const centerX = 100 - (minX + treeWidth / 2)

  const treeGroup = svg.append('g').attr('transform', `translate(${centerX}, 20)`)

  // Draw links
  treeGroup
    .append('g')
    .selectAll('path')
    .data(root.links())
    .join('path')
    .attr('fill', 'none')
    .attr('stroke', (d) => {
      // Highlight only parent-focused and focused-children links
      if (!focusedNodeId.value) return '#aaa'
      const focusedId = focusedNodeId.value
      // parent -> focused
      if (d.target.data.id === focusedId && d.source.data.id !== focusedId) return 'red'
      // focused -> direct child
      if (d.source.data.id === focusedId && d.target.data.id !== focusedId) return 'red'
      return '#aaa'
    })
    .attr('stroke-width', 2)
    .attr(
      'd',
      d3
        .linkVertical()
        .x((d) => d.x)
        .y((d) => d.y),
    )

  // Draw nodes
  treeGroup
    .append('g')
    .selectAll('circle')
    .data(root.descendants())
    .join('circle')
    .attr('cx', (d) => d.x)
    .attr('cy', (d) => d.y)
    .attr('r', 2)
    .attr('fill', (d) => {
      // Highlight nodes in the focused subtree
      if (focusedNodeId.value && isInFocusedSubtree(d, focusedNodeId.value)) return 'red'
      return '#ccc'
    })
    .attr('stroke', (d) => {
      if (focusedNodeId.value && isInFocusedSubtree(d, focusedNodeId.value)) return 'red'
      return '#333'
    })
    .attr('stroke-width', 2)
}

function getFocusedSubtree(d) {
  // Returns a subtree with only the focused node, its parent, and its direct children
  const cloneNode = (node) => {
    const cloned = { ...node }
    if (cloned.children) {
      // Only keep direct children, remove their children
      cloned.children = cloned.children.map((child) => ({ ...child, children: undefined }))
    }
    return cloned
  }

  if (d.parent) {
    // Clone parent and attach focused node as its only child
    const parentClone = { ...d.parent.data }
    parentClone.children = [cloneNode(d.data)]
    return parentClone
  } else {
    return cloneNode(d.data)
  }
}

function isInFocusedSubtree(d, focusedId) {
  // Returns true if d is in the focused subtree
  if (d.data.id === focusedId) return true
  if (d.parent && d.parent.data.id === focusedId) return true
  if (d.children && d.children.some((c) => c.data.id === focusedId)) return true
  return false
}

function restoreFullTree() {
  focusedNodeId.value = null
  focusedSubtree.value = null
}
</script>

<style scoped>
.argument-node {
  background: white;
  border: 3px solid #dee2e6;
  border-radius: 15px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  z-index: 10;
}
.node-thesis {
  border-color: #28a745;
  background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
}
.node-pro {
  border-color: #007bff;
  background: linear-gradient(135deg, #cce7ff 0%, #b8d9ff 100%);
}
.node-con {
  border-color: #dc3545;
  background: linear-gradient(135deg, #f8d7da 0%, #f1b0b7 100%);
}
.add-to-chat-hint {
  margin-top: 8px;
  padding: 6px 12px;
  background: rgba(0, 123, 255, 0.15);
  border-radius: 15px;
  text-align: center;
  font-size: 12px;
  color: #007bff;
  font-weight: 600;
  border: 1px solid rgba(0, 123, 255, 0.3);
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}
.add-to-chat-hint:hover {
  background: rgba(0, 123, 255, 0.25);
  color: #0056b3;
  border-color: rgba(0, 123, 255, 0.5);
  transform: translateY(-1px);
}
.minitree-box {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 220px;
  height: 170px;
  z-index: 100;
  background: rgba(255, 255, 255, 0.35);
  border: 0.5px solid #e0e0e000;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 10px 0 0 0;
  transition: box-shadow 0.2s;
}
.minitree-svg {
  background: #f8f8ff;
  border: 1.5px solid #bdbdbd;
  border-radius: 10px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.minitree-label {
  text-align: center;
  font-size: 12px;
  color: #222;
  margin-top: 6px;
  font-weight: 500;
  letter-spacing: 0.02em;
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>

<style scoped>
.minitree-box {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 220px;
  height: 170px;
  z-index: 100;
  background: rgba(255, 255, 255, 0.35);
  border: 0.5px solid #e0e0e000;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 10px 0 0 0;
  transition: box-shadow 0.2s;
}
.minitree-svg {
  background: #f8f8ff;
  border: 1.5px solid #bdbdbd;
  border-radius: 10px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.minitree-label {
  text-align: center;
  font-size: 12px;
  color: #222;
  margin-top: 6px;
  font-weight: 500;
  letter-spacing: 0.02em;
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
