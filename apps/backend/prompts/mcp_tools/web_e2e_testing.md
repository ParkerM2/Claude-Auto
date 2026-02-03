## WEB E2E TESTING GUIDELINES

Comprehensive guide for end-to-end testing of React web applications using browser automation.

### Prerequisites

- Browser automation tool available (Puppeteer MCP or Chrome DevTools MCP)
- Development server running (typically `http://localhost:3000`)
- Test credentials configured (if authentication required)

### Authentication Flow

#### Step 1: Navigate to Login Page

```
Tool: mcp__puppeteer__puppeteer_navigate
Args: {"url": "http://localhost:3000/login"}
```

Navigate to the application's login URL.

#### Step 2: Capture Initial State

```
Tool: mcp__puppeteer__puppeteer_screenshot
Args: {"name": "login-page"}
```

Screenshot before authentication for debugging reference.

#### Step 3: Fill Login Credentials

**Fill username/email field:**
```
Tool: mcp__puppeteer__puppeteer_fill
Args: {"selector": "input[name='email']", "value": "test@example.com"}
```

**Fill password field:**
```
Tool: mcp__puppeteer__puppeteer_fill
Args: {"selector": "input[type='password']", "value": "testpassword123"}
```

#### Step 4: Submit Login Form

```
Tool: mcp__puppeteer__puppeteer_click
Args: {"selector": "button[type='submit']"}
```

#### Step 5: Verify Authentication Success

Wait for navigation and verify logged-in state:

```
Tool: mcp__puppeteer__puppeteer_evaluate
Args: {"script": "window.location.pathname"}
```

Check redirect to dashboard/home page. Then verify authenticated UI:

```
Tool: mcp__puppeteer__puppeteer_evaluate
Args: {"script": "document.querySelector('[data-testid=\"user-menu\"]') !== null"}
```

### React-Specific Testing

#### Testing React Components

**Verify component renders:**
```
Tool: mcp__puppeteer__puppeteer_evaluate
Args: {"script": "document.querySelector('[data-testid=\"my-component\"]') !== null"}
```

**Check React state via DOM:**
```
Tool: mcp__puppeteer__puppeteer_evaluate
Args: {"script": "document.querySelector('.counter-display')?.textContent"}
```

**Interact with React forms:**
```
Tool: mcp__puppeteer__puppeteer_fill
Args: {"selector": "input[placeholder='Search...']", "value": "search term"}
```

#### Handling React Router Navigation

**Test hash routes:**
```
Tool: mcp__puppeteer__puppeteer_evaluate
Args: {"script": "window.location.hash = '#/settings'; true"}
```

**Test path routes:**
```
Tool: mcp__puppeteer__puppeteer_navigate
Args: {"url": "http://localhost:3000/settings"}
```

#### Testing Async Operations

**Wait for loading states:**
```
Tool: mcp__puppeteer__puppeteer_evaluate
Args: {"script": "new Promise(r => setTimeout(() => r(document.querySelector('.loading') === null), 2000))"}
```

**Verify data loaded:**
```
Tool: mcp__puppeteer__puppeteer_evaluate
Args: {"script": "document.querySelectorAll('[data-testid=\"list-item\"]').length > 0"}
```

### Error Handling

#### Capture Console Errors

Set up error capture before testing:
```
Tool: mcp__puppeteer__puppeteer_evaluate
Args: {
  "script": "window.__testErrors = []; window.onerror = (msg, src, line) => { window.__testErrors.push({msg, src, line}); };"
}
```

Check errors after interactions:
```
Tool: mcp__puppeteer__puppeteer_evaluate
Args: {"script": "window.__testErrors"}
```

#### Capture React Error Boundaries

```
Tool: mcp__puppeteer__puppeteer_evaluate
Args: {"script": "document.querySelector('.error-boundary-message')?.textContent || 'No error'"}
```

#### Handle Network Failures

Check for failed API calls:
```
Tool: mcp__puppeteer__puppeteer_evaluate
Args: {
  "script": "document.querySelector('[data-testid=\"error-message\"]')?.textContent || document.querySelector('.error-toast')?.textContent || 'No errors'"
}
```

### Common Testing Patterns

#### Modal Dialog Testing

```
# Open modal
Tool: mcp__puppeteer__puppeteer_click
Args: {"selector": "[data-testid='open-modal-btn']"}

# Verify modal visible
Tool: mcp__puppeteer__puppeteer_evaluate
Args: {"script": "document.querySelector('[role=\"dialog\"]') !== null"}

# Close modal
Tool: mcp__puppeteer__puppeteer_click
Args: {"selector": "[data-testid='close-modal-btn']"}
```

#### Form Validation Testing

```
# Submit empty form to trigger validation
Tool: mcp__puppeteer__puppeteer_click
Args: {"selector": "button[type='submit']"}

# Check validation errors appear
Tool: mcp__puppeteer__puppeteer_evaluate
Args: {"script": "document.querySelectorAll('.form-error, .field-error, [role=\"alert\"]').length"}
```

#### Dropdown/Select Testing

```
Tool: mcp__puppeteer__puppeteer_select
Args: {"selector": "select[name='category']", "value": "option-value"}
```

### Document Findings

```
E2E VERIFICATION:
- Authentication: PASS/FAIL
  - Login form found: YES/NO
  - Credentials accepted: YES/NO
  - Redirected after login: YES/NO
- Component Testing: PASS/FAIL
  - [Component Name]: PASS/FAIL
  - Interactions working: YES/NO
- Console Errors: [list or "None"]
- React Errors: [list or "None"]
- Visual Verification: PASS/FAIL
- Issues: [list or "None"]
```

### Best Practices

1. **Use data-testid attributes** - Most reliable selectors for React apps
2. **Wait for async operations** - React state updates are asynchronous
3. **Screenshot before and after** - Capture state for debugging failures
4. **Test happy path first** - Verify core functionality before edge cases
5. **Check console for errors** - React often logs errors to console
6. **Handle loading states** - Wait for spinners/skeletons to disappear
7. **Test keyboard navigation** - Verify accessibility with Tab/Enter
8. **Verify responsive behavior** - Test at different viewport sizes

### Selector Priority

When targeting React components:
1. `[data-testid="..."]` - Most reliable, explicit test hooks
2. `[role="..."]` - Semantic roles (button, dialog, alert)
3. `input[name="..."]` - Form fields by name attribute
4. `button:has-text("...")` - Buttons by visible text
5. `.className` - CSS classes (less reliable with CSS modules)

### Handling Common Issues

**Login Failure:**
1. Take screenshot of current state
2. Check for error messages in DOM
3. Verify selectors match actual form elements
4. Document as "Manual verification required"

**Element Not Found:**
1. Wait for page to fully load
2. Check if element is inside iframe
3. Verify selector syntax
4. Try alternative selector strategies

**Session Timeout:**
1. Detect timeout via redirect or error message
2. Re-authenticate if credentials available
3. Document and continue or abort gracefully
