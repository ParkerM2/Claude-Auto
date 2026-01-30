/**
 * Rebuilds the Electron app and reinstalls it.
 * The desktop shortcut will then launch the updated version.
 *
 * Usage: node scripts/rebuild-and-install.cjs [--silent]
 *   --silent: Install without showing the installer UI
 */

const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const isWindows = process.platform === 'win32';
const isMac = process.platform === 'darwin';
const isLinux = process.platform === 'linux';

const silent = process.argv.includes('--silent') || process.argv.includes('-s');
const frontendDir = path.resolve(__dirname, '..');
const distDir = path.join(frontendDir, 'dist');

function getPackageVersion() {
  const pkgPath = path.join(frontendDir, 'package.json');
  const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'));
  return pkg.version;
}

function findInstaller(version) {
  if (isWindows) {
    // Try different naming patterns
    const patterns = [
      `Auto-Claude-${version}-win32-x64.exe`,
      `Auto-Claude-${version}-win-x64.exe`,
      `Auto-Claude Setup ${version}.exe`,
    ];
    for (const pattern of patterns) {
      const installerPath = path.join(distDir, pattern);
      if (fs.existsSync(installerPath)) {
        return installerPath;
      }
    }
    // Fallback: find any .exe that's not an uninstaller
    const files = fs.readdirSync(distDir);
    const exe = files.find(f => f.endsWith('.exe') && !f.includes('uninstaller'));
    if (exe) {
      return path.join(distDir, exe);
    }
  } else if (isMac) {
    const patterns = [
      `Auto-Claude-${version}-mac-arm64.dmg`,
      `Auto-Claude-${version}-mac-x64.dmg`,
      `Auto-Claude-${version}.dmg`,
    ];
    for (const pattern of patterns) {
      const dmgPath = path.join(distDir, pattern);
      if (fs.existsSync(dmgPath)) {
        return dmgPath;
      }
    }
  } else if (isLinux) {
    const patterns = [
      `Auto-Claude-${version}-linux-x64.AppImage`,
      `Auto-Claude-${version}.AppImage`,
    ];
    for (const pattern of patterns) {
      const appImagePath = path.join(distDir, pattern);
      if (fs.existsSync(appImagePath)) {
        return appImagePath;
      }
    }
  }
  return null;
}

async function main() {
  console.log('Auto-Claude Rebuild & Install\n');

  // Step 1: Build
  console.log('Step 1: Building application...\n');

  let buildCmd;
  if (isWindows) {
    buildCmd = 'npm run package:win';
  } else if (isMac) {
    buildCmd = 'npm run package:mac';
  } else {
    buildCmd = 'npm run package:linux';
  }

  try {
    execSync(buildCmd, {
      cwd: frontendDir,
      stdio: 'inherit',
    });
  } catch (error) {
    console.error('\nBuild failed!');
    process.exit(1);
  }

  // Step 2: Find and run installer
  console.log('\nStep 2: Installing...\n');

  const version = getPackageVersion();
  const installer = findInstaller(version);

  if (!installer) {
    console.error('Could not find installer in dist/');
    console.log('Available files:');
    fs.readdirSync(distDir).forEach(f => console.log(`  ${f}`));
    process.exit(1);
  }

  console.log(`Found installer: ${path.basename(installer)}`);

  if (isWindows) {
    // NSIS installer supports /S for silent install
    const args = silent ? ['/S'] : [];
    console.log(silent ? 'Installing silently...' : 'Launching installer...');

    const child = spawn(installer, args, {
      detached: true,
      stdio: 'ignore',
    });
    child.unref();

    if (silent) {
      console.log('\nSilent installation started.');
      console.log('The app will be updated in the background.');
    } else {
      console.log('\nInstaller launched. Complete the installation to update.');
    }
  } else if (isMac) {
    // Open DMG on macOS
    console.log('Opening DMG...');
    execSync(`open "${installer}"`, { stdio: 'inherit' });
    console.log('\nDMG opened. Drag Auto-Claude to Applications to install.');
  } else if (isLinux) {
    // Make AppImage executable
    console.log('Making AppImage executable...');
    execSync(`chmod +x "${installer}"`, { stdio: 'inherit' });
    console.log(`\nAppImage ready: ${installer}`);
    console.log('Run it directly or move to a permanent location.');
  }

  console.log('\nDone! Your desktop shortcut will launch the updated version.');
}

main().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
