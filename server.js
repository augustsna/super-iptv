import http from 'http';
import fs from 'fs';
import path from 'path';
import url from 'url';
import { spawn } from 'child_process';

const PORT = process.env.PORT || 5000;
const FFMPEG_BIN = 'C:\\SuperFolder\\ffmpeg\\bin';
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

  // GET /api/probe?url=<encoded> — detect audio codec via ffprobe
  if (pathname === '/api/probe' && req.method === 'GET') {
    const streamUrl = parsedUrl.query.url;
    if (!streamUrl) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Missing url parameter' }));
      return;
    }

    const ffprobe = spawn(path.join(FFMPEG_BIN, 'ffprobe.exe'), [
      '-v', 'quiet',
      '-print_format', 'json',
      '-show_streams',
      '-select_streams', 'a:0',
      '-i', streamUrl
    ]);

    let probeOutput = '';
    ffprobe.stdout.on('data', (chunk) => { probeOutput += chunk.toString(); });
    ffprobe.stderr.on('data', () => {}); // suppress stderr

    ffprobe.on('close', () => {
      try {
        const info = JSON.parse(probeOutput);
        const audioStream = info.streams && info.streams[0];
        const codec = audioStream ? audioStream.codec_name : 'unknown';
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ codec }));
      } catch {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ codec: 'unknown' }));
      }
    });

    ffprobe.on('error', (err) => {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: err.message }));
    });

    return;
  }

  // GET /api/transcode?url=<encoded> — stream with AC3/EAC3 → AAC transcoding via FFmpeg
  if (pathname === '/api/transcode' && req.method === 'GET') {
    const streamUrl = parsedUrl.query.url;
    if (!streamUrl) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Missing url parameter' }));
      return;
    }

    console.log(`[transcode] Starting FFmpeg transcode for: ${streamUrl}`);

    // Set streaming headers before spawning FFmpeg
    res.writeHead(200, {
      'Content-Type': 'video/mp2t',
      'Transfer-Encoding': 'chunked',
      'Cache-Control': 'no-cache, no-store',
      'X-Accel-Buffering': 'no',
    });

    const ffmpeg = spawn(path.join(FFMPEG_BIN, 'ffmpeg.exe'), [
      '-hide_banner',
      '-loglevel', 'warning',
      // Input — tell ffmpeg to keep retrying network streams
      '-reconnect', '1',
      '-reconnect_streamed', '1',
      '-reconnect_delay_max', '5',
      '-i', streamUrl,
      // Video: copy as-is (no re-encode)
      '-c:v', 'copy',
      // Audio: transcode AC3/EAC3 → AAC stereo
      '-c:a', 'aac',
      '-b:a', '192k',
      '-ac', '2',
      // Output as MPEG-TS to stdout
      '-f', 'mpegts',
      '-muxdelay', '0',
      'pipe:1'
    ]);

    // Pipe FFmpeg stdout → HTTP response
    ffmpeg.stdout.pipe(res);

    // Log FFmpeg stderr warnings
    ffmpeg.stderr.on('data', (data) => {
      console.warn('[ffmpeg]', data.toString().trim());
    });

    // Clean up when client disconnects
    req.on('close', () => {
      console.log('[transcode] Client disconnected — killing FFmpeg');
      ffmpeg.kill('SIGKILL');
    });

    ffmpeg.on('error', (err) => {
      console.error('[transcode] FFmpeg spawn error:', err.message);
      if (!res.writableEnded) res.end();
    });

    ffmpeg.on('close', (code) => {
      console.log(`[transcode] FFmpeg exited with code ${code}`);
      if (!res.writableEnded) res.end();
    });

    return;
  }

  // Fallback for page not found
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not Found' }));
});

server.listen(PORT, () => {
  console.log(`IPTV Config API running on port ${PORT}`);
});
