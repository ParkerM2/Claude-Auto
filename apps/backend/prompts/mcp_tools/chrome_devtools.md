## CHROME DEVTOOLS VALIDATION

For web applications with Chrome debugging enabled, use the Chrome DevTools MCP tools for browser automation and validation via Chrome DevTools Protocol (CDP).

**Prerequisites:**
- Chrome/Chromium browser running with `--remote-debugging-port=9222`
- Target web application loaded in browser
- Start Chrome with: `chrome --remote-debugging-port=9222`

### Available Tools

The MCP server provides 20 tools across 4 categories:

#### Navigation Tools (7)

| Tool | Purpose |
|------|---------|
| `mcp__chrome-devtools__navigate_page` | Navigate to URL |
| `mcp__chrome-devtools__new_page` | Open new tab |
| `mcp__chrome-devtools__list_pages` | List open tabs |
| `mcp__chrome-devtools__select_page` | Switch to tab |
| `mcp__chrome-devtools__close_page` | Close tab |
| `mcp__chrome-devtools__navigate_page_history` | Back/forward navigation |
| `mcp__chrome-devtools__wait_for` | Wait for selector/condition |

#### Input Tools (7)

| Tool | Purpose |
|------|---------|
| `mcp__chrome-devtools__click` | Click element |
| `mcp__chrome-devtools__fill` | Fill single input field |
| `mcp__chrome-devtools__fill_form` | Fill multiple form fields |
| `mcp__chrome-devtools__hover` | Hover over element |
| `mcp__chrome-devtools__drag` | Drag element |
| `mcp__chrome-devtools__handle_dialog` | Accept/dismiss dialogs |
| `mcp__chrome-devtools__upload_file` | File upload |

#### Debugging Tools (4)

| Tool | Purpose |
|------|---------|
| `mcp__chrome-devtools__take_screenshot` | Capture screenshot |
| `mcp__chrome-devtools__take_snapshot` | DOM snapshot |
| `mcp__chrome-devtools__evaluate_script` | Execute JavaScript |
| `mcp__chrome-devtools__list_console_messages` | Console logs |

#### Network Tools (2)

| Tool | Purpose |
|------|---------|
| `mcp__chrome-devtools__list_network_requests` | List network requests |
| `mcp__chrome-devtools__get_network_request` | Get request details |

### Validation Flow

#### Step 1: List Available Pages

```
Tool: mcp__chrome-devtools__list_pages
```

List all open tabs to find the target page for testing.

#### Step 2: Navigate to Page

```
Tool: mcp__chrome-devtools__navigate_page
Args: {"url": "http://localhost:3000"}
```

Navigate to the development server URL.

#### Step 3: Wait for Page Load

```
Tool: mcp__chrome-devtools__wait_for
Args: {"selector": "[data-testid=\"app-root\"]", "timeout": 5000}
```

Wait for a specific element to confirm the page has loaded.

#### Step 4: Take Screenshot

```
Tool: mcp__chrome-devtools__take_screenshot
Args: {"name": "page-initial-state"}
```

Capture the initial page state for visual verification.

#### Step 5: Verify Elements Exist

```
Tool: mcp__chrome-devtools__evaluate_script
Args: {"script": "document.querySelector('[data-testid=\"feature\"]') !== null"}
```

Check that expected elements are present on the page.

#### Step 6: Test Interactions

**Click buttons/links:**
```
Tool: mcp__chrome-devtools__click
Args: {"selector": "[data-testid=\"submit-button\"]"}
```

**Fill form fields:**
```
Tool: mcp__chrome-devtools__fill
Args: {"selector": "input[name=\"email\"]", "value": "test@example.com"}
```

**Fill multiple fields at once:**
```
Tool: mcp__chrome-devtools__fill_form
Args: {
  "selector": "form#login",
  "fields": {
    "email": "test@example.com",
    "password": "testpassword123"
  }
}
```

**Hover over elements:**
```
Tool: mcp__chrome-devtools__hover
Args: {"selector": ".dropdown-trigger"}
```

**Handle dialogs (alerts, confirms, prompts):**
```
Tool: mcp__chrome-devtools__handle_dialog
Args: {"action": "accept"}
# Or: {"action": "dismiss"}, {"action": "accept", "promptText": "response"}
```

#### Step 7: Check Console for Errors

```
Tool: mcp__chrome-devtools__list_console_messages
Args: {"level": "error"}
```

Check for JavaScript errors logged to the console.

#### Step 8: Monitor Network Requests

**List recent network requests:**
```
Tool: mcp__chrome-devtools__list_network_requests
Args: {"filter": "api"}
```

**Get details of a specific request:**
```
Tool: mcp__chrome-devtools__get_network_request
Args: {"requestId": "request-123"}
```

### Advanced Usage

#### Tab Management

**Open new tab:**
```
Tool: mcp__chrome-devtools__new_page
Args: {"url": "http://localhost:3000/settings"}
```

**Switch between tabs:**
```
Tool: mcp__chrome-devtools__select_page
Args: {"pageId": "page-abc123"}
```

**Close tab:**
```
Tool: mcp__chrome-devtools__close_page
Args: {"pageId": "page-abc123"}
```

#### Navigation History

```
Tool: mcp__chrome-devtools__navigate_page_history
Args: {"direction": "back"}
# Or: {"direction": "forward"}
```

#### DOM Snapshot

```
Tool: mcp__chrome-devtools__take_snapshot
Args: {"name": "dom-structure"}
```

Capture full DOM structure for inspection.

#### File Upload

```
Tool: mcp__chrome-devtools__upload_file
Args: {"selector": "input[type=\"file\"]", "filePath": "/path/to/file.pdf"}
```

### Document Findings

```
CHROME DEVTOOLS VALIDATION:
- Browser Connection: PASS/FAIL
  - Debug port accessible: YES/NO
  - Connected to correct page: YES/NO
- Page Verification: PASS/FAIL
  - Screenshots captured: [list]
  - Visual elements correct: PASS/FAIL
  - Interactions working: PASS/FAIL
- Console Errors: [list or "None"]
- Network Issues: [list or "None"]
- Issues: [list or "None"]
```

### Common Selectors

When testing UI elements, prefer these selector strategies:
1. `[data-testid="..."]` - Most reliable (if available)
2. `#id` - Element IDs
3. `button:contains("Text")` - By visible text
4. `.class-name` - CSS classes
5. `input[name="..."]` - Form fields by name

### Handling Common Issues

**Browser Not Running with Debug Port:**
If Chrome is not running with remote debugging enabled:
1. Document that Chrome DevTools validation was skipped
2. Note reason: "Browser not running with --remote-debugging-port=9222"
3. Add to QA report as "Manual verification required"
4. Provide instructions: Start Chrome with `chrome --remote-debugging-port=9222`

**Page Not Found:**
If the target page is not found in the list of open tabs:
1. Use `mcp__chrome-devtools__new_page` to open a new tab
2. Navigate to the target URL
3. Proceed with validation

**Element Not Found:**
If selectors fail to find elements:
1. Use `mcp__chrome-devtools__take_snapshot` to inspect DOM
2. Use `mcp__chrome-devtools__evaluate_script` to debug selectors
3. Adjust selectors based on actual DOM structure

**Timeout Errors:**
If wait operations timeout:
1. Increase timeout value
2. Check if page is loading correctly
3. Verify network requests are completing
