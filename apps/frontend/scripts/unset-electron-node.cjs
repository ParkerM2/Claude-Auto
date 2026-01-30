#!/usr/bin/env node
/**
 * Wrapper script to run electron with ELECTRON_RUN_AS_NODE unset.
 *
 * When running from VSCode's integrated terminal or Claude Code,
 * ELECTRON_RUN_AS_NODE=1 is inherited, which causes Electron to run as Node.js
 * instead of as Electron. This breaks require('electron') which returns
 * the path to electron.exe instead of the electron module.
 *
 * Usage: node scripts/unset-electron-node.cjs <command> [args...]
 * Example: node scripts/unset-electron-node.cjs electron .
 */

const { spawn } = require('child_process');
const path = require('path');

// Get the command and arguments
const [,, command, ...args] = process.argv;

if (!command) {
  console.error('Usage: node scripts/unset-electron-node.cjs <command> [args...]');
  process.exit(1);
}

// Create environment without ELECTRON_RUN_AS_NODE
const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;

// Resolve the command path
// In npm workspaces, binaries are hoisted to the monorepo root node_modules/.bin
let resolvedCommand = command;
const isWindows = process.platform === 'win32';
const ext = isWindows ? '.cmd' : '';

// Try local node_modules first, then monorepo root (for workspaces)
const localBin = path.join(__dirname, '..', 'node_modules', '.bin', command + ext);
const rootBin = path.join(__dirname, '..', '..', '..', 'node_modules', '.bin', command + ext);

if (command === 'electron' || command === 'electron-vite') {
  const fs = require('fs');
  if (fs.existsSync(localBin)) {
    resolvedCommand = localBin;
  } else if (fs.existsSync(rootBin)) {
    resolvedCommand = rootBin;
  } else {
    console.error(`Could not find ${command} in node_modules/.bin`);
    console.error('Tried:', localBin);
    console.error('Tried:', rootBin);
    process.exit(1);
  }
}

// Spawn the process
// On Windows, .cmd files need shell: true, but we can avoid the deprecation warning
// by passing a single argument string when using shell mode
const spawnOptions = {
  env,
  stdio: 'inherit',
};

let child;
if (isWindows && resolvedCommand.endsWith('.cmd')) {
  // For .cmd files on Windows, use shell mode but combine into single command
  const fullCommand = [resolvedCommand, ...args].map(arg =>
    arg.includes(' ') ? `"${arg}"` : arg
  ).join(' ');
  child = spawn(fullCommand, [], { ...spawnOptions, shell: true });
} else {
  child = spawn(resolvedCommand, args, spawnOptions);
}

child.on('close', (code) => {
  process.exit(code || 0);
});

child.on('error', (err) => {
  console.error('Failed to start process:', err);
  process.exit(1);
});
