#!/usr/bin/env node
/**
 * Electron Log Collector
 * ======================
 *
 * Connects to Electron app via Chrome DevTools Protocol (CDP) and collects console logs.
 *
 * Features:
 * - Connects to Electron via CDP Runtime.consoleAPICalled
 * - Captures console.log, console.error, console.warn, console.info
 * - Filters by severity/category
 * - Outputs to file or stdout
 * - Real-time streaming or batch collection
 *
 * Usage:
 *   node scripts/electron-log-collector.js [options]
 *
 * Options:
 *   --port <port>      CDP debug port (default: 9222)
 *   --output <file>    Output file path (default: stdout)
 *   --filter <level>   Filter by level: all, error, warn, info, log (default: all)
 *   --duration <ms>    Collection duration in ms (default: 10000, 0 = continuous)
 *   --format <type>    Output format: json, text (default: json)
 *   --follow           Follow mode - continuously stream logs
 */

import http from 'http';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);
const WebSocket = require('ws');
import path from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Parse CLI arguments
const args = process.argv.slice(2);
const config = {
  port: parseInt(process.env.ELECTRON_DEBUG_PORT, 10) || 9222,
  output: null,
  filter: 'all',
  duration: 10000,
  format: 'json',
  follow: false,
};

for (let i = 0; i < args.length; i++) {
  const arg = args[i];
  if (arg === '--port' && args[i + 1]) {
    config.port = parseInt(args[++i], 10);
  } else if (arg === '--output' && args[i + 1]) {
    config.output = args[++i];
  } else if (arg === '--filter' && args[i + 1]) {
    config.filter = args[++i];
  } else if (arg === '--duration' && args[i + 1]) {
    config.duration = parseInt(args[++i], 10);
  } else if (arg === '--format' && args[i + 1]) {
    config.format = args[++i];
  } else if (arg === '--follow') {
    config.follow = true;
    config.duration = 0;
  }
}

/**
 * Log levels and their numeric priorities
 */
const LOG_LEVELS = {
  error: 0,
  warn: 1,
  warning: 1,
  info: 2,
  log: 3,
  debug: 4,
  verbose: 5,
};

/**
 * Get CDP targets from the debug port
 */
async function getCDPTargets(port) {
  return new Promise((resolve, reject) => {
    http
      .get(`http://127.0.0.1:${port}/json/list`, (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          try {
            resolve(JSON.parse(data));
          } catch (err) {
            reject(new Error(`Failed to parse CDP targets: ${err.message}`));
          }
        });
      })
      .on('error', (err) => {
        reject(new Error(`Failed to connect to CDP: ${err.message}`));
      });
  });
}

/**
 * Connect to a CDP target via WebSocket
 */
function connectToCDP(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);

    ws.on('open', () => {
      resolve(ws);
    });

    ws.on('error', (err) => {
      reject(new Error(`WebSocket error: ${err.message}`));
    });
  });
}

/**
 * Send CDP command and wait for response
 */
function sendCDPCommand(ws, method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = Math.floor(Math.random() * 1000000);
    const timeout = setTimeout(() => {
      ws.removeListener('message', handler);
      reject(new Error(`CDP command timeout: ${method}`));
    }, 10000);

    const handler = (data) => {
      try {
        const message = JSON.parse(data.toString());
        if (message.id === id) {
          clearTimeout(timeout);
          ws.removeListener('message', handler);
          if (message.error) {
            reject(new Error(`CDP error: ${message.error.message}`));
          } else {
            resolve(message.result);
          }
        }
      } catch {
        // Ignore parse errors for non-response messages
      }
    };

    ws.on('message', handler);
    ws.send(JSON.stringify({ id, method, params }));
  });
}

/**
 * Format a console log entry
 */
function formatLogEntry(entry, format) {
  if (format === 'json') {
    return JSON.stringify(entry);
  }

  const timestamp = new Date(entry.timestamp).toISOString();
  const level = entry.level.toUpperCase().padEnd(5);
  const args = entry.args.map((a) => a.value || a.description || JSON.stringify(a)).join(' ');

  return `${timestamp} [${level}] ${args}`;
}

/**
 * Filter log entry by level
 */
function shouldIncludeLog(entry, filter) {
  if (filter === 'all') return true;

  const entryLevel = LOG_LEVELS[entry.level] ?? LOG_LEVELS.log;
  const filterLevel = LOG_LEVELS[filter] ?? LOG_LEVELS.all;

  return entryLevel <= filterLevel;
}

/**
 * Collect logs from Electron app
 */
