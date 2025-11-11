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
    <!-- Graph controls (reset view, etc.) -->
    <div class="graph-controls" role="group" aria-label="Graph controls">
      <button class="reset-view" @click="resetView" title="Reset view">Reset view</button>
    </div>
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

// Keep references to the d3 svg selection and the zoom behavior so we can
// programmatically reset the view later.
let svgD3 = null
let zoomBehaviorObj = null

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

function resetView() {
  if (!svgRef.value || !zoomBehaviorObj) return
  const svg = d3.select(svgRef.value)
  // Smoothly transition back to identity (no pan/zoom)
  svg.transition().duration(450).call(zoomBehaviorObj.transform, d3.zoomIdentity)
}

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
  // store selection so other functions can use it
  svgD3 = svg
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

  // Compute nodes per depth BEFORE layout so we can reserve enough horizontal
  // space to avoid overlap. This helps when a layer contains many nodes.
  const preNodes = root.descendants()
  const nodesByDepthCount = {}
  preNodes.forEach((n) => {
    nodesByDepthCount[n.depth] = (nodesByDepthCount[n.depth] || 0) + 1
  })
  const maxNodesInLayer = Math.max(...Object.values(nodesByDepthCount), 1)

  // Minimum spacing between nodes. For focused mode we'll compute a box width
  // that fits content; otherwise use a sensible minimum for circle nodes.
  const nodeMargin = 24
  const minCircleSpacing = 48 // min horizontal distance for circle nodes (r=20 + gap)

  const isFocusedTree = focusedNodeId.value && focusedSubtree.value

  // Compute an initial box width for focused layout (uses available props.width as baseline)
  const minBoxWidth = 180
  let boxWidth = 260
  if (isFocusedTree) {
    // Adaptive width based on available component width; ensure at least minBoxWidth
    boxWidth = Math.max(
      minBoxWidth,
      Math.floor((props.width - nodeMargin * (maxNodesInLayer - 1)) / maxNodesInLayer),
    )
  }

  // Use nodeSize to enforce a minimum horizontal spacing (dx) between nodes so
  // overlaps are prevented regardless of layout size. Choose dx based on
  // focused vs normal mode.
  const dx = isFocusedTree
    ? boxWidth + nodeMargin
    : Math.max(minCircleSpacing, Math.floor(props.width / maxNodesInLayer))
  // dy: vertical spacing between levels. Compute based on available height and max depth.
  const maxDepth = Math.max(...preNodes.map((n) => n.depth), 1)
  const dy = Math.max(80, Math.floor((props.height - verticalPadding * 2) / (maxDepth + 1)))

  const treeLayout = d3.tree().nodeSize([dx, dy])
  treeLayout(root)

  const nodes = root.descendants()
  const minX = d3.min(nodes, (d) => d.x)
  const maxX = d3.max(nodes, (d) => d.x)
  const treeWidth = maxX - minX
  const centerX = props.width / 2 - (minX + treeWidth / 2)

  // Create a zoomable root group so all content can be panned / zoomed
  // and apply the transform on this group. Keep a nested content group
  // to apply initial centering translate so node coordinates stay the same.
  const zoomRoot = svg.append('g').attr('class', 'zoom-root')
  const contentGroup = zoomRoot
    .append('g')
    .attr('transform', `translate(${centerX}, ${verticalPadding})`)

  // Apply d3 zoom behaviour to the svg element. We store the zoom on the svg
  // so wheel/touch/pinch gestures will transform the zoomRoot group.
  const zoomBehavior = d3
    .zoom()
    .scaleExtent([0.2, 4])
    .on('zoom', (event) => {
      zoomRoot.attr('transform', event.transform)
    })
  // keep a reference for external control (reset)
  zoomBehaviorObj = zoomBehavior

  // Prevent browser default (page zoom) when user uses ctrl/cmd + wheel.
  // Also allow touch gestures (pinch) by disabling browser touch-action default.
  svg.style('touch-action', 'none')
  svg.call(zoomBehavior)
  svg.on('wheel', (event) => {
    // In many browsers ctrlKey (or metaKey on mac) indicates intent to zoom the page.
    // We intercept ctrlKey || metaKey to prevent page zoom and instead let d3.zoom handle it.
    if (event.ctrlKey || event.metaKey) {
      event.preventDefault()
      // Let d3.zoom handle the event (it will still be delivered).
    }
  })

  // Draw links inside the content group
  contentGroup
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
  contentGroup
    .append('g')
    .selectAll('g.node')
    .data(root.descendants())
    .join('g')
    .attr('class', 'node')
    .each(function (d) {
      const group = d3.select(this)
      // Recompute boxWidth based on actual treeWidth to keep nodes non-overlapping
      if (isFocusedTree) {
        const maxNodes = Math.max(...Object.values(nodesByDepthCount))
        const adaptive = Math.floor((treeWidth - nodeMargin * (maxNodes - 1)) / maxNodes)
        boxWidth = Math.max(minBoxWidth, adaptive)
      }
      const boxHeight = 110
      if (isFocusedTree) {
        let nodeTypeClass = ''
        let isFocused = focusedNodeId.value === d.data.id
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
            if (isFocused) return 'red' // red border for focused node
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
          .attr('stroke-width', isFocused ? 5 : 3)
          .style('filter', 'drop-shadow(0 4px 15px rgba(0,0,0,0.1))')

        // Header: id (upper left)
        group
          .append('text')
          .attr('x', d.x - boxWidth / 2 + 12)
          .attr('y', d.y - boxHeight / 2 + 22)
          .attr('text-anchor', 'start')
          .attr('font-size', '12px')
          .attr('font-weight', '600')
          .attr('fill', '#6c757d')
          .text(d.data.id || '')

        // Speaker (higher right corner, same style as id)
        group
          .append('text')
          .attr('x', d.x + boxWidth / 2 - 12)
          .attr('y', d.y - boxHeight / 2 + 22)
          .attr('text-anchor', 'end')
          .attr('font-size', '12px')
          .attr('font-weight', '600')
          .attr('fill', '#6c757d')
          .text(d.data.speaker ? d.data.speaker : '')

        // Type (upper right)
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

        // Main text with pixel-based wrapping
        const text = d.data.text || ''
        // Helper to wrap text by pixel width using SVG measurement
        function wrapTextByWidth(
          str,
          maxWidth,
          fontSize = 12,
          fontWeight = 'normal',
          fontFamily = 'sans-serif',
        ) {
          const words = str.split(' ')
          const lines = []
          let line = ''
          // Create a temporary SVG text element for measurement
          const tempText = group
            .append('text')
            .attr('font-size', fontSize + 'px')
            .attr('font-weight', fontWeight)
            .attr('font-family', fontFamily)
            .attr('visibility', 'hidden')
          words.forEach((word) => {
            const testLine = line ? line + ' ' + word : word
            tempText.text(testLine)
            const testWidth = tempText.node().getComputedTextLength()
            if (testWidth > maxWidth && line) {
              lines.push(line)
              line = word
            } else {
              line = testLine
            }
          })
          if (line) lines.push(line)
          tempText.remove()
          return lines
        }
        // Only show 3 lines in the box
        const wrapped = wrapTextByWidth(text, boxWidth - 32)
        let textY = d.y - boxHeight / 2 + 38
        let lastTextY = textY
        // Show up to 2 lines, and if truncated, show 'Expand' as the third line
        let displayLines = wrapped.slice(0, 2)
        let isTruncated = wrapped.length > 3
        // Use SVG tspan for proper wrapping
        const textElem = group
          .append('text')
          .attr('x', d.x)
          .attr('y', textY)
          .attr('text-anchor', 'middle')
          .attr('font-size', '12px')
          .attr('font-weight', 'normal')
          .attr('fill', '#333')
        displayLines.forEach((line, i) => {
          textElem
            .append('tspan')
            .attr('x', d.x)
            .attr('y', textY + i * 15)
            .text(line)
        })
        lastTextY = textY + displayLines.length * 15
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
          textElem.append('tspan').attr('x', d.x).attr('y', lastTextY).text(wrapped[2])
        }

        // Button centered inside box, below text, never overlapping and always inside box
        let buttonY = lastTextY + 18
        if (buttonY > d.y + boxHeight / 2 - 32) {
          buttonY = d.y + boxHeight / 2 - 32
        }
        // Button container for both buttons
        // Make width adaptive to boxWidth, max 220px, min 120px
        const buttonContainerWidth = Math.max(120, Math.min(boxWidth - 12, 220))
        const buttonContainer = group
          .append('foreignObject')
          .attr('x', d.x - buttonContainerWidth / 2)
          .attr('y', buttonY)
          .attr('width', buttonContainerWidth)
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
          .style('width', `${Math.max(80, Math.floor(buttonContainerWidth / 2) - 8)}px`)
          .style('height', '24px')
          .style('border-radius', '12px')
          .style('background', 'rgba(0,123,255,0.15)')
          .style('color', '#007bff')
          .style('border', '1px solid rgba(0,123,255,0.3)')
          .style('font-size', buttonContainerWidth < 160 ? '10px' : '11px')
          .style('font-weight', '600')
          .style('cursor', 'pointer')
          .style('user-select', 'none')
          .style('transition', 'all 0.2s ease')
          .style('white-space', 'normal')
          .style('overflow-wrap', 'break-word')
          .style('word-break', 'break-word')
          .style('text-align', 'center')
          .text(buttonContainerWidth < 120 ? 'Chat' : 'Add to chat')
          .on('click', function (event) {
            event.stopPropagation()
            // normalize payload to the unified AddToChatPayload shape
            const payload = {
              text: d.data && d.data.text ? d.data.text : '',
              nodeId: d.data && d.data.id ? d.data.id : undefined,
              node: d.data,
              source: 'graph',
            }
            emit('addToChat', payload)
          })

        // Show 'Focus this node' for every node except the currently focused one
        if (!focusedNodeId.value || d.data.id !== focusedNodeId.value) {
          // Dynamically reduce font size so text fits in one line
          const focusText = buttonContainerWidth < 120 ? 'Focus' : 'Focus this node'
          let focusFontSize = 11
          // Estimate required font size for the button width
          const minFontSize = 8
          const maxButtonWidth = Math.max(80, Math.floor(buttonContainerWidth / 2) - 8)
          // Create a temp span to measure text width
          const tempSpan = document.createElement('span')
          tempSpan.style.visibility = 'hidden'
          tempSpan.style.position = 'absolute'
          tempSpan.style.fontWeight = '600'
          tempSpan.style.fontFamily = 'inherit'
          tempSpan.style.whiteSpace = 'nowrap'
          tempSpan.innerText = focusText
          document.body.appendChild(tempSpan)
          while (focusFontSize > minFontSize) {
            tempSpan.style.fontSize = focusFontSize + 'px'
            if (tempSpan.offsetWidth <= maxButtonWidth - 16) break
            focusFontSize = focusFontSize - 2
          }
          document.body.removeChild(tempSpan)
          buttonContainer
            .append('xhtml:button')
            .attr('class', 'focus-node-hint')
            .style('width', `${maxButtonWidth}px`)
            .style('height', '24px')
            .style('border-radius', '12px')
            .style('background', 'rgba(40,167,69,0.15)')
            .style('color', '#28a745')
            .style('border', '1px solid rgba(40,167,69,0.3)')
            .style('font-size', focusFontSize + 'px')
            .style('font-weight', '600')
            .style('cursor', 'pointer')
            .style('user-select', 'none')
            .style('transition', 'all 0.2s ease')
            .style('white-space', 'nowrap')
            .style('overflow-wrap', 'break-word')
            .style('word-break', 'break-word')
            .style('text-align', 'center')
            .text(focusText)
            .on('click', function (event) {
              event.stopPropagation()
              focusedNodeId.value = d.data.id
              focusedSubtree.value = getFocusedSubtree(d)
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
  // Always search the full tree for the focused node by id
  function findNodeAndParent(node, id, parent = null) {
    if (node.id === id) return { node, parent }
    if (node.children) {
      for (const child of node.children) {
        const result = findNodeAndParent(child, id, node)
        if (result) return result
      }
    }
    return null
  }

  const result = findNodeAndParent(props.treeData, d.data.id)
  if (!result) return d.data
  const { node: focused, parent } = result

  const cloneNode = (node) => {
    const cloned = { ...node }
    if (cloned.children && cloned.children.length > 0) {
      cloned.children = cloned.children.map((child) => ({ ...child, children: undefined }))
    } else {
      cloned.children = []
    }
    return cloned
  }

  if (parent) {
    const parentClone = { ...parent }
    parentClone.children = [cloneNode(focused)]
    return parentClone
  } else {
    return cloneNode(focused)
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
  left: 20px;
  width: 25%;
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
  font-size: 11px;
  color: #222;
  margin-top: 6px;
  font-weight: 400;
  letter-spacing: 0.02em;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Graph controls overlay (top-right) */
.graph-controls {
  position: absolute;
  top: 12px;
  right: 18px;
  z-index: 160;
  display: flex;
  gap: 8px;
  align-items: center;
}
.graph-controls .reset-view {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(0, 0, 0, 0.08);
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 12px;
  cursor: pointer;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
}
.graph-controls .reset-view:hover {
  transform: translateY(-2px);
}
</style>
