import React from 'react';
import { Tv, Film, Clapperboard, Heart, Settings, LogOut, Radio } from 'lucide-react';

export default function Sidebar({ 
  activeTab, 
  setActiveTab, 
  playlistInfo, 
  onLogout, 
  favoritesCount 
}) {
  const hasVod = playlistInfo?.type === 'xtream';

  return (
    <aside className="sidebar-container glass-panel">
      {/* Brand logo */}
      <div className="sidebar-brand">
        <Radio className="brand-icon glow-text-primary" size={24} />
        <div>
          <span className="brand-title text-digital glow-text-primary">StreamPulse</span>
          <span className="brand-version text-digital">v1.1</span>
        </div>
      </div>

      {/* Playlist Status Info */}
      <div className="playlist-status">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <span className="status-dot online"></span>
          <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', color: 'var(--text-main)', letterSpacing: '0.05em' }}>
            {playlistInfo?.type === 'xtream' ? 'Xtream Portal' : 'M3U Playlist'}
          </span>
        </div>
        <div className="playlist-name" title={playlistInfo?.name || playlistInfo?.credentials?.host}>
          {playlistInfo?.type === 'xtream' 
            ? playlistInfo.credentials.host.replace(/^https?:\/\//, '') 
            : playlistInfo?.name || 'Local File'}
        </div>
        {playlistInfo?.userInfo?.exp_date && (
          <div style={{ fontSize: '10px', color: 'var(--text-dark)', marginTop: '4px' }}>
            Exp: {playlistInfo.userInfo.exp_date === '0' || !playlistInfo.userInfo.exp_date
              ? 'Unlimited'
              : new Date(parseInt(playlistInfo.userInfo.exp_date) * 1000).toLocaleDateString()}
          </div>
        )}
      </div>

      {/* Navigation menu */}
      <nav className="sidebar-menu">
        <button 
          className={`menu-item ${activeTab === 'live' ? 'active' : ''}`}
          onClick={() => setActiveTab('live')}
        >
          <Tv size={18} />
          <span>Live TV</span>
        </button>

        {hasVod && (
          <>
            <button 
              className={`menu-item ${activeTab === 'movies' ? 'active' : ''}`}
              onClick={() => setActiveTab('movies')}
            >
              <Film size={18} />
              <span>Movies VOD</span>
            </button>

            <button 
              className={`menu-item ${activeTab === 'series' ? 'active' : ''}`}
              onClick={() => setActiveTab('series')}
            >
              <Clapperboard size={18} />
              <span>TV Series</span>
            </button>
          </>
        )}

        <button 
          className={`menu-item ${activeTab === 'favorites' ? 'active' : ''}`}
          onClick={() => setActiveTab('favorites')}
        >
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Heart size={18} fill={activeTab === 'favorites' ? 'currentColor' : 'none'} />
            {favoritesCount > 0 && (
              <span className="favorite-count-badge text-digital">{favoritesCount}</span>
            )}
          </div>
          <span>Favorites</span>
        </button>

        <button 
          className={`menu-item ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          <Settings size={18} />
          <span>Settings</span>
        </button>
      </nav>

      {/* Logout button at footer */}
      <div className="sidebar-footer">
        <button className="logout-btn" onClick={onLogout}>
          <LogOut size={16} />
          <span>Disconnect</span>
        </button>
      </div>

      <style>{`
        .sidebar-container {
          width: 240px;
          height: 100%;
          border-radius: 0;
          border-left: none;
          border-top: none;
          border-bottom: none;
          background: var(--bg-sidebar);
          display: flex;
          flex-direction: column;
          padding: 24px 16px;
          flex-shrink: 0;
          z-index: 30;
        }

        .sidebar-brand {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 32px;
          padding-left: 8px;
        }
        .brand-icon {
          color: var(--primary);
        }
        .brand-title {
          font-size: 18px;
          font-weight: 800;
          color: var(--primary);
          display: block;
          line-height: 1.2;
        }
        .brand-version {
          font-size: 9px;
          color: var(--text-dark);
          text-transform: uppercase;
          letter-spacing: 0.1em;
          display: block;
        }

        .playlist-status {
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid var(--border-color);
          border-radius: var(--radius-sm);
          padding: 12px;
          margin-bottom: 24px;
        }
        .status-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          display: inline-block;
        }
        .status-dot.online {
          background: var(--accent);
          box-shadow: 0 0 6px var(--accent);
        }
        .playlist-name {
          font-size: 12px;
          color: var(--text-muted);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-weight: 500;
        }

        .sidebar-menu {
          display: flex;
          flex-direction: column;
          gap: 6px;
          flex: 1;
        }

        .menu-item {
          display: flex;
          align-items: center;
          gap: 12px;
          background: transparent;
          border: none;
          color: var(--text-muted);
          padding: 12px 16px;
          border-radius: var(--radius-sm);
          cursor: pointer;
          font-family: var(--font-sans);
          font-size: 14px;
          font-weight: 500;
          transition: all 0.2s ease;
          text-align: left;
          width: 100%;
        }
        .menu-item:hover {
          background: rgba(255, 255, 255, 0.03);
          color: var(--text-main);
        }
        .menu-item.active {
          background: var(--primary-glow);
          color: var(--primary);
          font-weight: 600;
          border-left: 3px solid var(--primary);
          border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
          padding-left: 13px; /* account for border width */
        }
        
        .favorite-count-badge {
          position: absolute;
          top: -6px;
          right: -8px;
          background: var(--secondary);
          color: #fff;
          font-size: 8px;
          padding: 1px 4px;
          border-radius: 6px;
          font-weight: 800;
          min-width: 12px;
          text-align: center;
          box-shadow: 0 0 6px var(--secondary-glow);
        }

        .sidebar-footer {
          border-top: 1px solid var(--border-color);
          padding-top: 16px;
        }
        .logout-btn {
          display: flex;
          align-items: center;
          gap: 10px;
          background: transparent;
          border: none;
          color: var(--text-dark);
          width: 100%;
          padding: 10px 12px;
          cursor: pointer;
          font-family: var(--font-sans);
          font-size: 13px;
          font-weight: 500;
          transition: all 0.2s ease;
          border-radius: var(--radius-sm);
        }
        .logout-btn:hover {
          color: #f87171;
          background: rgba(239, 68, 68, 0.05);
        }
      `}</style>
    </aside>
  );
}
