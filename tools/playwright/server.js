/**
 * Playwright HTTP Server - Simplified version for Docker
 * Simple HTTP interface for AI-driven browser testing
 */

const { chromium } = require('@playwright/test');
const http = require('http');

let browser, context, page;

async function init() {
  browser = await chromium.launch({
    headless: true,  // Must be true in Docker
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  context = await browser.newContext({
    ignoreHTTPSErrors: true,
    viewport: { width: 1920, height: 1080 }
  });
  page = await context.newPage();
  console.log('✅ Browser ready');
}

async function executeCommand(cmd) {
  try {
    const result = await eval(`(async function() { ${cmd} }).call({ page, context, browser })`);
    return { success: true, result };
  } catch (error) {
    return { success: false, error: error.message, stack: error.stack };
  }
}

const server = http.createServer(async (req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  // Health check
  if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'ok',
      browserOpen: !!browser,
      timestamp: new Date().toISOString()
    }));
    return;
  }

  // Execute command
  if (req.method === 'POST' && req.url === '/exec') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', async () => {
      const result = await executeCommand(body);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(result, null, 2));
    });
    return;
  }

  // Shutdown
  if (req.url === '/close') {
    res.writeHead(200);
    res.end('Shutting down...');
    await cleanup();
    return;
  }

  // Not found
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not found' }));
});

async function cleanup() {
  console.log('🧹 Cleaning up...');
  if (browser) await browser.close();
  process.exit(0);
}

process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);

init().then(() => {
  const PORT = process.env.PORT || 9876;
  server.listen(PORT, () => {
    console.log('🚀 Playwright HTTP Server');
    console.log(`   Listening on: http://localhost:${PORT}`);
    console.log('');
    console.log('📡 Endpoints:');
    console.log('   POST /exec - Execute Playwright command');
    console.log('   GET /health - Health check');
    console.log('   GET /close - Shutdown server');
    console.log('');
    console.log('💡 Usage:');
    console.log('   curl -X POST http://localhost:9876/exec -d "return await page.title();"');
  });
}).catch(console.error);
