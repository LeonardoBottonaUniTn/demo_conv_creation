# Conversation Creator

A Vue.js application for creating and visualizing hierarchical discussion trees with integrated chat functionality. This tool helps facilitate structured debates and discussions by organizing arguments in a tree-like structure with pro/con relationships.

## ✨ Features

- **Discussion Graph Visualization**: Interactive tree and single-branch views of argument structures
- **Real-time Chat Interface**: Telegram-style chat with multiple user personas
- **Argument Tree Management**: Support for thesis, pro, and con argument types
- **Dynamic User Personas**: AI-generated speakers with distinct stances and communication styles
- **Responsive Design**: Optimized for both desktop and mobile viewing
- **Multiple View Modes**: Switch between tree view and focused single-branch view

## 🏗️ Architecture

### Frontend (Vue.js)

- **Framework**: Vue 3 with TypeScript
- **Build Tool**: Vite
- **UI Components**: Custom components for chat and graph visualization
- **State Management**: Vue Composition API with composables

## 📁 Project Structure

```
src/
├── components/
│   ├── chat/                 # Chat interface components
│   │   ├── ChatHeader.vue
│   │   ├── ChatInput.vue
│   │   ├── ChatMessage.vue
│   │   └── ChatMessages.vue
│   ├── graph/                # Graph visualization components
│   │   ├── DiscussionGraph.vue
│   │   ├── controls/
│   │   ├── nodes/
│   │   └── views/
│   └── shared/               # Reusable components
├── composables/              # Vue composables for state management
├── types/                    # TypeScript type definitions
└── backend/                  # Python data processing scripts TODO
```

## 🛠️ Technology Stack

- **Vue 3** - Progressive JavaScript framework
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and dev server
- **Vue Router** - Client-side routing
- **Playwright** - End-to-end testing
- **ESLint + Prettier** - Code formatting and linting

## 🚀 Getting Started

### Prerequisites

Make sure you have the correct Node.js version installed:

```sh
# Using nvm (recommended)
nvm use

# Or check your Node version matches
node --version  # Should be v20.19.0 or higher
```

### Installation

1. **Clone the repository**

   ```sh
   git clone <repository-url>
   cd conv_creator
   ```

2. **Install dependencies**

   ```sh
   npm install
   ```

3. **Start development server**

   ```sh
   npm run dev
   ```

4. **Open your browser**
   Navigate to `http://localhost:5173`

## 📜 Available Scripts

### Development

```sh
npm run dev          # Start development server with hot reload
npm run build        # Build for production
npm run preview      # Preview production build locally
```

### Graph Components

- **DiscussionGraph**: Main graph container with view switching
- **TreeView**: Hierarchical tree visualization
- **SingleBranchView**: Focused view on individual argument branches
- **ArgumentNode/ThesisNode**: Individual argument displays

### Chat Components

- **TelegramChat**: Main chat interface
- **ChatMessages**: Message history display
- **ChatInput**: Message composition
- **ChatHeader**: Chat title and controls

## 🔧 Development Tools

### IDE Setup

- **Recommended**: [VSCode](https://code.visualstudio.com/) + [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar)
- **Disable**: Vetur extension (conflicts with Volar)

### Version Management

The project supports multiple Node.js version managers:

- `.nvmrc` for nvm users
- `.node-version` for nodenv users
- `.tool-versions` for asdf users
