#!/usr/bin/env node
/**
 * MCP E2E Test Orchestrator
 * =========================
 *
 * Orchestrates end-to-end testing of the Electron app using MCP Electron server.
 *
 * Responsibilities:
 * 1. Start Electron app with MCP debugging enabled
 * 2. Wait for CDP connection to be available
 * 3. Execute test scenarios via Claude agent or Playwright
 * 4. Collect console logs from Electron
 * 5. Generate test report
 * 6. Cleanup and exit with appropriate code
 *
 * Usage:
 *   node scripts/run-mcp-tests.js [options]
 *
 * Options:
 *   --scenario <name>  Run specific scenario (smoke, regression, all)
 *   --keep-alive       Keep app running after tests
 *   --verbose          Enable verbose logging
 *   --timeout <ms>     Test timeout in milliseconds (default: 60000)
 *   --port <port>      CDP debug port (default: 9222)
 */

import { spawn } from 'child_process';
import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';
import http from 'http';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
// createRequire available for future dynamic imports if needed
void createRequire;

// Load test environment
const envTestPath = path.join(__dirname, '..', '.env.test');
if (fs.existsSync(envTestPath)) {
  const envContent = fs.readFileSync(envTestPath, 'utf-8');
  for (const line of envContent.split('\n')) {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('#')) {
      const [key, ...valueParts] = trimmed.split('=');
      const value = valueParts.join('=');
      if (key && value !== undefined && !process.env[key]) {
        process.env[key] = value;
      }
    }
  }
}

// Parse CLI arguments
const args = process.argv.slice(2);
const config = {
  scenario: 'smoke',
  keepAlive: false,
  verbose: false,
  timeout: parseInt(process.env.TEST_TIMEOUT, 10) || 60000,
  port: parseInt(process.env.ELECTRON_DEBUG_PORT, 10) || 9222,
};

for (let i = 0; i < args.length; i++) {
  const arg = args[i];
  if (arg === '--scenario' && args[i + 1]) {
    config.scenario = args[++i];
  } else if (arg === '--keep-alive') {
    config.keepAlive = true;
  } else if (arg === '--verbose') {
    config.verbose = true;
  } else if (arg === '--timeout' && args[i + 1]) {
    config.timeout = parseInt(args[++i], 10);
  } else if (arg === '--port' && args[i + 1]) {
    config.port = parseInt(args[++i], 10);
  }
}

function log(message, level = 'info') {
  const timestamp = new Date().toISOString();
  const prefix = {
    info: '\x1b[36m[INFO]\x1b[0m',
    warn: '\x1b[33m[WARN]\x1b[0m',
    error: '\x1b[31m[ERROR]\x1b[0m',
    success: '\x1b[32m[SUCCESS]\x1b[0m',
  }[level] || '[INFO]';

  if (level !== 'info' || config.verbose) {
    console.log(`${timestamp} ${prefix} ${message}`);
  } else {
    console.log(`${prefix} ${message}`);
  }
}

/**
 * Check if CDP is available on the debug port
 */
async function checkCDPConnection(port, timeout = 5000) {
  return new Promise((resolve) => {
    const startTime = Date.now();

    const check = () => {
      const req = http.get(`http://127.0.0.1:${port}/json/version`, (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          try {
            const info = JSON.parse(data);
            resolve({ connected: true, info });
          } catch {
            resolve({ connected: false, error: 'Invalid JSON response' });
          }
        });
      });

      req.on('error', () => {
        if (Date.now() - startTime < timeout) {
          setTimeout(check, 500);
        } else {
          resolve({ connected: false, error: 'Connection timeout' });
        }
      });

      req.setTimeout(1000, () => {
        req.destroy();
        if (Date.now() - startTime < timeout) {
          setTimeout(check, 500);
        } else {
          resolve({ connected: false, error: 'Request timeout' });
        }
      });
    };

    check();
  });
}

/**
 * Wait for CDP connection to be available
 */
