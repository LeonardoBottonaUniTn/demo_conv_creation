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
    const containerWidth = graphContainer.value?.clientWidth || 800
    const branchCount = totalBranches

    if (branchCount === 0) return { x: 0, y: 0 }

    const totalContentWidth = branchCount * 220 + (branchCount - 1) * 40
    const startX = (containerWidth - totalContentWidth) / 2 + 110
    const branchSpacing = 260

    const centerX = startX + branchIndex * branchSpacing

    return {
      x: centerX,
      y: 240,
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
