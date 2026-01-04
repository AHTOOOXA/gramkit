# Playwright Interactive Testing

**Purpose**: Test frontend features interactively via browser automation

**When to use**: When implementing frontend features and need to verify user interactions work correctly

**Availability**: ✅ Always running at `http://localhost:9876` (part of shared infrastructure)

---

## Quick Reference

**Navigate to page:**
```bash
curl -s -X POST http://localhost:9876/exec \
  -d 'await page.goto("https://local.gramkit.dev/tarot"); return page.url();'
```

**Click element:**
```bash
curl -s -X POST http://localhost:9876/exec \
  -d 'await page.locator("button.submit").click();'
```

**Read page content:**
```bash
curl -s -X POST http://localhost:9876/exec \
  -d 'return await page.locator("body").innerText();'
```

**Fill form:**
```bash
curl -s -X POST http://localhost:9876/exec \
  -d 'await page.locator("input[name=email]").fill("test@example.com");'
```

**Take screenshot (for debugging):**
```bash
curl -s -X POST http://localhost:9876/exec \
  -d 'await page.screenshot({ path: "/tmp/screenshot.png" });'

# Copy from container
docker cp shared-playwright:/tmp/screenshot.png ./screenshot.png
```

---

## Common Testing Patterns

### Test User Flow

```bash
# 1. Navigate
curl -s -X POST http://localhost:9876/exec \
  -d 'await page.goto("https://local.gramkit.dev/tarot/spread");
      return page.url();'

# 2. Read current state
curl -s -X POST http://localhost:9876/exec \
  -d 'return await page.locator("body").innerText();'

# 3. Interact (e.g., click button)
curl -s -X POST http://localhost:9876/exec \
  -d 'await page.locator("text=Daily Card").click();
      await page.waitForTimeout(2000);'

# 4. Verify navigation
curl -s -X POST http://localhost:9876/exec \
  -d 'return { url: page.url(), title: await page.title() };'
```

### Test Form Submission

```bash
# Fill form fields
curl -s -X POST http://localhost:9876/exec \
  -d 'await page.locator("input[name=question]").fill("My question");
      await page.locator("button[type=submit]").click();
      await page.waitForTimeout(2000);'

# Verify result
curl -s -X POST http://localhost:9876/exec \
  -d 'const text = await page.locator(".result").innerText();
      return text;'
```

### Test Authentication

```bash
# Toggle TG Mock
curl -s -X POST http://localhost:9876/exec \
  -d 'await page.locator("text=TG Mock OFF").click();
      await page.waitForTimeout(2000);'

# Verify logged in
curl -s -X POST http://localhost:9876/exec \
  -d 'const text = await page.locator("body").innerText();
      return text.includes("TG Mock ON");'
```

---

## Playwright API Reference

### Selectors

```javascript
page.locator("button")                    // By tag
page.locator(".classname")                // By class
page.locator("#id")                       // By ID
page.locator("text=Login")                // By text
page.locator('[data-testid="submit"]')   // By attribute (preferred)
```

### Actions

```javascript
await locator.click()
await locator.fill("text")
await locator.press("Enter")
await locator.check()  // checkbox
await locator.uncheck()
```

### Reading Content

```javascript
await locator.innerText()       // Visible text
await locator.textContent()     // All text (including hidden)
await locator.getAttribute("href")
await locator.isVisible()
await locator.isEnabled()
```

### Navigation

```javascript
await page.goto(url)
page.url()
await page.reload()
await page.goBack()
```

### Waiting

```javascript
await page.waitForTimeout(ms)                      // Simple delay
await page.waitForSelector(".element")             // Wait for element
await page.waitForLoadState("networkidle")         // Wait for network
await page.waitForSelector(".loading", { state: "hidden" })  // Wait for hidden
```

Full API: https://playwright.dev/docs/api/class-page

---

## Best Practices

**✅ Do:**
- Read page state before asserting
- Use `waitForTimeout()` after dynamic actions (2000ms typical)
- Use specific selectors (data-testid preferred)
- Take screenshots when debugging unexpected behavior

**❌ Don't:**
- Don't use for unit testing (use pytest for backend)
- Don't rely on brittle selectors (nth-child, complex CSS)
- Don't assume page state (always verify first)

---

## Troubleshooting

**Element not found:**
```bash
# Debug: See all page text
curl -s -X POST http://localhost:9876/exec \
  -d 'return await page.locator("body").innerText();'

# Debug: Take screenshot to see page state
curl -s -X POST http://localhost:9876/exec \
  -d 'await page.screenshot({ path: "/tmp/debug.png" });'
```

**Timeout errors:**
```bash
# Add longer wait
curl -s -X POST http://localhost:9876/exec \
  -d 'await page.waitForTimeout(5000);'

# Or increase selector timeout
curl -s -X POST http://localhost:9876/exec \
  -d 'await page.waitForSelector(".element", { timeout: 60000 });'
```

**Server issues:**
```bash
# Check server health
curl http://localhost:9876/health

# Check container
docker ps | grep playwright

# Restart if needed
docker-compose -f docker-compose.shared.yml restart playwright
```

**Session cookie expired (403 on admin pages):**

If tests fail with 403 errors on admin-only pages, the session may have expired from Redis.

```bash
# 1. Check if session exists in Redis
docker exec {app}-redis redis-cli -p 6391 -a password \
  GET "{app}:session:{session_id}"

# 2. If empty, create a new admin session:
# First find an admin user
docker exec {app}-db psql -U postgres -d {app} \
  -c "SELECT id, username, role FROM users WHERE role IN ('admin', 'owner');"

# Then create session (expires in 7 days)
docker exec {app}-redis redis-cli -p 6391 -a password \
  SETEX "{app}:session:test-admin-session" 604800 \
  '{"user_id":"<ADMIN_USER_UUID>"}'
```

**Setting cookies in Playwright:**
```javascript
// Before navigating to admin pages
await page.context().addCookies([{
  name: '{app}_session',  // e.g., 'template_session'
  value: 'test-admin-session',
  domain: 'local.gramkit.dev',
  path: '/'
}]);
await page.goto('https://local.gramkit.dev/{app}/admin');
```

---

## Technical Details

- **Headless mode**: No visible browser (runs in Docker)
- **Viewport**: 1920x1080
- **Browser**: Chromium (Playwright v1.48.0)
- **Container**: `shared-playwright` (always running)
- **Network**: `shared_gateway` (accessible from all apps)
