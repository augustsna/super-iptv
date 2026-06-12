import React, { useState } from 'react';
import { Loader, Tv, AlertCircle } from 'lucide-react';

export default function PlaylistSelector({ onPlaylistLoaded, onError }) {
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Xtream Codes state
  const [xtreamUrl, setXtreamUrl] = useState('http://s1.dnspass.xyz');
  const [username, setUsername] = useState('yaevqytp');
  const [password, setPassword] = useState('i1D45f9uCd');

  // CORS proxy setting for loading urls
  const proxyUrl = 'https://api.allorigins.win/raw?url=';

  const handleXtreamLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');

    try {
      // Xtream Codes login involves checking credentials and retrieving categories
      // We will make a login request to the server
      const targetUrl = `${xtreamUrl}/player_api.php?username=${username}&password=${password}`;
      
      let data;
      let usedProxy = false;

      try {
        // Try direct fetch first (if server has CORS headers, this succeeds instantly)
        const response = await fetch(targetUrl);
        if (!response.ok) throw new Error(`Status ${response.status}`);
        const text = await response.text();
        data = JSON.parse(text);
      } catch (directErr) {
        console.warn('Direct fetch failed, falling back to CORS proxy:', directErr);
        // Fallback to proxy fetch
        try {
          const fetchUrl = `${proxyUrl}${encodeURIComponent(targetUrl)}`;
          const response = await fetch(fetchUrl);
          if (!response.ok) throw new Error(`Status ${response.status}`);
          const text = await response.text();
          data = JSON.parse(text);
          usedProxy = true;
        } catch (proxyErr) {
          console.error('Both direct and proxy fetch failed:', proxyErr);
          throw new Error('Connection failed. Server might be offline or proxy is blocked.');
        }
      }
      
      if (data.user_info && data.user_info.status === 'Active') {
        onPlaylistLoaded({
          type: 'xtream',
          credentials: { host: xtreamUrl, username, password },
          userInfo: data.user_info,
          serverInfo: data.server_info,
          useProxy: usedProxy,
          proxyUrl
        });
      } else {
        throw new Error(data.user_info?.status || 'Authentication failed. Please verify credentials.');
      }
    } catch (err) {
      console.error(err);
      setErrorMsg(`Connection error: ${err.message}. Ensure credentials are correct.`);
      onError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="playlist-selector-container">
      <div className="glass-panel" style={{ padding: '40px', maxWidth: '520px', width: '100%', margin: 'auto' }}>
        
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{
            display: 'inline-flex',
            padding: '16px',
            borderRadius: '50%',
            background: 'var(--primary-glow)',
            color: 'var(--primary)',
            marginBottom: '16px',
            border: '1px solid var(--border-active)'
          }}>
            <Tv size={36} />
          </div>
          <h1 className="text-digital glow-text-primary" style={{ fontSize: '28px', color: 'var(--primary)', marginBottom: '8px' }}>SUPER STREAM</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>August IPTV Player</p>
        </div>

        {errorMsg && (
          <div style={{
            display: 'flex',
            gap: '12px',
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            borderRadius: 'var(--radius-sm)',
            padding: '12px 16px',
            marginBottom: '20px',
            color: '#f87171',
            fontSize: '13px',
            lineHeight: '1.5'
          }}>
            <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>{errorMsg}</div>
          </div>
        )}

        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 0' }}>
            <Loader className="spin-animation" size={32} style={{ color: 'var(--primary)', marginBottom: '16px' }} />
            <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Connecting and parsing channels...</p>
          </div>
        ) : (
          <form onSubmit={handleXtreamLogin} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label className="input-label">Server Host URL</label>
              <input 
                type="url" 
                className="input-field" 
                value={xtreamUrl} 
                onChange={e => setXtreamUrl(e.target.value)} 
                placeholder="http://example.com:8080" 
                required 
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div>
                <label className="input-label">Username</label>
                <input 
                  type="text" 
                  className="input-field" 
                  value={username} 
                  onChange={e => setUsername(e.target.value)} 
                  placeholder="Username" 
                  required 
                />
              </div>
              <div>
                <label className="input-label">Password</label>
                <input 
                  type="password" 
                  className="input-field" 
                  value={password} 
                  onChange={e => setPassword(e.target.value)} 
                  placeholder="Password" 
                  required 
                />
              </div>
            </div>
            
            <button type="submit" className="btn btn-primary" style={{ marginTop: '8px' }}>
              Load Stream Portal
            </button>
          </form>
        )}
      </div>

      {/* Styled JSX for component specific states not fitting nicely in index.css */}
      <style>{`
        .playlist-selector-container {
          display: flex;
          height: 100vh;
          width: 100vw;
          padding: 24px;
          overflow-y: auto;
          background: radial-gradient(circle at center, #151a30 0%, #07090e 100%);
        }

        .input-label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          text-transform: uppercase;
          color: var(--text-muted);
          margin-bottom: 6px;
          letter-spacing: 0.05em;
        }

        .spin-animation {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        @media (max-width: 480px) {
          .playlist-selector-container {
            padding: 12px;
          }
          .playlist-selector-container .glass-panel {
            padding: 24px 16px !important;
            margin: auto 0;
          }
          .playlist-selector-container h1 {
            font-size: 22px !important;
          }
          .playlist-selector-container p {
            font-size: 12px !important;
          }
          .playlist-selector-container form > div {
            grid-template-columns: 1fr !important;
            gap: 12px !important;
          }
        }
      `}</style>
    </div>
  );
}
