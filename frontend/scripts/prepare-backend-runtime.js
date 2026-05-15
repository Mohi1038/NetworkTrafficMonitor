const { execFileSync, spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const frontendDir = path.resolve(__dirname, '..');
const backendDir = path.resolve(frontendDir, '..', 'backend');
const requirementsFile = path.join(backendDir, 'requirements.txt');

function run(command, args) {
  execFileSync(command, args, {
    stdio: 'inherit',
    cwd: backendDir,
    shell: false
  });
}

function commandExists(command, args = ['--version']) {
  const result = spawnSync(command, args, { stdio: 'ignore', shell: false });
  return result.status === 0;
}

function resolvePythonLauncher() {
  const candidates = process.platform === 'win32'
    ? [
        { command: 'py', args: ['-3'] },
        { command: 'python', args: [] },
        { command: 'python3', args: [] }
      ]
    : [
        { command: 'python3', args: [] },
        { command: 'python', args: [] }
      ];

  for (const candidate of candidates) {
    if (commandExists(candidate.command, [...candidate.args, '--version'])) {
      return candidate;
    }
  }

  throw new Error('No Python launcher found. Install Python 3.8+ to build self-contained installers.');
}

function getVenvPaths() {
  const venvDir = path.join(backendDir, 'venv');
  if (process.platform === 'win32') {
    return {
      venvDir,
      pythonPath: path.join(venvDir, 'Scripts', 'python.exe'),
      pipArgs: ['-m', 'pip']
    };
  }

  return {
    venvDir,
    pythonPath: path.join(venvDir, 'bin', 'python'),
    pipArgs: ['-m', 'pip']
  };
}

function main() {
  if (!fs.existsSync(requirementsFile)) {
    throw new Error(`Missing requirements file: ${requirementsFile}`);
  }

  const launcher = resolvePythonLauncher();
  const { venvDir, pythonPath, pipArgs } = getVenvPaths();

  console.log(`[prepare-backend-runtime] Backend directory: ${backendDir}`);

  if (!fs.existsSync(pythonPath)) {
    console.log('[prepare-backend-runtime] Creating backend virtual environment...');
    run(launcher.command, [...launcher.args, '-m', 'venv', venvDir]);
  } else {
    console.log('[prepare-backend-runtime] Reusing existing backend virtual environment.');
  }

  console.log('[prepare-backend-runtime] Upgrading pip...');
  run(pythonPath, [...pipArgs, 'install', '--upgrade', 'pip']);

  console.log('[prepare-backend-runtime] Installing backend dependencies...');
  run(pythonPath, [...pipArgs, 'install', '-r', requirementsFile]);

  console.log('[prepare-backend-runtime] Backend runtime is ready for packaging.');
}

try {
  main();
} catch (error) {
  console.error(`[prepare-backend-runtime] ${error.message}`);
  process.exit(1);
}
