# Conversation Creator

A Vue.js application for creating and visualizing hierarchical discussion trees with integrated chat functionality. This tool helps facilitate structured debates and discussions by organizing arguments in a tree-like structure with pro/con relationships.

## ✨ Features

- **Discussion Graph Visualization**: Interactive tree and single-branch views of argument structures
- **Real-time Chat Interface**: Telegram-style chat with multiple user personas
- **Argument Tree Management**: Support for thesis, pro, and con argument types
- **Dynamic User Personas**: AI-generated speakers with distinct stances and communication styles
- **Responsive Design**: Optimized for both desktop and mobile viewing
- **Multiple View Modes**: Switch between tree view and focused single-branch view
- **Conversation Annotation / Labeling**: Annotate conversations with customizable schemas, including message-level and conversation-level fields, progress tracking, and a built-in schema editor
- **Supabase-backed Persistence**: User authentication, file storage, and metadata stored in a managed Postgres database

## 🏗️ Architecture

### Frontend (Vue.js)

- **Framework**: Vue 3 with TypeScript
- **Build Tool**: Vite
- **UI Components**: Custom components for chat and graph visualization
- **State Management**: Vue Composition API with composables

### Backend (FastAPI + Supabase)

- **API**: FastAPI (Python) serving file, folder, user, and LLM routes
- **Database**: **Supabase Postgres** — the `files` table stores file metadata and the `user_settings` table stores per-user API keys, model/provider preferences, and the saved `annotation_schema`
- **Auth**: Supabase authentication; records are scoped per user (`created_by` / `user_id`)
- **Storage**: Supabase Storage for uploaded file contents

#### Database setup

The schema is applied idempotently from a script. Configure `.env` (see `SUPABASE_URL`, Supabase keys, and `DATABASE_IPv4_URL` — the direct Postgres connection string), then run:

```sh
python backend/scripts/setup_db.py
```

This creates/updates the `files` and `user_settings` tables.

### Annotation / Labeling

The annotation page lets you label a selected conversation:

- **Customizable schema**: Define message-level and conversation-level fields via the schema editor; schemas are saved per user in `user_settings.annotation_schema`
- **Progress tracking**: Per-conversation annotation progress and completion status
- **Persistence**: Annotations are stored alongside the conversation data

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
└── views/                    # Page views (Files, Discussion, Annotation, ...)

backend/
├── main.py                   # FastAPI app entrypoint
├── routes/                   # API routes (files, folders, users, llm, upload, ...)
├── database.py               # Supabase Postgres data access (files, settings)
├── supabase_client.py        # Supabase client setup
├── file_storage.py           # Supabase Storage helpers
└── scripts/setup_db.py       # Idempotent database schema setup
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

### Version Management

The project supports multiple Node.js version managers:

- `.nvmrc` for nvm users
- `.node-version` for nodenv users
- `.tool-versions` for asdf users
