<template>
  <div class="home-page">
    <div class="hero-section">
      <h1 class="title">Title we want</h1>
      <p class="subtitle">
        Create and visualize interactive discussions with argument graphs and chat simulations
      </p>

      <div class="features">
        <router-link to="/files" class="feature-card clickable-card">
          <h3>Files</h3>
          <p>Upload and navigate your discussion files</p>
        </router-link>

        <router-link to="/discussion" class="feature-card clickable-card">
          <h3>Conversation Generator</h3>
          <p>Generate a conversation flow based on your discussion topics</p>
        </router-link>

        <div class="feature-card">
          <h3>Conversation Evaluator</h3>
          <p>Evaluate your generated discussion</p>
        </div>
      </div>

      <div class="actions">
        <button class="secondary-button" @click="showAbout = true">Learn More</button>
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
        <button class="primary-button" @click="showAbout = false">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const showAbout = ref(false)
</script>

<style scoped>
.home-page {
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  color: white;
  overflow-y: auto;
  box-sizing: border-box;
}

.hero-section {
  text-align: center;
  max-width: 1200px;
  width: 100%;
  padding: 0.5rem 0;
  max-height: 100%;
  overflow-y: auto;
}

.title {
  font-size: 2.8rem;
  font-weight: 700;
  margin-bottom: 0.8rem;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
}

.subtitle {
  font-size: 1.1rem;
  margin-bottom: 2rem;
  opacity: 0.9;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.feature-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition:
    transform 0.3s ease,
    box-shadow 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}

.clickable-card {
  text-decoration: none;
  color: inherit;
  cursor: pointer;
  border: 2px solid rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.15);
}

.clickable-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 15px 40px rgba(0, 0, 0, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.25);
}

.feature-icon {
  font-size: 2.5rem;
  margin-bottom: 0.8rem;
}

.feature-card h3 {
  font-size: 1.3rem;
  margin-bottom: 0.8rem;
  font-weight: 600;
}

.feature-card p {
  opacity: 0.9;
  line-height: 1.6;
}

.actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}

.primary-button {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 2px solid rgba(255, 255, 255, 0.3);
  padding: 1rem 2rem;
  border-radius: 50px;
  font-size: 1.1rem;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.primary-button:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-2px);
}

.secondary-button {
  background: transparent;
  color: white;
  border: 2px solid rgba(255, 255, 255, 0.5);
  padding: 1rem 2rem;
  border-radius: 50px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.secondary-button:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-2px);
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  color: #333;
  padding: 2rem;
  border-radius: 16px;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content h2 {
  margin-bottom: 1rem;
  color: #333;
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
    padding: 0.5rem;
    align-items: flex-start;
    padding-top: 1rem;
  }

  .title {
    font-size: 2.2rem;
  }

  .subtitle {
    font-size: 1rem;
    margin-bottom: 1.5rem;
  }

  .features {
    grid-template-columns: 1fr;
    margin-bottom: 1.5rem;
    gap: 1rem;
  }

  .feature-card {
    padding: 1rem;
  }

  .feature-icon {
    font-size: 2rem;
    margin-bottom: 0.5rem;
  }

  .feature-card h3 {
    font-size: 1.2rem;
    margin-bottom: 0.5rem;
  }

  .actions {
    flex-direction: column;
    align-items: center;
    gap: 0.8rem;
  }

  .primary-button,
  .secondary-button {
    width: 100%;
    max-width: 300px;
    padding: 0.8rem 1.5rem;
    font-size: 1rem;
  }
}
</style>
