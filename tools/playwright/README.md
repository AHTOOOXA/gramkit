# Playwright Server

Simple HTTP server for AI-driven interactive browser testing.

## Usage

### Start Server (Shared Infrastructure)

```bash
# Start shared infrastructure (includes Playwright)
make -f Makefile.shared up

# Or start Playwright service only
docker-compose -f docker-compose.shared.yml up playwright
```

### From Claude Code (AI Assistant)

```bash
# Navigate to page
curl -s -X POST http://localhost:9876/exec \
  -d 'await page.goto("http://localhost:3001/template-react"); return page.url();'

# Click element
curl -s -X POST http://localhost:9876/exec \
  -d 'await page.locator("button.submit").click();'

# Get text content
curl -s -X POST http://localhost:9876/exec \
  -d 'return await page.locator("body").innerText();'

# Take screenshot
curl -s -X POST http://localhost:9876/exec \
  -d 'await page.screenshot({ path: "/tmp/screenshot.png" });'

# Check health
curl http://localhost:9876/health
```

### From Any App (Inside Docker Network)

Apps can connect using `http://shared-playwright:9876`:

```bash
# From any container
curl -X POST http://shared-playwright:9876/exec -d "..."
```

## Endpoints

- `POST /exec` - Execute Playwright command
- `GET /health` - Health check
- `GET /close` - Shutdown server

## Playwright API Reference

The `page` object is available in all commands:

```javascript
// Navigation
await page.goto("https://example.com");
return page.url();

// Selectors
await page.locator("button").click();
await page.locator("input").fill("text");
const text = await page.locator(".result").innerText();

// Wait
await page.waitForTimeout(1000);
await page.waitForSelector(".element");

// Info
return await page.title();
return page.url();

// Screenshots
await page.screenshot({ path: "/path/to/file.png" });
```

See full API: https://playwright.dev/docs/api/class-page

## Security

⚠️ **Only use in trusted environments!**
- Server executes arbitrary JavaScript
- No authentication by default
- Don't expose to public internet

## Troubleshooting

**Service not starting:**
```bash
# Check logs
docker logs shared-playwright

# Check health
curl http://localhost:9876/health
```

**Browser issues:**
```bash
# Restart service
docker-compose -f docker-compose.shared.yml restart playwright
```
