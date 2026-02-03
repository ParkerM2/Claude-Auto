# E2E Testing for Web Applications

Auto Claude's QA agents can perform automated end-to-end (E2E) testing of your React web applications. This guide covers how to set up and use browser automation for testing during QA validation.

## Overview

QA agents can interact with your running web application through browser automation, allowing them to:

| Capability | Description |
|------------|-------------|
| **Navigate pages** | Open URLs, click links, navigate history |
| **Fill forms** | Enter text in inputs, select options, submit forms |
| **Click elements** | Buttons, links, custom components |
| **Authenticate** | Log in with test credentials |
| **Take screenshots** | Capture visual state for verification |
| **Check console** | Monitor JavaScript errors and warnings |
| **Inspect DOM** | Verify elements exist and have correct content |

## Prerequisites

Before using E2E testing, ensure you have:

1. **A running development server** - Typically at `http://localhost:3000`
2. **Chrome browser installed** - Required for Chrome DevTools mode
3. **Browser automation enabled** - See Configuration section below

## Browser Automation Modes

Auto Claude supports two browser automation modes for E2E testing:

### Puppeteer MCP (Default)

Puppeteer MCP launches a headless browser automatically. No additional setup required.

**Enable in `.auto-claude/.env` or project settings:**
```bash
PUPPETEER_MCP_ENABLED=true
```

**Best for:**
- CI/CD environments
- Headless testing
- Projects without specific Chrome version requirements

### Chrome DevTools MCP

Chrome DevTools MCP connects to an existing Chrome browser session via Chrome DevTools Protocol (CDP). This allows testing in a real browser with your extensions and settings.

**Enable in `.auto-claude/.env` or project settings:**
```bash
CHROME_DEVTOOLS_MCP_ENABLED=true
```

**Requires Chrome running with remote debugging:**

**Windows:**
```bash
chrome.exe --remote-debugging-port=9222
```

**macOS:**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

**Linux:**
```bash
google-chrome --remote-debugging-port=9222
```

**Best for:**
- Interactive debugging
- Testing with browser extensions
- Inspecting network requests in real-time

## Configuration

### Project-Level Settings

Configure E2E testing per project via the Desktop UI:

1. Open your project in Auto Claude
2. Go to **Project Settings** → **Integrations** → **E2E Testing**
3. Configure:
   - **Browser Mode**: `auto`, `puppeteer`, or `chrome-devtools`
   - **Base URL**: Your development server URL (e.g., `http://localhost:3000`)
   - **Login URL**: Authentication page URL (if applicable)
   - **Credentials**: Test username and password (stored securely)

### Environment Variables

Set browser automation mode in `.auto-claude/.env`:

```bash
# Enable Puppeteer for web frontend testing
PUPPETEER_MCP_ENABLED=true

# OR enable Chrome DevTools for existing browser connection
CHROME_DEVTOOLS_MCP_ENABLED=true

# Chrome DevTools debug port (default: 9222)
CHROME_DEVTOOLS_PORT=9222
```

## Authentication Setup

If your application requires login, configure test credentials so QA agents can authenticate automatically.

### Step 1: Configure Login Settings

In Project Settings → E2E Testing:

| Setting | Description | Example |
|---------|-------------|---------|
| **Login URL** | Page with login form | `/login` or `/auth` |
| **Username** | Test account email/username | `test@example.com` |
| **Password** | Test account password | (stored securely) |

### Step 2: Configure Form Selectors (Optional)

If your login form uses non-standard selectors:

| Setting | Default | Description |
|---------|---------|-------------|
| **Username Selector** | `input[name='email']` | CSS selector for username input |
| **Password Selector** | `input[type='password']` | CSS selector for password input |
| **Submit Selector** | `button[type='submit']` | CSS selector for login button |

### Step 3: Test Authentication

Run QA validation to verify the authentication flow:

```bash
cd apps/backend
python run.py --spec YOUR_SPEC --qa
```

The QA agent will:
1. Navigate to your login URL
2. Fill in credentials
3. Submit the form
4. Verify successful authentication
5. Continue with feature testing

## Running E2E Tests

E2E testing happens automatically during QA validation when browser tools are enabled.

### Start Your Development Server

