# Auto Claude UI

A desktop application for managing AI-driven development tasks using the Auto Claude autonomous coding framework.

## Overview

Auto Claude UI provides a visual Kanban board interface for creating, monitoring, and managing auto-build tasks. It replaces the terminal-based workflow with an intuitive GUI while preserving all CLI functionality.

## Features

- **Project Management**: Add, configure, and switch between multiple projects
- **Kanban Board**: Visual task board with columns for Backlog, In Progress, AI Review, Human Review, and Done
- **Task Creation Wizard**: Form-based interface for creating new tasks
- **Real-Time Progress**: Live updates from implementation_plan.json during agent execution
- **Human Review Workflow**: Review QA results and provide feedback
- **Theme Support**: Light and dark mode with system preference detection
- **Settings**: Per-project and app-wide configuration options

## Tech Stack

- **Framework**: Electron with React 18 (TypeScript)
- **Build Tool**: electron-vite with electron-builder
- **UI Components**: Radix UI primitives (shadcn/ui pattern)
- **Styling**: TailwindCSS with dark mode support
- **State Management**: Zustand
- **File Watching**: chokidar

## Project Structure

```
auto-build-ui/
├── src/
│   ├── main/                 # Electron main process
│   │   ├── index.ts          # App entry point
│   │   ├── agent-manager.ts  # Python subprocess management
│   │   ├── file-watcher.ts   # Implementation plan watching
│   │   ├── ipc-handlers.ts   # IPC message handlers
│   │   └── project-store.ts  # JSON project persistence
│   ├── preload/              # Preload scripts
│   │   └── index.ts          # Secure contextBridge API
│   ├── renderer/             # React application
│   │   ├── components/       # React components
│   │   │   ├── ui/           # Wrapped Radix UI components
│   │   │   ├── Sidebar.tsx
│   │   │   ├── KanbanBoard.tsx
│   │   │   ├── TaskCard.tsx
│   │   │   ├── TaskDetailPanel.tsx
│   │   │   ├── TaskCreationWizard.tsx
│   │   │   ├── ProjectSettings.tsx
│   │   │   └── AppSettings.tsx
│   │   ├── stores/           # Zustand state stores
│   │   ├── hooks/            # Custom React hooks
│   │   ├── styles/           # Global CSS
│   │   └── App.tsx           # Root component
│   └── shared/               # Shared code
│       ├── types.ts          # TypeScript interfaces
│       └── constants.ts      # Constants and IPC channels
├── electron.vite.config.ts   # Build configuration
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── postcss.config.js
```

## Getting Started

### Prerequisites

- Node.js 18+
- npm or pnpm
- Python 3.10+ (for auto-build backend)

### Installation

```bash
# Navigate to auto-build-ui directory
cd auto-build-ui

# Install dependencies
npm install
```

### Development

```bash
# Start development server with hot reload
npm run dev
```

### Build

```bash
# Build for production
npm run build

# Package for macOS
npm run package:mac

# Package for Windows
npm run package:win

# Package for Linux
npm run package:linux
```

### Type Checking

```bash
npm run typecheck
```

### Linting

```bash
npm run lint
```

### Testing

```bash
npm run test
```

## Architecture

### Main Process

The main process handles:
- Window management
- Python subprocess spawning (agent-manager.ts)
- File system watching (file-watcher.ts)
- Project data persistence (project-store.ts)
- IPC communication with renderer

### Preload Script

Provides a secure bridge between main and renderer processes using Electron's contextBridge. All IPC channels are explicitly defined and typed.

### Renderer Process

A React application with:
- Zustand stores for state management
- Custom hooks for IPC event handling
- Radix UI components wrapped in the shadcn/ui pattern
- TailwindCSS for styling

## Security

The application follows Electron security best practices:
- `contextIsolation: true`
- `nodeIntegration: false`
- Minimal API surface via contextBridge
- No direct ipcRenderer exposure

## Environment Variables

- `CLAUDE_CODE_OAUTH_TOKEN`: OAuth token for Claude Code SDK (from auto-build/.env)
- `FALKORDB_URL`: FalkorDB connection URL (optional, defaults to localhost:6379)

## License

MIT
