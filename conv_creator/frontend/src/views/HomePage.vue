<template>
  <div class="home-page">
    <div class="hero-section">
      <!-- Logo image: place your raster logo at `frontend/public/cover.jpg` or `frontend/public/cover.png` to use it here.
     If you prefer to show only the image (no text title), add the `only-logo` class to the top-level `div.home-page` element. -->
      <img src="/LLMberjack_cover.png" alt="LLMberjack logo" class="hero-logo" />
      <p class="subtitle">
        Create and visualize interactive discussions with argument graphs and chat simulations
      </p>

      <div class="features stacked">
        <router-link to="/files" class="feature-card clickable-card">
          <h3>Files</h3>
          <p>Upload and navigate your discussion files</p>
        </router-link>

        <router-link to="/discussion" class="feature-card clickable-card">
          <h3>Conversation Generator</h3>
          <p>Generate a conversation flow based on your discussion topics</p>
        </router-link>

        <router-link to="/" class="feature-card clickable-card">
          <h3>Conversation Evaluator</h3>
          <p>Evaluate your generated discussion</p>
        </router-link>
      </div>

      <div class="actions">
        <button class="btn btn-secondary" @click="showAbout = true">Learn More</button>
      </div>
    </div>

    <!-- About Modal -->
    <div v-if="showAbout" class="modal-overlay" @click="showAbout = false">
      <div class="modal-content" @click.stop>
        <h2>About Discussion Creator</h2>
        <p>
          This application allows you to create, visualize, and interact with complex discussions
          through two main interfaces:
        </p>
        <ul>
          <li>
            <strong>Graph View:</strong> Visual representation of arguments and their relationships
          </li>
          <li>
            <strong>Chat Interface:</strong> Simulate real-time discussions between participants
          </li>
        </ul>
        <p>
          Use the graph to understand the structure of arguments, and the chat to see how
          conversations might flow in real-time.
        </p>
        <button class="btn btn-primary" @click="showAbout = false">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const showAbout = ref(false)
</script>

<style scoped>
/* Make home look consistent with FilesPage: light, neutral background and compact card/button styles */
.home-page {
  min-height: 100vh;
  /* If a cover image exists use it (SVG first, then JPG); otherwise a soft gradient is used */
  background:
    url('/cover.svg') center/cover no-repeat,
    url('/cover.jpg') center/cover no-repeat,
    linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  color: #2c3e50; /* match files page text color */
  overflow-y: auto;
  box-sizing: border-box;
  position: relative;
}

.home-page::before {
  /* soft white overlay so text and cards remain legible on top of arbitrary covers */
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(245, 247, 250, 0.55);
  pointer-events: none;
}

.hero-section {
  text-align: bottom;
  max-width: 1100px;
  width: 100%;
  position: relative; /* above the overlay */
  z-index: 0;
}

.title {
  font-size: 2.1rem;
  font-weight: 700;
  margin-bottom: 0.6rem;
  color: #2c3e50;
  text-shadow: none;
}

.hero-logo {
  display: block;
  max-width: 640px;
  max-height: 320px;
  width: auto;
  height: auto;
}

/* When showing logo only, hide the textual title */
.home-page.only-logo .title {
  display: none;
}

@media (min-width: 900px) {
  /* Keep hero centered on wide screens as well */
  .hero-section {
    display: block;
    text-align: center;
  }
  .hero-logo {
    margin: 0 auto 0.5rem auto;
  }
}

.subtitle {
  font-size: 1.05rem;
  margin-bottom: 1.5rem;
  color: #495057;
  max-width: 640px;
  margin-left: auto;
  margin-right: auto;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.features.stacked {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  justify-content: center;
  align-items: stretch;
  gap: 1.25rem;
  max-width: 1100px;
  margin: 1.25rem auto 1.5rem auto;
}

.features.stacked .feature-card {
  flex: 0 1 300px; /* allow cards to grow/shrink, prefer 300px each */
  width: 300px;
}

.feature-card {
  background: white;
  border-radius: 12px;
  padding: 1.25rem;
  border: 1px solid #e9ecef;
  box-shadow: 0 6px 16px rgba(33, 37, 41, 0.04);
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
  color: #2c3e50;
  text-align: left;
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 30px rgba(33, 37, 41, 0.06);
}

.clickable-card {
  text-decoration: none;
  color: inherit;
  cursor: pointer;
}

.feature-icon {
  font-size: 1.8rem;
  margin-bottom: 0.6rem;
}

.feature-card h3 {
  font-size: 1.15rem;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.feature-card p {
  color: #556270;
  line-height: 1.5;
}

.actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}

/* Buttons styled to match FilesPage buttons */
/* Buttons are provided globally via theme.css (.btn, .btn-primary, .btn-secondary) */

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  color: #333;
  padding: 1.5rem;
  border-radius: 12px;
  max-width: 520px;
  width: 94%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content h2 {
  margin-bottom: 0.75rem;
  color: #2c3e50;
}

.modal-content ul {
  text-align: left;
  margin: 1rem 0;
}

.modal-content li {
  margin-bottom: 0.5rem;
}

@media (max-width: 768px) {
  .home-page {
    padding: 0.6rem;
    align-items: flex-start;
    padding-top: 1rem;
  }

  .title {
    font-size: 1.9rem;
  }

  .subtitle {
    font-size: 0.98rem;
    margin-bottom: 1rem;
  }

  .features {
    grid-template-columns: 1fr;
    margin-bottom: 1rem;
  }

  .feature-card {
    padding: 1rem;
  }

  .actions {
    flex-direction: column;
    align-items: center;
  }

  .btn {
    width: 100%;
    max-width: 320px;
  }

  /* On small screens, stack the feature cards */
  .features.stacked {
    flex-direction: column;
    max-width: 420px;
    align-items: center;
  }
}
</style>
