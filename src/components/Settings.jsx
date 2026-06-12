import React, { useState } from 'react';
import { Sliders, Shield, Trash2, Key, Info, Globe, AlertTriangle } from 'lucide-react';

export default function Settings({ 
  playlistInfo, 
  onClearPlaylist, 
  onClearFavorites,
  useProxy,
  setUseProxy,
  proxyUrl,
  setProxyUrl
}) {
  const [proxyPreset, setProxyPreset] = useState('allorigins');
  const [customProxy, setCustomProxy] = useState('');

  const handlePresetChange = (preset) => {
    setProxyPreset(preset);
    if (preset === 'allorigins') {
      setUseProxy(true);
      setProxyUrl('https://api.allorigins.win/raw?url=');
    } else if (preset === 'cors-anywhere') {
      setUseProxy(true);
      setProxyUrl('https://cors-anywhere.herokuapp.com/');
    } else if (preset === 'none') {
      setUseProxy(false);
    } else if (preset === 'custom') {
      setUseProxy(true);
      setProxyUrl(customProxy);
    }
  };

  const handleCustomProxyBlur = () => {
    if (proxyPreset === 'custom') {
      setProxyUrl(customProxy);
    }
  };

  return (
    <div className="settings-container animate-slide-in">
      <div className="settings-content glass-panel">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '24px', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
          <Sliders size={24} style={{ color: 'var(--primary)' }} />
          <h2 className="text-digital glow-text-primary" style={{ fontSize: '20px', color: 'var(--primary)' }}>Application Settings</h2>
        </div>

        {/* CORS PROXY SECTION */}
        <section className="settings-section">
          <div className="section-title">
            <Globe size={18} />
            <span>CORS Network Proxy</span>
          </div>
          <div className="section-body">
            <p className="setting-description">
              Because this web app runs client-side inside your browser, loading playlists or EPG data from servers without CORS headers will fail. Toggling a proxy routes requests through an external helper to bypass restrictions.
            </p>

            <div className="proxy-selector-grid">
              <label className={`preset-card ${proxyPreset === 'allorigins' ? 'active' : ''}`}>
                <input 
                  type="radio" 
                  name="proxyPreset" 
                  checked={proxyPreset === 'allorigins'} 
                  onChange={() => handlePresetChange('allorigins')} 
                />
                <div className="preset-name">AllOrigins Proxy</div>
                <div className="preset-desc">Recommended. Free CORS filter wrapper.</div>
              </label>

              <label className={`preset-card ${proxyPreset === 'cors-anywhere' ? 'active' : ''}`}>
                <input 
                  type="radio" 
                  name="proxyPreset" 
                  checked={proxyPreset === 'cors-anywhere'} 
                  onChange={() => handlePresetChange('cors-anywhere')} 
                />
                <div className="preset-name">CORS Anywhere</div>
                <div className="preset-desc">Requires clicking a button to activate temp access.</div>
              </label>

              <label className={`preset-card ${proxyPreset === 'custom' ? 'active' : ''}`}>
                <input 
                  type="radio" 
                  name="proxyPreset" 
                  checked={proxyPreset === 'custom'} 
                  onChange={() => handlePresetChange('custom')} 
                />
                <div className="preset-name">Custom Proxy</div>
                <div className="preset-desc">Define your own proxy endpoint url.</div>
              </label>

              <label className={`preset-card ${proxyPreset === 'none' ? 'active' : ''}`}>
                <input 
                  type="radio" 
                  name="proxyPreset" 
                  checked={proxyPreset === 'none'} 
                  onChange={() => handlePresetChange('none')} 
                />
                <div className="preset-name">Disable Proxy</div>
                <div className="preset-desc">Direct fetch connection. Only works if server supports CORS.</div>
              </label>
            </div>

            {proxyPreset === 'custom' && (
              <div style={{ marginTop: '16px' }}>
                <label className="input-label">Custom Proxy URL Prefix</label>
                <input 
                  type="url" 
                  className="input-field" 
                  value={customProxy} 
                  onChange={e => setCustomProxy(e.target.value)} 
                  onBlur={handleCustomProxyBlur}
                  placeholder="https://my-proxy.com/api?url=" 
                />
              </div>
            )}
          </div>
        </section>

        {/* SECURE VS INSECURE STREAMS HELP */}
        <section className="settings-section">
          <div className="section-title" style={{ color: 'var(--accent)' }}>
            <Shield size={18} />
            <span>Mixed Content (HTTP Streams in HTTPS Browser)</span>
          </div>
          <div className="section-body">
            <div style={{
              display: 'flex',
              gap: '12px',
              background: 'rgba(5, 255, 197, 0.05)',
              border: '1px solid rgba(5, 255, 197, 0.15)',
              borderRadius: 'var(--radius-sm)',
              padding: '16px',
              fontSize: '13px',
              lineHeight: '1.5'
            }}>
              <AlertTriangle size={24} style={{ color: 'var(--accent)', flexShrink: 0, marginTop: '2px' }} />
              <div>
                <p style={{ fontWeight: '700', color: 'var(--text-main)', marginBottom: '6px' }}>Why is my video player showing a black screen or errors?</p>
                <p style={{ color: 'var(--text-muted)', marginBottom: '8px' }}>
                  Your IPTV links (`http://s1.dnspass.xyz`) are served over **HTTP**, but sites hosted on GitHub Pages are strictly **HTTPS**. Browsers block insecure HTTP streams on secure sites.
                </p>
                <p style={{ fontWeight: '600', color: 'var(--text-main)', marginBottom: '4px' }}>How to fix it:</p>
                <ul style={{ paddingLeft: '16px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <li>
                    <strong>Method 1 (Highly Recommended):</strong> Run this IPTV app locally using <code>npm run dev</code>! Browsers allow HTTP streams to load when the app runs on <code>http://localhost:5173</code> because localhost is treated as a secure development context.
                  </li>
                  <li>
                    <strong>Method 2:</strong> In Chrome, click the 🔒 lock icon next to the URL, select <em>Site Settings</em>, find <em>Insecure content</em>, and toggle it to <strong>Allow</strong>. This enables HTTP playback for this site.
                  </li>
                  <li>
                    <strong>Method 3:</strong> Install a browser extension like <em>Allow Mixed Content</em> or <em>CORS Unblock</em>.
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* DATA MANAGEMENT */}
        <section className="settings-section">
          <div className="section-title" style={{ color: '#ef4444' }}>
            <Trash2 size={18} />
            <span>Cache & Data Management</span>
          </div>
          <div className="section-body" style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
            <div>
              <button className="btn btn-secondary" onClick={onClearFavorites} style={{ border: '1px solid rgba(239,68,68,0.2)', color: '#f87171' }}>
                Clear Favorites List
              </button>
              <span style={{ display: 'block', fontSize: '11px', color: 'var(--text-dark)', marginTop: '6px' }}>Removes all starred channels from browser cache</span>
            </div>
            <div>
              <button className="btn btn-secondary" onClick={onClearPlaylist} style={{ border: '1px solid rgba(239,68,68,0.2)', color: '#f87171' }}>
                Disconnect Active Playlist
              </button>
              <span style={{ display: 'block', fontSize: '11px', color: 'var(--text-dark)', marginTop: '6px' }}>Resets the application back to the login screen</span>
            </div>
          </div>
        </section>
      </div>

      <style>{`
        .settings-container {
          padding: 24px;
          height: 100%;
          overflow-y: auto;
          display: flex;
          justify-content: center;
        }
        
        .settings-content {
          max-width: 800px;
          width: 100%;
          padding: 32px;
          height: fit-content;
        }

        .settings-section {
          margin-bottom: 32px;
        }
        .section-title {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 15px;
          font-weight: 700;
          color: var(--primary);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 12px;
        }
        .section-body {
          padding-left: 28px;
        }
        .setting-description {
          font-size: 13px;
          color: var(--text-muted);
          line-height: 1.5;
          margin-bottom: 16px;
        }

        .proxy-selector-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
          gap: 12px;
        }
        
        .preset-card {
          border: 1px solid var(--border-color);
          border-radius: var(--radius-sm);
          padding: 12px;
          cursor: pointer;
          transition: all 0.2s ease;
          background: rgba(255,255,255,0.01);
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .preset-card input {
          display: none;
        }
        .preset-card:hover {
          border-color: rgba(255,255,255,0.15);
          background: rgba(255,255,255,0.03);
        }
        .preset-card.active {
          border-color: var(--primary);
          background: var(--primary-glow);
          box-shadow: 0 0 10px var(--primary-glow);
        }
        
        .preset-name {
          font-size: 13px;
          font-weight: 600;
          color: #fff;
        }
        .preset-card.active .preset-name {
          color: var(--primary);
        }
        .preset-desc {
          font-size: 10px;
          color: var(--text-muted);
          line-height: 1.3;
        }

        .input-label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          text-transform: uppercase;
          color: var(--text-muted);
          margin-bottom: 6px;
        }
      `}</style>
    </div>
  );
}
