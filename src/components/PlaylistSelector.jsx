import React, { useState, useEffect } from 'react';
import { Loader, Tv, AlertCircle, Lock, ChevronLeft, CheckCircle } from 'lucide-react';

export default function PlaylistSelector({ onPlaylistLoaded, onError }) {
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Xtream Codes state
  const [xtreamUrl, setXtreamUrl] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  // Admin panel state
  const [adminMode, setAdminMode] = useState('none'); // 'none', 'auth', 'config'
  const [adminPassword, setAdminPassword] = useState('');
  const [newAdminPassword, setNewAdminPassword] = useState('');
  const [adminError, setAdminError] = useState('');
  const [adminSuccess, setAdminSuccess] = useState('');
  const [adminLoading, setAdminLoading] = useState(false);

  // Admin config edit states
  const [tempXtreamUrl, setTempXtreamUrl] = useState('');
  const [tempUsername, setTempUsername] = useState('');
  const [tempPassword, setTempPassword] = useState('');

  // CORS proxy setting for loading urls
  const proxyUrl = 'https://api.allorigins.win/raw?url=';

  // Fetch custom server defaults on mount
  useEffect(() => {
    const fetchDefaultConfig = async () => {
      try {
        const response = await fetch('/api/config');
        if (response.ok) {
          const data = await response.json();
          if (data.xtreamUrl) setXtreamUrl(data.xtreamUrl);
          if (data.username) setUsername(data.username);
          if (data.password) setPassword(data.password);
        }
      } catch (err) {
        console.warn('Could not fetch server default config, using client defaults:', err);
      }
    };
    fetchDefaultConfig();
  }, []);

  const handleXtreamLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');

    try {
      const targetUrl = `${xtreamUrl}/player_api.php?username=${username}&password=${password}`;
      
      let data;
      let usedProxy = false;

      try {
        const response = await fetch(targetUrl);
        if (!response.ok) throw new Error(`Status ${response.status}`);
        const text = await response.text();
        data = JSON.parse(text);
      } catch (directErr) {
        console.warn('Direct fetch failed, falling back to CORS proxy:', directErr);
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

  const handleAdminAuth = async (e) => {
    e.preventDefault();
    setAdminLoading(true);
    setAdminError('');
    try {
      const response = await fetch(`/api/config?adminPassword=${encodeURIComponent(adminPassword)}`);
      if (response.ok) {
        const data = await response.json();
        setTempXtreamUrl(data.config.xtreamUrl || '');
        setTempUsername(data.config.username || '');
        setTempPassword(data.config.password || '');
        setAdminMode('config');
      } else {
        const errData = await response.json();
        throw new Error(errData.error || 'Invalid admin password');
      }
    } catch (err) {
      setAdminError(err.message);
    } finally {
      setAdminLoading(false);
    }
  };

  const handleAdminSave = async (e) => {
    e.preventDefault();
    setAdminLoading(true);
    setAdminError('');
    setAdminSuccess('');
    try {
      const response = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          adminPassword,
          xtreamUrl: tempXtreamUrl,
          username: tempUsername,
          password: tempPassword,
          newAdminPassword: newAdminPassword || undefined
        })
      });

      if (response.ok) {
        setAdminSuccess('Configuration saved successfully!');
        
        // Update form prefill
        setXtreamUrl(tempXtreamUrl);
        setUsername(tempUsername);
        setPassword(tempPassword);
        setNewAdminPassword('');

        setTimeout(() => {
          setAdminMode('none');
          setAdminSuccess('');
          setAdminPassword('');
        }, 1500);
      } else {
        const errData = await response.json();
        throw new Error(errData.error || 'Failed to update configuration');
      }
    } catch (err) {
      setAdminError(err.message);
    } finally {
      setAdminLoading(false);
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

        {/* ADMIN MODE: AUTHENTICATION */}
        {adminMode === 'auth' && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
              <button 
                type="button" 
                onClick={() => setAdminMode('none')}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center' }}
              >
                <ChevronLeft size={16} /> Back
              </button>
              <span style={{ fontSize: '14px', fontWeight: '700', textTransform: 'uppercase', color: 'var(--primary)', letterSpacing: '0.05em' }}>
                Admin Authentication
              </span>
            </div>

            {adminError && (
              <div style={{ display: 'flex', gap: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', marginBottom: '20px', color: '#f87171', fontSize: '13px' }}>
                <AlertCircle size={18} style={{ flexShrink: 0 }} />
                <div>{adminError}</div>
              </div>
            )}

            {adminLoading ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '30px 0' }}>
                <Loader className="spin-animation" size={24} style={{ color: 'var(--primary)', marginBottom: '12px' }} />
                <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Authenticating...</p>
              </div>
            ) : (
              <form onSubmit={handleAdminAuth} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <label className="input-label">Admin Password</label>
                  <div style={{ position: 'relative' }}>
                    <Lock size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dark)' }} />
                    <input 
                      type="password" 
                      className="input-field" 
                      value={adminPassword} 
                      onChange={e => setAdminPassword(e.target.value)} 
                      placeholder="Enter admin password" 
                      style={{ paddingLeft: '36px' }}
                      required 
                    />
                  </div>
                </div>
                <button type="submit" className="btn btn-primary" style={{ marginTop: '8px' }}>
                  Login to Admin Panel
                </button>
              </form>
            )}
          </div>
        )}

        {/* ADMIN MODE: CONFIGURATION */}
        {adminMode === 'config' && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
              <button 
                type="button" 
                onClick={() => {
                  setAdminMode('none');
                  setAdminPassword('');
                }}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center' }}
              >
                <ChevronLeft size={16} /> Cancel
              </button>
              <span style={{ fontSize: '14px', fontWeight: '700', textTransform: 'uppercase', color: 'var(--primary)', letterSpacing: '0.05em' }}>
                Admin Configuration
              </span>
            </div>

            {adminError && (
              <div style={{ display: 'flex', gap: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', marginBottom: '20px', color: '#f87171', fontSize: '13px' }}>
                <AlertCircle size={18} style={{ flexShrink: 0 }} />
                <div>{adminError}</div>
              </div>
            )}

            {adminSuccess && (
              <div style={{ display: 'flex', gap: '12px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.2)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', marginBottom: '20px', color: '#34d399', fontSize: '13px' }}>
                <CheckCircle size={18} style={{ flexShrink: 0 }} />
                <div>{adminSuccess}</div>
              </div>
            )}

            {adminLoading ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '30px 0' }}>
                <Loader className="spin-animation" size={24} style={{ color: 'var(--primary)', marginBottom: '12px' }} />
                <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Saving configuration...</p>
              </div>
            ) : (
              <form onSubmit={handleAdminSave} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <label className="input-label">Default Server Host URL</label>
                  <input 
                    type="url" 
                    className="input-field" 
                    value={tempXtreamUrl} 
                    onChange={e => setTempXtreamUrl(e.target.value)} 
                    placeholder="http://example.com:8080" 
                    required 
                  />
                </div>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div>
                    <label className="input-label">Default Username</label>
                    <input 
                      type="text" 
                      className="input-field" 
                      value={tempUsername} 
                      onChange={e => setTempUsername(e.target.value)} 
                      placeholder="Username" 
                      required 
                    />
                  </div>
                  <div>
                    <label className="input-label">Default Password</label>
                    <input 
                      type="text" 
                      className="input-field" 
                      value={tempPassword} 
                      onChange={e => setTempPassword(e.target.value)} 
                      placeholder="Password" 
                      required 
                    />
                  </div>
                </div>

                <div style={{ borderTop: '1px solid var(--border-color)', marginTop: '8px', paddingTop: '16px' }}>
                  <label className="input-label">Change Admin Password (Optional)</label>
                  <input 
                    type="password" 
                    className="input-field" 
                    value={newAdminPassword} 
                    onChange={e => setNewAdminPassword(e.target.value)} 
                    placeholder="Enter new admin password" 
                  />
                </div>

                <button type="submit" className="btn btn-primary" style={{ marginTop: '8px' }}>
                  Save Configuration
                </button>
              </form>
            )}
          </div>
        )}

        {/* STANDARD USER LOGIN FORM */}
        {adminMode === 'none' && (
          <div>
            {errorMsg && (
              <div style={{ display: 'flex', gap: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', marginBottom: '20px', color: '#f87171', fontSize: '13px', lineHeight: '1.5' }}>
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
              <div>
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
                        type="text" 
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

                {/* Server Admin Panel Link */}
                <div style={{ textAlign: 'center', marginTop: '24px', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
                  <button 
                    type="button" 
                    onClick={() => {
                      setAdminMode('auth');
                      setAdminPassword('');
                      setAdminError('');
                    }} 
                    className="admin-link-btn"
                  >
                    🔐 Server Admin Panel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

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

        .admin-link-btn {
          background: transparent;
          border: none;
          color: var(--text-dark);
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          transition: color 0.2s ease;
        }
        .admin-link-btn:hover {
          color: var(--primary);
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