```bash
# React/Vite
npm run dev

# Create React App
npm start

# Next.js
npm run dev
```

### Run QA Validation

```bash
cd apps/backend

# Run QA on a spec (includes E2E if enabled)
python run.py --spec 001 --qa

# Run full build with QA
python run.py --spec 001
```

### What QA Agents Test

During E2E validation, QA agents will:

1. **Navigate to feature pages** - Open URLs where new features are implemented
2. **Verify UI elements** - Check components render correctly
3. **Test interactions** - Click buttons, fill forms, submit data
4. **Check for errors** - Monitor console for JavaScript errors
5. **Capture screenshots** - Document visual state for review
6. **Verify authentication** - Test login flows if credentials are configured

## Troubleshooting

### "Browser not running with debug port"

**Chrome DevTools mode only.** Start Chrome with remote debugging:

```bash
# Windows
chrome.exe --remote-debugging-port=9222

# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222
```

### "Element not found" errors

The QA agent couldn't find a UI element. Check:

1. **Correct selector** - Verify the CSS selector matches your HTML
2. **Element visibility** - Element might be hidden or behind a modal
3. **Timing** - Element might not be rendered yet (async loading)

**Best practice:** Add `data-testid` attributes to important elements:

```jsx
<button data-testid="submit-button" type="submit">
  Submit
</button>
```

### "Login failed" errors

Authentication didn't work. Verify:

1. **Correct credentials** - Test username/password are valid
2. **Correct URL** - Login URL points to your auth page
3. **Correct selectors** - Form selectors match your login form
4. **Dev server running** - Application is accessible

### "Console errors detected"

The QA agent found JavaScript errors. Check:

1. **Error details** - Review the QA report for specific errors
2. **Network requests** - API calls might be failing
3. **State management** - Check for React state issues

## Best Practices

### 1. Add Test IDs to Elements

Use `data-testid` attributes for reliable element selection:

```jsx
// Good - explicit test hooks
<button data-testid="create-task-btn">Create</button>
<input data-testid="task-title-input" />

// Avoid - brittle selectors
<button className="btn-primary">Create</button>
```

### 2. Use Semantic HTML

QA agents can target elements by role:

```jsx
// Good - semantic roles
<button type="submit">Submit</button>
<nav role="navigation">...</nav>
<dialog role="dialog">...</dialog>

// Avoid - non-semantic
<div onClick={submit}>Submit</div>
```

### 3. Handle Loading States

Ensure loading states are detectable:

```jsx
// Good - testable loading state
{isLoading ? (
  <div data-testid="loading-spinner">Loading...</div>
) : (
  <div data-testid="content">...</div>
)}
```

### 4. Provide Error Messages

Display clear error messages for validation:

```jsx
// Good - visible error messages
{error && (
  <div role="alert" data-testid="form-error">
    {error}
  </div>
)}
```

### 5. Create Test Accounts

Maintain dedicated test accounts for E2E testing:

- Use a consistent test email (e.g., `autotest@yourcompany.com`)
- Set a strong but known password
- Pre-configure test data the account needs

## Related Documentation

- [CLI Usage](CLI-USAGE.md) - Complete CLI reference
- [Main README](../README.md) - Getting started with Auto Claude
- [Backend README](../apps/backend/README.md) - Backend configuration

---

## FAQ

**Q: Can I use E2E testing without a UI?**

Yes! Use the CLI to run QA validation:
```bash
python run.py --spec 001 --qa
```

**Q: What browsers are supported?**

Currently Chrome/Chromium. Puppeteer mode uses Chromium headless, Chrome DevTools mode connects to your installed Chrome.

**Q: How do I debug E2E test failures?**

1. Check the QA report in `.auto-claude/specs/XXX/qa_report.md`
2. Review screenshots captured during testing
3. Check console errors in the report
4. Enable Chrome DevTools mode for interactive debugging

**Q: Can I skip E2E testing?**

Yes, disable browser automation:
```bash
PUPPETEER_MCP_ENABLED=false
CHROME_DEVTOOLS_MCP_ENABLED=false
```

**Q: Does E2E testing work in CI/CD?**

Yes! Use Puppeteer mode (headless) for CI environments:
```bash
PUPPETEER_MCP_ENABLED=true
```