async function waitForCDPConnection(port, timeout = 30000) {
  log(`Waiting for CDP connection on port ${port}...`);
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    const result = await checkCDPConnection(port, 2000);
    if (result.connected) {
      log(`CDP connected: ${result.info?.Browser || 'Electron'}`, 'success');
      return result;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  throw new Error(`CDP connection timeout after ${timeout}ms`);
}

/**
 * Start the Electron app with debugging enabled
 */
function startElectronApp(port) {
  return new Promise((resolve, reject) => {
    log('Starting Electron app with MCP debugging...');

    const isWindows = process.platform === 'win32';
    const electronPath = path.join(__dirname, '..', 'node_modules', '.bin', isWindows ? 'electron.cmd' : 'electron');
    const appPath = path.join(__dirname, '..');

    // Build the app first if needed
    const outDir = path.join(appPath, 'out');
    if (!fs.existsSync(outDir)) {
      log('Building Electron app...', 'info');
      const buildResult = spawn('npm', ['run', 'build'], {
        cwd: appPath,
        stdio: 'inherit',
        shell: isWindows,
      });

      buildResult.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`Build failed with code ${code}`));
          return;
        }
        startApp();
      });
    } else {
      startApp();
    }

    function startApp() {
      const electronProcess = spawn(
        electronPath,
        ['.', `--remote-debugging-port=${port}`],
        {
          cwd: appPath,
          stdio: ['ignore', 'pipe', 'pipe'],
          env: {
            ...process.env,
            NODE_ENV: 'test',
            ELECTRON_USER_DATA_PATH: path.join(appPath, '.auto-claude-test'),
            ELECTRON_MCP_ENABLED: 'true',
            ELECTRON_DEBUG_PORT: String(port),
          },
          shell: isWindows,
        }
      );

      // Collect stdout/stderr for debugging
      const logs = [];

      electronProcess.stdout?.on('data', (data) => {
        const line = data.toString().trim();
        if (line) {
          logs.push({ type: 'stdout', message: line, timestamp: Date.now() });
          if (config.verbose) {
            console.log(`[Electron] ${line}`);
          }
        }
      });

      electronProcess.stderr?.on('data', (data) => {
        const line = data.toString().trim();
        if (line) {
          logs.push({ type: 'stderr', message: line, timestamp: Date.now() });
          if (config.verbose) {
            console.error(`[Electron] ${line}`);
          }
        }
      });

      electronProcess.on('error', (err) => {
        reject(new Error(`Failed to start Electron: ${err.message}`));
      });

      electronProcess.on('close', (code) => {
        if (!config.keepAlive) {
          log(`Electron process exited with code ${code}`);
        }
      });

      // Give the app time to initialize
      setTimeout(() => {
        resolve({ process: electronProcess, logs });
      }, 2000);
    }
  });
}

/**
 * Collect console logs via CDP
 */
async function collectLogs(port) {
  return new Promise((resolve) => {
    http.get(`http://127.0.0.1:${port}/json/list`, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const targets = JSON.parse(data);
          resolve(targets);
        } catch {
          resolve([]);
        }
      });
    }).on('error', () => resolve([]));
  });
}

/**
 * Load test scenarios from YAML files
 */
function loadScenarios(scenarioName) {
  const scenariosDir = path.join(__dirname, '..', 'e2e', 'scenarios');

  if (!fs.existsSync(scenariosDir)) {
    log(`Scenarios directory not found: ${scenariosDir}`, 'warn');
    return [];
  }

  const scenarios = [];

  if (scenarioName === 'all') {
    // Load all scenario files
    const files = fs.readdirSync(scenariosDir).filter((f) => f.endsWith('.yaml') || f.endsWith('.yml'));
    for (const file of files) {
      try {
        const content = fs.readFileSync(path.join(scenariosDir, file), 'utf-8');
        scenarios.push({ file, content });
      } catch (err) {
        log(`Failed to load scenario ${file}: ${err.message}`, 'error');
      }
    }
  } else {
    // Load specific scenario
    const file = `${scenarioName}.yaml`;
    const filePath = path.join(scenariosDir, file);
    if (fs.existsSync(filePath)) {
      const content = fs.readFileSync(filePath, 'utf-8');
      scenarios.push({ file, content });
    } else {
      log(`Scenario file not found: ${filePath}`, 'error');
    }
  }

  return scenarios;
}

