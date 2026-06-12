import http from 'http';
import fs from 'fs';
import path from 'path';
import url from 'url';
import { spawn, exec } from 'child_process';

const PORT = process.env.PORT || 5000;
const __filename = url.fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const CONFIG_PATH = path.join(__dirname, 'config.json');

// Hardcoded initial defaults
const DEFAULT_CONFIG = {
  xtreamUrl: '',
  username: '',
  password: '',
  adminPassword: '8899'
};

// Ensure config file exists with default config if not already present
function initConfig() {
  if (!fs.existsSync(CONFIG_PATH)) {
    try {
      fs.writeFileSync(CONFIG_PATH, JSON.stringify(DEFAULT_CONFIG, null, 2), 'utf8');
      console.log('Config file initialized at:', CONFIG_PATH);
    } catch (err) {
      console.error('Failed to initialize config file:', err);
    }
  }
}

// Read current config
function readConfig() {
  try {
    if (fs.existsSync(CONFIG_PATH)) {
      const data = fs.readFileSync(CONFIG_PATH, 'utf8');
      return JSON.parse(data);
    }
  } catch (err) {
    console.error('Error reading config file:', err);
  }
  return DEFAULT_CONFIG;
}

// Write new config
function writeConfig(config) {
  try {
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2), 'utf8');
    return true;
  } catch (err) {
    console.error('Error writing config file:', err);
    return false;
  }
}

// Initialize on start
initConfig();

const server = http.createServer((req, res) => {
  // Add CORS headers for robustness
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;

  // GET /api/config
  if (pathname === '/api/config' && req.method === 'GET') {
    const config = readConfig();
    const queryPassword = parsedUrl.query.adminPassword;

    if (queryPassword !== undefined) {
      // Admin is trying to authenticate
      if (queryPassword === config.adminPassword) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          authenticated: true,
          config: {
            xtreamUrl: config.xtreamUrl,
            username: config.username,
            password: config.password
          }
        }));
      } else {
        res.writeHead(401, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Incorrect admin password' }));
      }
    } else {
      // Public view (get default form values)
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        xtreamUrl: config.xtreamUrl,
        username: config.username,
        password: config.password
      }));
    }
    return;
  }

  // POST /api/config
  if (pathname === '/api/config' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
    });

    req.on('end', () => {
      try {
        const payload = JSON.parse(body);
        const config = readConfig();

        // Verify admin password
        if (payload.adminPassword !== config.adminPassword) {
          res.writeHead(401, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Incorrect admin password' }));
          return;
        }

        // Update config values
        if (payload.xtreamUrl) config.xtreamUrl = payload.xtreamUrl;
        if (payload.username) config.username = payload.username;
        if (payload.password) config.password = payload.password;

        // Update admin password if requested
        if (payload.newAdminPassword && payload.newAdminPassword.trim().length > 0) {
          config.adminPassword = payload.newAdminPassword.trim();
        }

        if (writeConfig(config)) {
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ success: true }));
        } else {
          res.writeHead(500, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Failed to write config' }));
        }
      } catch (err) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Invalid JSON request payload' }));
      }
    });
    return;
  }

  // GET /api/stream
  if (pathname === '/api/stream' && req.method === 'GET') {
    const streamUrl = parsedUrl.query.url;
    if (!streamUrl) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Missing stream url parameter' }));
      return;
    }

    console.log(`[Proxy] Transcoding audio to AAC for stream: ${streamUrl}`);

    // Set headers for live streaming TS format
    res.writeHead(200, {
      'Content-Type': 'video/mp2t',
      'Connection': 'keep-alive',
      'Cache-Control': 'no-cache',
      'Access-Control-Allow-Origin': '*'
    });

    const ffmpegArgs = [
      '-re',
      '-i', streamUrl,
      '-c:v', 'copy',
      '-c:a', 'aac',
      '-b:a', '192k',
      '-ac', '2',
      '-f', 'mpegts',
      'pipe:1'
    ];

    const ffmpeg = spawn('ffmpeg', ffmpegArgs);

    ffmpeg.stdout.pipe(res);

    ffmpeg.on('error', (err) => {
      console.error('[Proxy] FFmpeg process error:', err.message);
      if (err.code === 'ENOENT') {
        console.error('[Proxy] FFmpeg was not found in system PATH. Transcoding failed.');
      }
      res.end();
    });

    req.on('close', () => {
      console.log('[Proxy] Client disconnected, terminating FFmpeg process');
      ffmpeg.kill('SIGKILL');
    });
    return;
  }

  // Fallback for page not found
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not Found' }));
});

function checkFfmpeg() {
  exec('ffmpeg -version', (err) => {
    if (err) {
      console.warn('\x1b[33m%s\x1b[0m', 'WARNING: ffmpeg was not found in your system PATH. AC-3/EC-3 transcoding will fail. Please install FFmpeg on this system.');
    } else {
      console.log('FFmpeg is verified and ready for dynamic audio transcoding.');
    }
  });
}

server.listen(PORT, () => {
  console.log(`IPTV Config API running on port ${PORT}`);
  checkFfmpeg();
});
