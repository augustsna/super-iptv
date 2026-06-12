import express from 'express';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;
const CONFIG_FILE = path.join(__dirname, 'config.json');

app.use(express.json());

// Enable CORS for development
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization');
  res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  if (req.method === 'OPTIONS') {
    return res.sendStatus(200);
  }
  next();
});

// GET configuration
app.get('/api/config', (req, res) => {
  if (fs.existsSync(CONFIG_FILE)) {
    try {
      const data = fs.readFileSync(CONFIG_FILE, 'utf8');
      return res.json(JSON.parse(data));
    } catch (err) {
      console.error('Error reading config file:', err);
    }
  }
  // Return default placeholder values if config file doesn't exist
  res.json({
    url: 'http://s1.dnspass.xyz',
    username: 'yaevqytp',
    password: 'i1D45f9uCd'
  });
});

// POST configuration
app.post('/api/config', (req, res) => {
  const authHeader = req.headers.authorization;
  
  // Basic security check: verify admin password
  if (authHeader !== '8899') {
    return res.status(401).json({ error: 'Unauthorized: Invalid admin password' });
  }

  const { url, username, password } = req.body;
  if (!url || !username || !password) {
    return res.status(400).json({ error: 'Missing required configuration fields' });
  }

  const config = { url, username, password };
  try {
    fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2), 'utf8');
    res.json({ success: true, config });
  } catch (err) {
    console.error('Error writing config file:', err);
    res.status(500).json({ error: 'Failed to write configuration file' });
  }
});

// Serve static files from Vite's build output (dist) if accessed directly
app.use(express.static(path.join(__dirname, 'dist')));

// Fallback to index.html for SPA routing
app.get('*', (req, res) => {
  const indexPath = path.join(__dirname, 'dist', 'index.html');
  if (fs.existsSync(indexPath)) {
    res.sendFile(indexPath);
  } else {
    res.status(404).send('Frontend not built. Please run npm run build.');
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
