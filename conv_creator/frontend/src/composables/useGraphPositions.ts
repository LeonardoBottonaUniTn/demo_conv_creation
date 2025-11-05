// Composable for calculating positions and connections
import { type Ref } from 'vue'
import type { Position, NodePosition } from '../types/graph'

export function useGraphPositions(graphContainer: Ref<HTMLElement | undefined>) {
  const getBranchColor = (branchIndex: number): string => {
    const colors = ['#1976D2', '#388E3C', '#D32F2F', '#7B1FA2', '#F57C00']
    return colors[branchIndex % colors.length]
  }

  const getBranchConnectionEnd = (branchIndex: number, totalBranches: number): Position => {
    const container = graphContainer.value
    if (!container) return { x: 400, y: 240 }

    const containerWidth = container.clientWidth
    const containerHeight = container.clientHeight

    // Calculate responsive positioning based on container size
    const minBranchWidth = 160
    const maxBranchWidth = 220
    const padding = 20

    // Determine if we need to use grid layout (when branches don't fit horizontally)
    const totalRequiredWidth = totalBranches * minBranchWidth + (totalBranches - 1) * padding
    const availableWidth = containerWidth - padding * 2

    if (totalRequiredWidth > availableWidth) {
      // Use grid layout - calculate based on grid position
      const branchesPerRow = Math.floor(availableWidth / (minBranchWidth + padding))
      const actualBranchesPerRow = Math.max(1, Math.min(branchesPerRow, totalBranches))

      const row = Math.floor(branchIndex / actualBranchesPerRow)
      const col = branchIndex % actualBranchesPerRow

      const effectiveWidth = Math.min(
        maxBranchWidth,
        availableWidth / actualBranchesPerRow - padding,
      )
      const startX = padding + effectiveWidth / 2
      const rowSpacing = 200

      return {
        x: startX + col * (effectiveWidth + padding),
        y: 240 + row * rowSpacing,
      }
    } else {
      // Use horizontal layout - original behavior but responsive
      const branchWidth = Math.min(maxBranchWidth, availableWidth / totalBranches - padding)
      const totalContentWidth = totalBranches * branchWidth + (totalBranches - 1) * padding
      const startX = (containerWidth - totalContentWidth) / 2 + branchWidth / 2

      return {
        x: startX + branchIndex * (branchWidth + padding),
        y: 240,
      }
    }
  }

  // Node card dimensions (should match ArgumentNode.vue CSS)
  const NODE_WIDTH = 300
  const NODE_HEIGHT = 80
  const VERTICAL_SPACING = 120
  const TOP_OFFSET = 50

  // Helper to get horizontal center of the container
  function getContainerCenterX() {
    const container = graphContainer.value
    if (!container) return window.innerWidth / 2
    const rect = container.getBoundingClientRect()
    return rect.left + container.clientWidth / 2 - rect.left
  }

  const getSingleBranchPosition = (index: number): NodePosition => {
    return {
      position: 'absolute' as const,
      left: `calc(50% - ${NODE_WIDTH / 2}px)`,
      top: `${TOP_OFFSET + index * VERTICAL_SPACING}px`,
    }
  }

  // Connection points: center of each node, using container center
  const getSingleConnectionStart = (index: number): Position => {
    return {
      x: getContainerCenterX(),
      y: TOP_OFFSET + (index - 1) * VERTICAL_SPACING + NODE_HEIGHT / 2,
    }
  }

  const getSingleConnectionEnd = (index: number): Position => {
    return {
      x: getContainerCenterX(),
      y: TOP_OFFSET + index * VERTICAL_SPACING + NODE_HEIGHT / 2,
    }
  }

  return {
    getBranchColor,
    getBranchConnectionEnd,
    getSingleBranchPosition,
    getSingleConnectionStart,
    getSingleConnectionEnd,
  }
}
