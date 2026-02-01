# Auto Claude Backend

Autonomous coding framework powered by Claude AI. Builds software features through coordinated multi-agent sessions.

## Getting Started

### 1. Install

```bash
cd apps/backend
python -m pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Authenticate with Claude Code (token auto-saved to Keychain):
```bash
claude
# Type: /login
# Press Enter to open browser
```

Token is auto-detected from macOS Keychain / Windows Credential Manager.

### 3. Run

```bash
# List available specs
python run.py --list

# Run a spec
python run.py --spec 001
```

## Requirements

- Python 3.10+
- Claude API token

## Commands

| Command | Description |
|---------|-------------|
| `--list` | List all specs |
| `--spec 001` | Run spec 001 |
| `--spec 001 --isolated` | Run in isolated workspace |
| `--spec 001 --direct` | Run directly in repo |
| `--spec 001 --merge` | Merge completed build |
| `--spec 001 --review` | Review build changes |
| `--spec 001 --discard` | Discard build |
| `--spec 001 --qa` | Run QA validation |
| `--jira-import ISSUE-123` | Import Jira issue as spec |
| `--jira-import ISSUE-123 --spec-name name` | Import with custom spec name |
| `--list-worktrees` | List all worktrees |
| `--help` | Show all options |

## Configuration

Optional `.env` settings:

| Variable | Description |
|----------|-------------|
| `AUTO_BUILD_MODEL` | Override Claude model |
| `DEBUG=true` | Enable debug logging |
| `LINEAR_API_KEY` | Enable Linear integration |
| `JIRA_BASE_URL` | Jira instance URL (Cloud or Server) |
| `JIRA_EMAIL` | Jira email (for API token auth) |
| `JIRA_API_TOKEN` | Jira API token (or use OAuth) |
| `GRAPHITI_ENABLED=true` | Enable memory system |

## Troubleshooting

**"tree-sitter not available"** - Safe to ignore, uses regex fallback.

**Missing module errors** - Run `python -m pip install -r requirements.txt`

**Debug mode** - Set `DEBUG=true DEBUG_LEVEL=2` before running.

---

## For Developers

### Project Structure

```
backend/
├── agents/          # AI agent execution
├── analysis/        # Code analysis
├── cli/             # Command-line interface
├── core/            # Core utilities
├── integrations/    # External services (Linear, Graphiti)
├── runners/         # Service runners (GitHub, GitLab, Jira)
├── merge/           # Git merge handling
├── project/         # Project detection
├── prompts/         # Prompt templates
├── qa/              # QA validation
├── spec/            # Spec management
└── ui/              # Terminal UI
```

### Design Principles

- **SOLID** - Single responsibility, clean interfaces
- **DRY** - Shared utilities in `core/`
- **KISS** - Simple flat imports via facade modules

### Import Convention

```python
# Use facade modules for clean imports
from debug import debug, debug_error
from progress import count_subtasks
from workspace import setup_workspace
```

### Adding Features

1. Create module in appropriate folder
2. Export API in `__init__.py`
3. Add facade module at root if commonly imported

## License

AGPL-3.0