async function collectLogs() {
  const collectedLogs = [];
  let outputStream = process.stdout;

  if (config.output) {
    outputStream = fs.createWriteStream(config.output, { flags: 'a' });
  }

  console.error(`Connecting to Electron on port ${config.port}...`);

  // Get available targets
  const targets = await getCDPTargets(config.port);

  if (targets.length === 0) {
    throw new Error('No CDP targets found. Is the Electron app running with --remote-debugging-port?');
  }

  // Find the main page target (prefer 'page' type, exclude DevTools)
  const pageTarget = targets.find((t) =>
    t.type === 'page' &&
    !t.url.startsWith('devtools://') &&
    !t.title.toLowerCase().includes('devtools')
  ) || targets.find((t) => t.type === 'page') || targets[0];
  console.error(`Connecting to target: ${pageTarget.title || pageTarget.url}`);

  // Connect via WebSocket
  const ws = await connectToCDP(pageTarget.webSocketDebuggerUrl);
  console.error('Connected to CDP');

  // Enable Runtime domain for console API
  await sendCDPCommand(ws, 'Runtime.enable');
  console.error('Runtime domain enabled');

  // Set up console API listener
  ws.on('message', (data) => {
    try {
      const message = JSON.parse(data.toString());

      if (message.method === 'Runtime.consoleAPICalled') {
        const { type, args, timestamp, stackTrace } = message.params;

        const entry = {
          timestamp: timestamp || Date.now(),
          level: type,
          args: args.map((arg) => ({
            type: arg.type,
            value: arg.value,
            description: arg.description,
          })),
          stackTrace: stackTrace
            ? {
                callFrames: stackTrace.callFrames.slice(0, 3).map((f) => ({
                  functionName: f.functionName,
                  url: f.url,
                  lineNumber: f.lineNumber,
                })),
              }
            : null,
        };

        if (shouldIncludeLog(entry, config.filter)) {
          collectedLogs.push(entry);

          const formatted = formatLogEntry(entry, config.format);
          outputStream.write(formatted + '\n');
        }
      }

      if (message.method === 'Runtime.exceptionThrown') {
        const { exceptionDetails } = message.params;

        const entry = {
          timestamp: Date.now(),
          level: 'error',
          args: [
            {
              type: 'exception',
              value: exceptionDetails.text,
              description: exceptionDetails.exception?.description,
            },
          ],
          stackTrace: exceptionDetails.stackTrace
            ? {
                callFrames: exceptionDetails.stackTrace.callFrames.slice(0, 5),
              }
            : null,
        };

        if (shouldIncludeLog(entry, config.filter)) {
          collectedLogs.push(entry);

          const formatted = formatLogEntry(entry, config.format);
          outputStream.write(formatted + '\n');
        }
      }
    } catch {
      // Ignore parse errors for non-console messages
    }
  });

  console.error(`Collecting logs${config.duration > 0 ? ` for ${config.duration}ms` : ' (continuous)'}...`);
  console.error(`Filter: ${config.filter}, Format: ${config.format}`);
  console.error('---');

  // Collect for duration or continuously
  if (config.duration > 0) {
    await new Promise((resolve) => setTimeout(resolve, config.duration));

    // Close connections
    ws.close();
    if (config.output) {
      outputStream.end();
    }

    console.error('---');
    console.error(`Collection complete. Captured ${collectedLogs.length} log entries.`);

    return collectedLogs;
  } else {
    // Continuous mode - wait for interrupt
    console.error('Press Ctrl+C to stop collection');

    process.on('SIGINT', () => {
      console.error('\n---');
      console.error(`Collection stopped. Captured ${collectedLogs.length} log entries.`);
      ws.close();
      if (config.output) {
        outputStream.end();
      }
      process.exit(0);
    });

    // Keep process alive - intentionally never resolves
    await new Promise(() => { /* intentional: keep process alive */ });
  }
}

/**
 * Get logs as a summary (for integration with test runner)
 */
async function getLogSummary() {
  const targets = await getCDPTargets(config.port);

  if (targets.length === 0) {
    return { error: 'No CDP targets found', logs: [], summary: {} };
  }

  // Find the main page target (prefer 'page' type, exclude DevTools)
  const pageTarget = targets.find((t) =>
    t.type === 'page' &&
    !t.url.startsWith('devtools://') &&
    !t.title.toLowerCase().includes('devtools')
  ) || targets.find((t) => t.type === 'page') || targets[0];
  const ws = await connectToCDP(pageTarget.webSocketDebuggerUrl);

  await sendCDPCommand(ws, 'Runtime.enable');

  // Collect logs for a short period
  const logs = [];
  const collectDuration = 2000;

  ws.on('message', (data) => {
    try {
      const message = JSON.parse(data.toString());
      if (message.method === 'Runtime.consoleAPICalled') {
        logs.push({
          level: message.params.type,
          message: message.params.args.map((a) => a.value || a.description).join(' '),
          timestamp: message.params.timestamp || Date.now(),
        });
      }
    } catch {
      // Ignore
    }
  });

  await new Promise((resolve) => setTimeout(resolve, collectDuration));
  ws.close();

  // Generate summary
  const summary = {
    total: logs.length,
    errors: logs.filter((l) => l.level === 'error').length,
    warnings: logs.filter((l) => l.level === 'warning' || l.level === 'warn').length,
    info: logs.filter((l) => l.level === 'info' || l.level === 'log').length,
  };

  return { logs, summary };
}

// Main execution
async function main() {
  try {
    await collectLogs();
  } catch (err) {
    console.error(`Error: ${err.message}`);
    process.exit(1);
  }
}

// Export for programmatic use
export { collectLogs, getLogSummary, getCDPTargets, connectToCDP, sendCDPCommand };

// Run if executed directly
main();
