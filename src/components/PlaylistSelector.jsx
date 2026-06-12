import React, { useState } from 'react';
import { Key, Link, Upload, Loader, Tv, AlertCircle } from 'lucide-react';
import { parseM3U } from '../utils/parsers';

export default function PlaylistSelector({ onPlaylistLoaded, onError }) {
  const [activeTab, setActiveTab] = useState('xtream');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Xtream Codes state
  const [xtreamUrl, setXtreamUrl] = useState('http://s1.dnspass.xyz');
  const [username, setUsername] = useState('yaevqytp');
  const [password, setPassword] = useState('i1D45f9uCd');

  // M3U URL state
  const [m3uUrl, setM3uUrl] = useState('http://s1.dnspass.xyz/get.php?username=yaevqytp&password=i1D45f9uCd&type=m3u_plus&output=ts');

  // CORS proxy setting for loading urls
  const useProxy = true;
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
      setErrorMsg(`Connection error: ${err.message}. Ensure credentials are correct or try uploading an M3U file.`);
      onError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleM3uUrlSubmit = async (e) => {
    e.preventDefault();
    if (!m3uUrl) return;

    setLoading(true);
    setErrorMsg('');

    try {
      let text;
      let usedProxy = false;

      try {
        // Try direct fetch first
        const response = await fetch(m3uUrl);
        if (!response.ok) throw new Error(`Status ${response.status}`);
        text = await response.text();
        if (text.trim().startsWith('<html') || text.trim().startsWith('<!doctype')) {
          throw new Error('Received HTML response instead of M3U');
        }
      } catch (directErr) {
        console.warn('Direct fetch failed, falling back to CORS proxy:', directErr);
        // Fallback to proxy fetch
        try {
          const fetchUrl = `${proxyUrl}${encodeURIComponent(m3uUrl)}`;
          const response = await fetch(fetchUrl);
          if (!response.ok) throw new Error(`Status ${response.status}`);
          text = await response.text();
          if (text.trim().startsWith('<html') || text.trim().startsWith('<!doctype')) {
            throw new Error('Received HTML response from proxy instead of M3U');
          }
          usedProxy = true;
        } catch (proxyErr) {
          console.error('Both direct and proxy fetch failed:', proxyErr);
          throw new Error('Failed to fetch playlist. Ensure URL is correct and server is reachable.');
        }
      }

      const parsed = parseM3U(text);

      if (parsed.channels.length === 0) {
        throw new Error('No valid channels found in this M3U file.');
      }

      onPlaylistLoaded({
        type: 'm3u',
        name: 'M3U Playlist',
        channels: parsed.channels,
        categories: parsed.categories,
        url: m3uUrl,
        useProxy: usedProxy,
        proxyUrl
      });
    } catch (err) {
      console.error(err);
      setErrorMsg(`Failed to load playlist: ${err.message}. If this is a CORS issue, please download the M3U file locally and upload it using the "Local File" tab.`);
      onError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setLoading(true);
    setErrorMsg('');

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target.result;
        const parsed = parseM3U(text);

        if (parsed.channels.length === 0) {
          throw new Error('No valid channels found in this file.');
        }

        onPlaylistLoaded({
          type: 'm3u',
          name: file.name,
          channels: parsed.channels,
          categories: parsed.categories,
          fileUploaded: true
        });
      } catch (err) {
        setErrorMsg(err.message);
        onError(err.message);
      } finally {
        setLoading(false);
      }
    };
    reader.onerror = () => {
      setErrorMsg('Failed to read file.');
      setLoading(false);
    };
    reader.readAsText(file);
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

        {/* Tab selection */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)', marginBottom: '24px' }}>
          <button 
            onClick={() => { setActiveTab('xtream'); setErrorMsg(''); }}
            className={`tab-btn ${activeTab === 'xtream' ? 'active' : ''}`}
          >
            <Key size={14} /> Xtream API
          </button>
          <button 
            onClick={() => { setActiveTab('m3u_url'); setErrorMsg(''); }}
            className={`tab-btn ${activeTab === 'm3u_url' ? 'active' : ''}`}
          >
            <Link size={14} /> M3U URL
          </button>
          <button 
            onClick={() => { setActiveTab('file'); setErrorMsg(''); }}
            className={`tab-btn ${activeTab === 'file' ? 'active' : ''}`}
          >
            <Upload size={14} /> Local File
          </button>
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
          <>
            {activeTab === 'xtream' && (
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

            {activeTab === 'm3u_url' && (
              <form onSubmit={handleM3uUrlSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <label className="input-label">M3U or M3U Plus URL</label>
                  <input 
                    type="url" 
                    className="input-field" 
                    value={m3uUrl} 
                    onChange={e => setM3uUrl(e.target.value)} 
                    placeholder="http://server.com/get.php?username=..." 
                    required 
                  />
                </div>



                <button type="submit" className="btn btn-primary" style={{ marginTop: '8px' }}>
                  Fetch Playlist
                </button>

                <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '16px', marginTop: '8px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-dark)', display: 'block', marginBottom: '8px' }}>USER PLAYLIST PRESETS</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <button
                      type="button"
                      className="preset-btn"
                      onClick={() => setM3uUrl('http://s1.dnspass.xyz/get.php?username=yaevqytp&password=i1D45f9uCd&type=m3u_plus&output=ts')}
                    >
                      M3U Plus (Live & VOD)
                    </button>
                    <button
                      type="button"
                      className="preset-btn"
                      onClick={() => setM3uUrl('http://s1.dnspass.xyz/get.php?username=yaevqytp&password=i1D45f9uCd&type=m3u&output=ts')}
                    >
                      Normal M3U
                    </button>
                  </div>
                </div>
              </form>
            )}

            {activeTab === 'file' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{
                  border: '2px dashed var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  padding: '40px 20px',
                  textAlign: 'center',
                  cursor: 'pointer',
                  position: 'relative',
                  background: 'rgba(255, 255, 255, 0.01)',
                  transition: 'all 0.2s ease',
                }}
                className="file-dropzone"
                onDragOver={(e) => e.preventDefault()}
                >
                  <input 
                    type="file" 
                    accept=".m3u,.m3u8,.txt" 
                    onChange={handleFileUpload} 
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: '100%',
                      opacity: 0,
                      cursor: 'pointer'
                    }}
                  />
                  <Upload size={32} style={{ color: 'var(--text-muted)', marginBottom: '12px' }} />
                  <p style={{ fontSize: '14px', fontWeight: '500', marginBottom: '4px' }}>Drag & Drop your M3U Playlist here</p>
                  <p style={{ fontSize: '12px', color: 'var(--text-dark)' }}>Supports .m3u, .m3u8, and text files</p>
                </div>
                <div style={{ 
                  background: 'rgba(255, 255, 255, 0.02)', 
                  border: '1px solid var(--border-color)', 
                  borderRadius: 'var(--radius-sm)', 
                  padding: '12px', 
                  fontSize: '12px', 
                  color: 'var(--text-muted)' 
                }}>
                  💡 **Tip**: Dragging and dropping an M3U file parses it inside your browser memory. This is completely secure, avoids CORS network errors, and supports large playlists instantly.
                </div>
              </div>
            )}
          </>
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
        .tab-btn {
          flex: 1;
          background: transparent;
          border: none;
          color: var(--text-muted);
          font-family: var(--font-sans);
          font-size: 14px;
          font-weight: 500;
          padding: 12px 8px;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          transition: all 0.2s ease;
          border-bottom: 2px solid transparent;
        }
        .tab-btn:hover {
          color: var(--text-main);
        }
        .tab-btn.active {
          color: var(--primary);
          border-bottom-color: var(--primary);
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
        .preset-btn {
          width: 100%;
          text-align: left;
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid var(--border-color);
          color: var(--text-main);
          font-size: 13px;
          padding: 8px 12px;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        .preset-btn:hover {
          background: var(--primary-glow);
          border-color: var(--primary);
          color: var(--primary);
        }
        .file-dropzone:hover {
          border-color: var(--primary);
          background: var(--primary-glow);
        }
        .spin-animation {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
