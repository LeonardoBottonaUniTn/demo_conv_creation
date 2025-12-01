<template>
  <div class="graph-section">
    <!-- d3-hierarchies graph visualization will be implemented here -->
    <div class="graph-visualization-placeholder">Graph visualization placeholder</div>
  </div>
</template>

<script setup lang="ts">
// Placeholder script for future d3-hierarchies implementation
</script>

<style>
.graph-header {
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 15px;
}

.graph-header h2 {
  margin: 0;
  color: #343a40;
  font-size: 24px;
}

.graph-container {
  background: white;
  border-radius: 8px;
  padding: 30px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  height: calc(100vh - 200px);
  position: relative;
  /* Disable scrolling inside the modular graph container: clip content and
     block scroll gestures. */
  overflow: hidden;
  touch-action: none;
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
@media (max-width: 768px) {
  .graph-section {
    flex: 2;
  }

  .graph-header {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