/**
 * Generate test report
 */
function generateReport(results, outputDir) {
  const reportDir = outputDir || path.join(__dirname, '..', 'e2e', 'reports');

  if (!fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true });
  }

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const reportFile = path.join(reportDir, `mcp-e2e-report-${timestamp}.json`);

  const report = {
    timestamp: new Date().toISOString(),
    config,
    results,
    summary: {
      total: results.length,
      passed: results.filter((r) => r.status === 'passed').length,
      failed: results.filter((r) => r.status === 'failed').length,
      skipped: results.filter((r) => r.status === 'skipped').length,
    },
  };

  fs.writeFileSync(reportFile, JSON.stringify(report, null, 2));
  log(`Report saved to: ${reportFile}`, 'success');

  // Also generate HTML report
  const htmlReport = generateHtmlReport(report);
  const htmlFile = path.join(reportDir, `mcp-e2e-report-${timestamp}.html`);
  fs.writeFileSync(htmlFile, htmlReport);
  log(`HTML report saved to: ${htmlFile}`, 'success');

  return report;
}

/**
 * Generate HTML report
 */
function generateHtmlReport(report) {
  const statusColors = {
    passed: '#22c55e',
    failed: '#ef4444',
    skipped: '#f59e0b',
  };

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MCP E2E Test Report</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
    .container { max-width: 1200px; margin: 0 auto; }
    h1 { color: #333; }
    .summary { display: flex; gap: 20px; margin-bottom: 20px; }
    .summary-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; }
    .summary-card h3 { margin: 0 0 10px 0; color: #666; font-size: 14px; }
    .summary-card .value { font-size: 32px; font-weight: bold; }
    .passed .value { color: ${statusColors.passed}; }
    .failed .value { color: ${statusColors.failed}; }
    .skipped .value { color: ${statusColors.skipped}; }
    .results { background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden; }
    .result-item { padding: 15px 20px; border-bottom: 1px solid #eee; display: flex; align-items: center; gap: 15px; }
    .result-item:last-child { border-bottom: none; }
    .status-badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; color: white; }
    .status-passed { background: ${statusColors.passed}; }
    .status-failed { background: ${statusColors.failed}; }
    .status-skipped { background: ${statusColors.skipped}; }
    .result-name { flex: 1; font-weight: 500; }
    .result-duration { color: #666; font-size: 14px; }
    .meta { color: #999; font-size: 12px; margin-top: 20px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>MCP E2E Test Report</h1>
    <p class="meta">Generated: ${report.timestamp}</p>

    <div class="summary">
      <div class="summary-card">
        <h3>Total Tests</h3>
        <div class="value">${report.summary.total}</div>
      </div>
      <div class="summary-card passed">
        <h3>Passed</h3>
        <div class="value">${report.summary.passed}</div>
      </div>
      <div class="summary-card failed">
        <h3>Failed</h3>
        <div class="value">${report.summary.failed}</div>
      </div>
      <div class="summary-card skipped">
        <h3>Skipped</h3>
        <div class="value">${report.summary.skipped}</div>
      </div>
    </div>

    <div class="results">
      ${report.results
        .map(
          (r) => `
        <div class="result-item">
          <span class="status-badge status-${r.status}">${r.status.toUpperCase()}</span>
          <span class="result-name">${r.name}</span>
          ${r.duration ? `<span class="result-duration">${r.duration}ms</span>` : ''}
        </div>
      `
        )
        .join('')}
    </div>

    <p class="meta">
      Scenario: ${config.scenario} | Port: ${config.port} | Timeout: ${config.timeout}ms
    </p>
  </div>
</body>
</html>`;
}

/**
 * Run basic connectivity test
 */
async function runConnectivityTest(port) {
  const results = [];

  // Test 1: CDP Connection
  log('Running: CDP Connection Test');
  const cdpResult = await checkCDPConnection(port, 5000);
  results.push({
    name: 'CDP Connection',
    status: cdpResult.connected ? 'passed' : 'failed',
    error: cdpResult.error,
    duration: null,
  });

  // Test 2: Get targets
  if (cdpResult.connected) {
    log('Running: Get CDP Targets');
    const targets = await collectLogs(port);
    results.push({
      name: 'Get CDP Targets',
      status: targets.length > 0 ? 'passed' : 'failed',
      error: targets.length === 0 ? 'No targets found' : null,
      details: { targetCount: targets.length },
    });
  }

  return results;
}

/**
 * Main execution
 */
async function main() {
  log('='.repeat(60));
  log('MCP E2E Test Orchestrator');
  log('='.repeat(60));
  log(`Scenario: ${config.scenario}`);
  log(`Port: ${config.port}`);
  log(`Timeout: ${config.timeout}ms`);
  log('');

  let electronApp = null;
  const results = [];

  try {
    // Check if Electron is already running on the port
    const existingConnection = await checkCDPConnection(config.port, 2000);

    if (existingConnection.connected) {
      log('Electron app already running, using existing instance', 'info');
    } else {
      // Start Electron app
      electronApp = await startElectronApp(config.port);
      log('Electron app started');

      // Wait for CDP connection
      await waitForCDPConnection(config.port, config.timeout);
    }

    // Run connectivity tests
    const connectivityResults = await runConnectivityTest(config.port);
    results.push(...connectivityResults);

    // Load and run scenarios
    const scenarios = loadScenarios(config.scenario);
    if (scenarios.length === 0) {
      log('No scenarios loaded, running basic tests only', 'warn');
    } else {
      log(`Loaded ${scenarios.length} scenario file(s)`);
      // Scenarios are loaded but actual execution would be done by Claude agent
      // or the Playwright tests. This orchestrator just ensures the app is ready.
      results.push({
        name: `Scenarios loaded: ${config.scenario}`,
        status: 'passed',
        details: { scenarios: scenarios.map((s) => s.file) },
      });
    }

    // Collect final logs
    const targets = await collectLogs(config.port);
    log(`Final CDP targets: ${targets.length}`);

    // Generate report
    const report = generateReport(results);

    // Summary
    log('');
    log('='.repeat(60));
    log('Test Summary');
    log('='.repeat(60));
    log(`Total: ${report.summary.total}`);
    log(`Passed: ${report.summary.passed}`, report.summary.passed > 0 ? 'success' : 'info');
    log(`Failed: ${report.summary.failed}`, report.summary.failed > 0 ? 'error' : 'info');
    log(`Skipped: ${report.summary.skipped}`, report.summary.skipped > 0 ? 'warn' : 'info');

    // Exit code
    const exitCode = report.summary.failed > 0 ? 1 : 0;

    if (!config.keepAlive && electronApp) {
      log('Cleaning up...');
      electronApp.process.kill();
    } else if (config.keepAlive) {
      log('Keep-alive enabled, app will continue running');
      log(`Press Ctrl+C to stop`);
    }

    process.exit(exitCode);
  } catch (err) {
    log(`Test orchestration failed: ${err.message}`, 'error');
    if (config.verbose && err.stack) {
      console.error(err.stack);
    }

    // Cleanup on error
    if (electronApp && !config.keepAlive) {
      electronApp.process.kill();
    }

    process.exit(1);
  }
}

// Handle cleanup on interrupt
process.on('SIGINT', () => {
  log('\nInterrupted, cleaning up...');
  process.exit(130);
});

process.on('SIGTERM', () => {
  log('\nTerminated, cleaning up...');
  process.exit(143);
});

main();
