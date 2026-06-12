import { spawn } from 'child_process';

console.log('\x1b[36m%s\x1b[0m', '--> Starting Express Backend (Port 3000)...');
const backend = spawn('node', ['server.js'], { 
  stdio: 'inherit', 
  shell: true 
});

console.log('\x1b[36m%s\x1b[0m', '--> Starting Vite Frontend Dev Server...');
const frontend = spawn('npx', ['vite'], { 
  stdio: 'inherit', 
  shell: true 
});

// Forward process exit signals to children
const cleanExit = () => {
  backend.kill();
  frontend.kill();
  process.exit();
};

process.on('SIGINT', cleanExit);
process.on('SIGTERM', cleanExit);
process.on('exit', cleanExit);
