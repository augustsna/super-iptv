import React, { useState } from 'react';
import { Loader, Tv, AlertCircle, Shield, Lock } from 'lucide-react';

export default function PlaylistSelector({ onPlaylistLoaded, onError }) {
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Loaded default values from localStorage, fallback to initial defaults
  const getDefaultUrl = () => localStorage.getItem('admin_placeholder_url') || 'http://s1.dnspass.xyz';
  const getDefaultUsername = () => localStorage.getItem('admin_placeholder_username') || 'yaevqytp';
  const getDefaultPassword = () => localStorage.getItem('admin_placeholder_password') || 'i1D45f9uCd';

  // Xtream Codes login form state
  const [xtreamUrl, setXtreamUrl] = useState(getDefaultUrl);
  const [username, setUsername] = useState(getDefaultUsername);
  const [password, setPassword] = useState(getDefaultPassword);

  // Admin view states
  const [showAdminPrompt, setShowAdminPrompt] = useState(false);
  const [isAdminMode, setIsAdminMode] = useState(false);
  const [adminInputPassword, setAdminInputPassword] = useState('');
  const [adminPromptError, setAdminPromptError] = useState('');

  // Admin configuration form state
  const [tempUrl, setTempUrl] = useState(getDefaultUrl);
  const [tempUsername, setTempUsername] = useState(getDefaultUsername);
  const [tempPassword, setTempPassword] = useState(getDefaultPassword);

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

  const handleOpenAdminPrompt = () => {
    setAdminInputPassword('');
    setAdminPromptError('');
    setShowAdminPrompt(true);
  };

  const handleAdminVerify = (e) => {
    e.preventDefault();
    if (adminInputPassword === '8899') {
      setAdminPromptError('');
      setShowAdminPrompt(false);
      setIsAdminMode(true);
      // Reset temp values with current stored placeholders
      setTempUrl(getDefaultUrl());
      setTempUsername(getDefaultUsername());
      setTempPassword(getDefaultPassword());
    } else {
      setAdminPromptError('Incorrect password! Please try again.');
    }
  };

  const handleSaveAdminConfig = (e) => {
    e.preventDefault();
    localStorage.setItem('admin_placeholder_url', tempUrl);
    localStorage.setItem('admin_placeholder_username', tempUsername);
    localStorage.setItem('admin_placeholder_password', tempPassword);

    // Sync input form states to the newly configured default/placeholder values
    setXtreamUrl(tempUrl);
    setUsername(tempUsername);
    setPassword(tempPassword);

    setIsAdminMode(false);
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 0' }}>
          <Loader className="spin-animation" size={32} style={{ color: 'var(--primary)', marginBottom: '16px' }} />
          <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Connecting and parsing channels...</p>
        </div>
      );
    }

    if (showAdminPrompt) {
      return (
        <form onSubmit={handleAdminVerify} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            <Lock size={22} style={{ color: 'var(--primary)' }} />
            <h2 className="text-digital glow-text-primary" style={{ fontSize: '18px', color: 'var(--primary)', margin: 0 }}>ADMIN ACCESS</h2>
          </div>

          {adminPromptError && (
            <div style={{
              display: 'flex',
              gap: '12px',
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.2)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px 16px',
              color: '#f87171',
              fontSize: '13px'
            }}>
              <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>{adminPromptError}</div>
            </div>
          )}

          <div>
            <label className="input-label">Admin Password</label>
            <input
              type="text"
              className="input-field"
              value={adminInputPassword}
              onChange={e => setAdminInputPassword(e.target.value)}
              placeholder="Enter password"
              required
              autoFocus
            />
          </div>

          <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ flex: 1 }}
              onClick={() => setShowAdminPrompt(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              style={{ flex: 1 }}
            >
              Verify
            </button>
          </div>
        </form>
      );
    }

    if (isAdminMode) {
      return (
        <form onSubmit={handleSaveAdminConfig} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            <Shield size={22} style={{ color: 'var(--accent)' }} />
            <h2 className="text-digital glow-text-accent" style={{ fontSize: '18px', color: 'var(--accent)', margin: 0 }}>ADMIN CONFIG</h2>
          </div>

          <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '4px', lineHeight: '1.4' }}>
            Change default placeholders and values for login form.
          </p>

          <div>
            <label className="input-label">Default Host URL</label>
            <input
              type="url"
              className="input-field"
              value={tempUrl}
              onChange={e => setTempUrl(e.target.value)}
              placeholder="http://example.com:8080"
              required
            />
          </div>

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

          <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ flex: 1 }}
              onClick={() => setIsAdminMode(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-accent"
              style={{ flex: 1 }}
            >
              Save Config
            </button>
          </div>
        </form>
      );
    }

    return (
      <form onSubmit={handleXtreamLogin} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <label className="input-label">Server Host URL</label>
          <input
            type="url"
            className="input-field"
            value={xtreamUrl}
            onChange={e => setXtreamUrl(e.target.value)}
            placeholder={getDefaultUrl()}
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
              placeholder={getDefaultUsername()}
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
              placeholder={getDefaultPassword()}
              required
            />
          </div>
        </div>

        <button type="submit" className="btn btn-primary" style={{ marginTop: '8px' }}>
          Log in
        </button>

        <button
          type="button"
          className="btn btn-secondary"
          onClick={handleOpenAdminPrompt}
          style={{
            marginTop: '8px',
            borderColor: 'rgba(255, 255, 255, 0.05)',
            fontSize: '12px',
            padding: '8px 16px'
          }}
        >
          <Shield size={14} style={{ color: 'var(--text-muted)' }} />
          Admin Panel
        </button>
      </form>
    );
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

        {errorMsg && !showAdminPrompt && !isAdminMode && (
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

        {renderContent()}
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
