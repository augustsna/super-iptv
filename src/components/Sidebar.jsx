import React from 'react';
import { Tv, Film, Clapperboard, Heart, Settings, LogOut, Radio, Clock } from 'lucide-react';

function getExpiryInfo(expDate) {
  if (!expDate || expDate === '0') return { label: 'Unlimited', remaining: null, color: 'var(--accent)' };
  const expMs = parseInt(expDate, 10) * 1000;
  const now = Date.now();
  const diff = expMs - now;
  const dateStr = new Date(expMs).toLocaleDateString();
  if (diff <= 0) return { label: `Expired (${dateStr})`, remaining: 'Expired', color: '#f87171' };
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  let remaining;
  if (days > 0) remaining = `${days}d ${hours}h ${mins}m remaining`;
  else if (hours > 0) remaining = `${hours}h ${mins}m remaining`;
  else remaining = `${mins}m remaining`;
  const color = days <= 1 ? '#f87171' : days <= 7 ? '#f59e0b' : 'var(--accent)';
  return { label: dateStr, remaining, color };
}

export default function Sidebar({ 
  activeTab, 
  setActiveTab, 
  playlistInfo, 
  onLogout,
  onHome,
  favoritesCount 
}) {
  const hasVod = playlistInfo?.type === 'xtream';
  const expiry = getExpiryInfo(playlistInfo?.userInfo?.exp_date);

  return (
    <aside className="sidebar-container glass-panel">
      {/* Brand logo */}
      <button className="sidebar-brand" onClick={onHome} title="Go to Home">
        <Radio className="brand-icon glow-text-primary" size={24} />
        <span className="brand-title text-digital glow-text-primary">Super Stream</span>
      </button>

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

      </nav>

      {/* Logout button at footer */}
      <div className="sidebar-footer">
        {/* Settings button */}
        <button
          className={`menu-item settings-footer-btn ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          <Settings size={18} />
          <span>Settings</span>
        </button>

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
            <div style={{ marginTop: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: 'var(--text-dark)' }}>
                <Clock size={10} />
                <span>Expires: {expiry.label}</span>
              </div>
              {expiry.remaining && (
                <div style={{ fontSize: '10px', fontWeight: '600', color: expiry.color, marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: expiry.color, display: 'inline-block', boxShadow: `0 0 4px ${expiry.color}` }}></span>
                  {expiry.remaining}
                </div>
              )}
            </div>
          )}
        </div>

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
          padding: 8px;
          background: transparent;
          border: none;
          cursor: pointer;
          border-radius: var(--radius-sm);
          transition: opacity 0.2s ease;
          width: 100%;
          text-align: left;
        }
        .sidebar-brand:hover {
          opacity: 0.8;
        }
        .brand-icon {
          color: var(--primary);
          flex-shrink: 0;
        }
        .brand-title {
          font-size: 18px;
          font-weight: 800;
          color: var(--primary);
          line-height: 1.2;
        }

        .playlist-status {
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid var(--border-color);
          border-radius: var(--radius-sm);
          padding: 12px;
          margin-bottom: 12px;
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
        .settings-footer-btn {
          margin-bottom: 8px;
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
