# Jira Integration Guide

Auto Claude integrates with Jira to streamline your development workflow. Import Jira issues as specs, track progress automatically, and link pull requests—all without manual ticket updates.

## Features

| Feature | Description |
|---------|-------------|
| **Import Issues as Specs** | Convert Jira tickets into Auto Claude specs with one command |
| **Auto Status Updates** | Ticket status updates automatically during build lifecycle |
| **PR Linking** | Completed PRs are automatically linked to Jira issues |
| **Dual Auth Support** | Use API tokens (simple) or OAuth 2.0 (more secure) |
| **Cloud & Server** | Works with both Jira Cloud and Jira Server |

## Quick Start

**Step 1:** Configure Jira credentials in `apps/backend/.env`

**Step 2:** Import a Jira issue as a spec

**Step 3:** Build the spec - Jira updates automatically

---

## Authentication Setup

Choose one of two authentication methods:

### Option 1: API Token (Simpler)

Best for personal use and small teams.

**Step 1:** Generate an API token

1. Go to [Atlassian Account Security](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token**
3. Give it a label (e.g., "Auto Claude")
4. Copy the token

**Step 2:** Configure `.env`

Add to `apps/backend/.env`:

```bash
# Jira Cloud
JIRA_BASE_URL=https://your-company.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=your-api-token-here

# Optional: Default project key
JIRA_PROJECT_KEY=PROJ
```

For Jira Server, use your server URL:

```bash
JIRA_BASE_URL=https://jira.your-company.com
```

### Option 2: OAuth 2.0 (More Secure)

Best for teams and production environments.

**Step 1:** Create an OAuth 2.0 app in Jira

**For Jira Cloud:**

1. Go to [Atlassian Developer Console](https://developer.atlassian.com/console/myapps/)
2. Click **Create** → **OAuth 2.0 integration**
3. Set **App name** (e.g., "Auto Claude")
4. Under **Permissions**, add:
   - `read:jira-work`
   - `write:jira-work`
5. Under **Authorization**, set **Callback URL**:
   ```
   http://localhost:8080/callback
   ```
6. Click **Save**
7. Copy **Client ID** and **Client Secret**

**For Jira Server:**

1. Go to **Application Links** in Jira Admin
2. Create a new **Application Link**
3. Configure OAuth settings
4. Copy **Consumer Key** and **Consumer Secret**

**Step 2:** Configure `.env`

Add to `apps/backend/.env`:

```bash
JIRA_BASE_URL=https://your-company.atlassian.net
JIRA_OAUTH_CLIENT_ID=your-client-id
JIRA_OAUTH_CLIENT_SECRET=your-client-secret
```

**Step 3:** Authenticate

Run the OAuth flow (first time only):

```bash
cd apps/backend
python -c "from runners.jira.oauth import JiraOAuthClient; import asyncio; asyncio.run(JiraOAuthClient().authorize())"
```

This will:
1. Open your browser for Jira login
2. Request permission to access your Jira account
3. Save the OAuth token securely

---

## Usage

### Importing a Jira Issue as a Spec

**CLI:**

```bash
cd apps/backend

# Import by issue key
python run.py --jira-import PROJ-123

# Import with custom spec name
python run.py --jira-import PROJ-123 --spec-name feature-login

# Import from specific project
JIRA_PROJECT_KEY=PROJ python run.py --jira-import PROJ-123
```

**Desktop UI:**

1. Open the **Jira Tickets** view
2. Select a ticket
3. Click **Create Spec**
4. The spec is created automatically with:
   - Title from Jira summary
   - Description from Jira description
   - Acceptance criteria from Jira acceptance criteria (if present)

**What Gets Created:**

When you import a Jira issue, Auto Claude creates:

```
.auto-claude/specs/001-proj-123/
├── spec.md                  # Feature specification
├── requirements.json        # Structured requirements
├── jira_issue.json         # Jira metadata (issue key, URL)
└── context.json            # Codebase context (created later)
```

### Building a Jira-Linked Spec

Build the spec like any other:

```bash
cd apps/backend
python run.py --spec 001-proj-123
```

**Automatic Jira Updates:**

| Build Event | Jira Status Update |
|-------------|-------------------|
| **Build started** | `To Do` → `In Progress` |
| **Build completed** | `In Progress` → `Done` |
| **Build failed/stuck** | `In Progress` → `To Do` |

Status names are mapped automatically. If your Jira workflow uses different status names, the integration will find the closest match.

### Creating a PR with Auto-Linking

When you create a pull request, it's automatically linked to the Jira issue:

```bash
cd apps/backend
python run.py --spec 001-proj-123 --merge
```

Or use the Desktop UI to create the PR.

**What Gets Linked:**

The PR URL is added to the Jira issue as a **Remote Link**, visible in:
- Jira issue **Development** panel
- Jira issue **Links** section

---

## Configuration Reference

All Jira environment variables (from `apps/backend/.env`):

| Variable | Required | Description |
|----------|----------|-------------|
| `JIRA_BASE_URL` | Yes | Jira instance URL (Cloud or Server) |
| `JIRA_EMAIL` | Yes* | Email for API token auth |
| `JIRA_API_TOKEN` | Yes* | API token (from Atlassian account) |
| `JIRA_OAUTH_CLIENT_ID` | Yes** | OAuth client ID (from OAuth app) |
| `JIRA_OAUTH_CLIENT_SECRET` | Yes** | OAuth client secret (from OAuth app) |
| `JIRA_PROJECT_KEY` | No | Default project key for filtering |

\* Required for API token authentication
\** Required for OAuth 2.0 authentication

**Validation:**

Auto Claude validates that you provide **exactly one** authentication method:

- ✅ `JIRA_EMAIL` + `JIRA_API_TOKEN`
- ✅ `JIRA_OAUTH_CLIENT_ID` + `JIRA_OAUTH_CLIENT_SECRET`
- ❌ Both API token **and** OAuth credentials (will error)
- ❌ Neither authentication method (will error)

---

## Status Mapping

Auto Claude maps build events to Jira status transitions:

| Auto Claude Event | Target Jira Status |
|-------------------|-------------------|
| Task started | `In Progress` |
| Build complete | `Done` |
| Task failed/stuck | `To Do` |

**How It Works:**

1. Auto Claude fetches available transitions for the issue
2. Finds a transition matching the target status (case-insensitive)
3. Executes the transition

**Custom Workflows:**

If your Jira workflow uses different status names (e.g., "Doing" instead of "In Progress"), the integration will attempt to find the best match. If no match is found, a warning is logged but the build continues.

---

## Troubleshooting

### "Authentication failed: Invalid credentials"

**API Token:**
- Verify `JIRA_EMAIL` matches your Atlassian account email
- Regenerate the API token if it's expired
- Ensure `JIRA_BASE_URL` is correct (no trailing slash)

**OAuth:**
- Re-run the OAuth flow: `python -c "from runners.jira.oauth import JiraOAuthClient; import asyncio; asyncio.run(JiraOAuthClient().authorize())"`
- Verify `JIRA_OAUTH_CLIENT_ID` and `JIRA_OAUTH_CLIENT_SECRET` are correct
- Check OAuth app permissions include `read:jira-work` and `write:jira-work`

### "Issue not found: PROJ-123"

- Verify the issue key is correct (case-sensitive)
- Ensure you have permission to view the issue
- Check `JIRA_BASE_URL` points to the correct Jira instance

### "Transition not available: In Progress"

Your Jira workflow may not allow this transition from the current status. This is a warning, not an error - the build will continue.

**To fix:**
1. Check the issue's current status in Jira
2. Verify the workflow allows the transition (e.g., `To Do` → `In Progress`)
3. Adjust your Jira workflow if needed

### "Multiple authentication methods provided"

You have both API token **and** OAuth credentials in `.env`. Remove one:

```bash
# Use API token - comment out OAuth
# JIRA_OAUTH_CLIENT_ID=...
# JIRA_OAUTH_CLIENT_SECRET=...

# OR use OAuth - comment out API token
# JIRA_EMAIL=...
# JIRA_API_TOKEN=...
```

### Debug Logging

Enable debug mode to see detailed Jira API calls:

```bash
# In apps/backend/.env
DEBUG=true
DEBUG_LEVEL=2
```

Then run your command and check the logs:

```bash
python run.py --jira-import PROJ-123
```

---

## Examples

### Example 1: Import and Build a Feature

```bash
cd apps/backend

# Import Jira issue PROJ-456 as spec
python run.py --jira-import PROJ-456

# Run the build (Jira status → "In Progress")
python run.py --spec 001-proj-456

# Create PR (automatically linked to PROJ-456)
python run.py --spec 001-proj-456 --merge
```

**Jira Updates:**
1. Status: `To Do` → `In Progress` (when build starts)
2. PR link added to issue (when PR created)
3. Status: `In Progress` → `Done` (when build completes)

### Example 2: Import Multiple Issues

```bash
cd apps/backend

# Import from different projects
python run.py --jira-import BACKEND-123
python run.py --jira-import FRONTEND-456
python run.py --jira-import INFRA-789

# List all specs (including Jira-linked ones)
python run.py --list
```

### Example 3: Using OAuth with Custom Project

```bash
# In apps/backend/.env
JIRA_BASE_URL=https://mycompany.atlassian.net
JIRA_OAUTH_CLIENT_ID=my-client-id
JIRA_OAUTH_CLIENT_SECRET=my-client-secret
JIRA_PROJECT_KEY=DEV

# First-time OAuth setup
cd apps/backend
python -c "from runners.jira.oauth import JiraOAuthClient; import asyncio; asyncio.run(JiraOAuthClient().authorize())"

# Import issue from DEV project
python run.py --jira-import DEV-42
```

---

## Security Best Practices

1. **Never commit `.env` to git** - It contains sensitive credentials
2. **Use OAuth for production** - More secure than API tokens
3. **Rotate API tokens regularly** - Regenerate every 90 days
4. **Use project-specific tokens** - Create separate tokens per project
5. **Review OAuth app permissions** - Only grant necessary scopes

---

## API Reference

For advanced usage, you can use the Jira integration programmatically:

```python
from runners.jira.jira_client import JiraClient, JiraConfig
from runners.jira.spec_importer import JiraSpecImporter

# Initialize client (API token auth)
config = JiraConfig(
    base_url="https://mycompany.atlassian.net",
    email="you@company.com",
    api_token="your-api-token"
)
client = JiraClient(config)

# Import issue as spec
importer = JiraSpecImporter(client)
spec = await importer.import_issue("PROJ-123", spec_dir="specs/001-proj-123")

# Update issue status
from runners.jira.status_updater import JiraStatusUpdater
updater = JiraStatusUpdater(client)
await updater.update_status("PROJ-123", "In Progress")

# Link PR to issue
from runners.jira.pr_linker import JiraPRLinker
linker = JiraPRLinker(client)
await linker.link_pr("PROJ-123", "https://github.com/user/repo/pull/42")
```

---

## FAQ

**Q: Can I use Jira Server instead of Jira Cloud?**

Yes! Set `JIRA_BASE_URL` to your Jira Server URL:

```bash
JIRA_BASE_URL=https://jira.mycompany.com
```

**Q: What happens if I delete the Jira issue?**

The spec continues to work normally. Status updates and PR linking will fail silently (logged as warnings).

**Q: Can I manually edit the spec after import?**

Yes! The spec is a standard Auto Claude spec. Edit `spec.md` as needed.

**Q: Does this work with Jira Data Center?**

Yes! Jira Data Center uses the same API as Jira Server.

**Q: Can I disable auto status updates?**

Currently, no. If Jira integration is enabled, status updates are automatic. To disable, remove Jira credentials from `.env`.

**Q: How do I re-authenticate with OAuth?**

Re-run the OAuth flow:

```bash
python -c "from runners.jira.oauth import JiraOAuthClient; import asyncio; asyncio.run(JiraOAuthClient().authorize())"
```

---

## Contributing

Found a bug or want to improve the Jira integration? See [CONTRIBUTING.md](../CONTRIBUTING.md) for development setup and guidelines.

---

## Related Documentation

- [CLI Usage](CLI-USAGE.md) - Complete CLI reference
- [Main README](../README.md) - Getting started
- [Backend README](../apps/backend/README.md) - Backend configuration
