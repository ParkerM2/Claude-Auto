# Auto Claude - VS Code Extension

Autonomous multi-agent coding framework integration for Visual Studio Code. Build production-quality software through coordinated AI agent sessions directly from your editor.

## Features

- **Create Specs from Selection**: Select code in your editor and create an Auto Claude specification with context
- **Task Progress Sidebar**: View specs, subtasks, and real-time build progress in a dedicated sidebar view
- **Diff View**: Review worktree changes with visual diff comparison before merging
- **QA Reports**: View validation results and acceptance criteria directly in VS Code
- **Command Palette Integration**: Access all Auto Claude features through VS Code commands
- **Worktree Management**: Run, review, merge, or discard builds without leaving your editor

## Requirements

- **VS Code**: Version 1.95.0 or higher
- **Node.js**: Version 24.0.0 or higher
- **Auto Claude Backend**: Python backend must be installed and configured
  - Python 3.12+
  - Auto Claude CLI installed and authenticated

## Installation

### From VS Code Marketplace (Coming Soon)

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "Auto Claude"
4. Click Install

### From VSIX Package

1. Download the `.vsix` file from releases
2. Open VS Code
3. Go to Extensions (Ctrl+Shift+X)
4. Click the "..." menu → "Install from VSIX..."
5. Select the downloaded `.vsix` file

### Backend Setup

Ensure the Auto Claude Python backend is installed and authenticated:

```bash
# Install backend
cd apps/backend
uv venv && uv pip install -r requirements.txt

# Authenticate
python -m claude
# Then type: /login
```

## Usage

### Create a Spec

1. Select code in your editor (optional)
2. Open Command Palette (Ctrl+Shift+P)
3. Run "Auto Claude: Create Spec from Selection"
4. Enter task description
5. Spec will be created with selected code as context

### Run a Build

1. Open Command Palette (Ctrl+Shift+P)
2. Run "Auto Claude: Run Spec"
3. Select a spec from the list
4. Monitor progress in the Auto Claude sidebar

### Review Changes

1. After a build completes, open Command Palette
2. Run "Auto Claude: Review Changes"
3. View git diff of worktree changes in WebView panel

### View QA Report

1. After QA validation completes, open Command Palette
2. Run "Auto Claude: View QA Report"
3. View validation results and acceptance criteria

### Merge or Discard

1. Open Command Palette
2. Run "Auto Claude: Merge Worktree" to accept changes
3. Or "Auto Claude: Discard Changes" to reject

## Commands

| Command | Description | Shortcut |
|---------|-------------|----------|
| `Auto Claude: Create Spec from Selection` | Create spec from selected code or file | - |
| `Auto Claude: Run Spec` | Run an autonomous build | - |
| `Auto Claude: Review Changes` | View worktree diff | - |
| `Auto Claude: View QA Report` | Display QA validation results | - |
| `Auto Claude: Merge Worktree` | Merge completed build into project | - |
| `Auto Claude: Discard Changes` | Discard worktree changes | - |

## Sidebar Views

### Tasks & Specs

The Auto Claude sidebar shows:

- List of all specs in your project
- Nested subtasks with status indicators
  - ⏳ Pending
  - 🔄 In Progress
  - ✅ Completed
- Real-time progress updates during builds

## Configuration

Currently, the extension uses the default Auto Claude backend configuration. Future versions will support VS Code settings for:

- Backend path
- Default complexity level
- Auto-run QA validation
- Merge behavior

## Troubleshooting

### Extension Not Activating

- Ensure VS Code version is 1.95.0 or higher
- Check that Node.js 24+ is installed
- Restart VS Code after installation

### Backend Not Found

- Verify Auto Claude backend is installed: `python -m claude --version`
- Ensure you're authenticated: `python -m claude` → `/login`
- Check that Python 3.12+ is in your PATH

### Commands Not Appearing

- Open Command Palette (Ctrl+Shift+P)
- Type "Auto Claude" to filter commands
- If no commands appear, reload VS Code (Ctrl+R)

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

AGPL-3.0 - See [LICENSE](../../LICENSE) for details.

## Links

- [GitHub Repository](https://github.com/ParkerM2/Claude-Auto)
- [Documentation](../../guides/)
- [Report Issues](https://github.com/ParkerM2/Claude-Auto/issues)

## Release Notes

### 2.7.6

- Initial release of VS Code extension
- Spec creation from selected code
- Task progress sidebar
- Diff view for worktree changes
- QA report display
- Command palette integration
- Worktree management
