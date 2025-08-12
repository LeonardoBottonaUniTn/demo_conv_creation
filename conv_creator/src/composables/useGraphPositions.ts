// Composable for calculating positions and connections
import { type Ref } from 'vue'
import type { Position, NodePosition } from '../types/graph'

export function useGraphPositions(graphContainer: Ref<HTMLElement | undefined>) {
  const getBranchColor = (branchIndex: number): string => {
    const colors = ['#1976D2', '#388E3C', '#D32F2F', '#7B1FA2', '#F57C00']
    return colors[branchIndex % colors.length]
  }

  const getThesisConnectionStart = (): Position => {
    return {
      x: graphContainer.value?.clientWidth ? graphContainer.value.clientWidth / 2 : 400,
      y: 140, // Bottom of thesis node
    }
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

  const getSingleBranchPosition = (index: number): NodePosition => {
    return {
      position: 'absolute' as const,
      left: '50px',
      top: `${index * 120 + 50}px`,
    }
  }

  const getSingleConnectionStart = (index: number): Position => {
    return {
      x: 175,
      y: index * 120 + 25,
    }
  }

  const getSingleConnectionEnd = (index: number): Position => {
    return {
      x: 175,
      y: (index + 1) * 120 + 100,
    }
  }

  return {
    getBranchColor,
    getThesisConnectionStart,
    getBranchConnectionEnd,
    getSingleBranchPosition,
    getSingleConnectionStart,
    getSingleConnectionEnd,
  }
}
