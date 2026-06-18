import React from 'react';
import { Sliders, Trash2, Radio, Clock, Wifi, Layers } from 'lucide-react';

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

export default function Settings({ 
  onClearPlaylist, 
  onClearFavorites,
  playlistInfo,
  loadStep,
  handleLoadStepChange,
  customLoadValue,
  handleCustomValueChange,
  selectValue,
  xtreamStreamFormat,
  onStreamFormatChange
}) {
  const expiry = getExpiryInfo(playlistInfo?.userInfo?.exp_date);
  const hostDisplay = playlistInfo?.type === 'xtream'
    ? playlistInfo.credentials.host.replace(/^https?:\/\//, '')
    : playlistInfo?.name || 'Local File';
  const typeLabel = playlistInfo?.type === 'xtream' ? 'Xtream Portal' : 'M3U Playlist';

  return (
    <div className="settings-container animate-slide-in">
      <div className="settings-content glass-panel">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '24px', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
          <Sliders size={24} style={{ color: 'var(--primary)' }} />
          <h2 style={{ fontSize: '20px', color: 'var(--primary)', fontFamily: 'var(--font-sans)', fontWeight: '700', letterSpacing: '-0.01em' }}>Application Settings</h2>
        </div>

        {/* CONNECTION INFO */}
        {playlistInfo && (
          <section className="settings-section">
            <div className="section-title">
              <Wifi size={18} />
              <span>Active Connection</span>
            </div>
            <div className="section-body">
              <div className="connection-card">
                {/* Type + status */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                  <span className="conn-dot"></span>
                  <span style={{ fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--primary)' }}>
                    {typeLabel}
                  </span>
                  <span style={{ marginLeft: 'auto', fontSize: '10px', color: 'var(--accent)', fontWeight: '600' }}>● Live</span>
                </div>

                {/* Host */}
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ fontSize: '10px', color: 'var(--text-dark)', marginBottom: '2px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Host / Source</div>
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: '500', wordBreak: 'break-all' }}>{hostDisplay}</div>
                </div>

                {/* Expiry */}
                {playlistInfo?.userInfo?.exp_date ? (
                  <div>
                    <div style={{ fontSize: '10px', color: 'var(--text-dark)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={10} />
                      <span>Subscription Expiry</span>
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: '500', marginBottom: '4px' }}>
                      {expiry.label}
                    </div>
                    {expiry.remaining && (
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: '700', color: expiry.color, background: `${expiry.color}18`, border: `1px solid ${expiry.color}44`, borderRadius: '20px', padding: '3px 10px' }}>
                        <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: expiry.color, display: 'inline-block', boxShadow: `0 0 5px ${expiry.color}` }}></span>
                        {expiry.remaining}
                      </div>
                    )}
                    {!expiry.remaining && (
                      <div style={{ fontSize: '12px', color: 'var(--accent)', fontWeight: '600' }}>No expiry limit</div>
                    )}
                  </div>
                ) : (
                  <div style={{ fontSize: '12px', color: 'var(--text-dark)' }}>No expiry information available</div>
                )}

                {/* Connections */}
                {playlistInfo?.userInfo?.max_connections !== undefined && (
                  <div style={{ marginTop: '12px' }}>
                    <div style={{ fontSize: '10px', color: 'var(--text-dark)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Wifi size={10} />
                      <span>Connections (Active / Max)</span>
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: '500' }}>
                      <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>{playlistInfo.userInfo.active_cons || 0}</span> / {playlistInfo.userInfo.max_connections || 'Unlimited'}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* BATCH LOADING LIMITS */}
        <section className="settings-section">
          <div className="section-title">
            <Layers size={18} />
            <span>Stream Loading &amp; Batching</span>
          </div>
          <div className="section-body">
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-dark)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Load Limit / Batch Size</span>
                <select
                  value={selectValue}
                  onChange={e => handleLoadStepChange(e.target.value)}
                  className="settings-select"
                >
                  <option value="50">50 items</option>
                  <option value="100">100 items</option>
                  <option value="200">200 items</option>
                  <option value="500">500 items</option>
                  <option value="1000">1000 items</option>
                  <option value="custom">Custom...</option>
                  <option value="all">Show All</option>
                </select>
              </div>

              {selectValue === 'custom' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '11px', color: 'var(--text-dark)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Custom Amount</span>
                  <input
                    type="number"
                    min="1"
                    value={customLoadValue}
                    onChange={e => handleCustomValueChange(e.target.value)}
                    className="settings-input"
                    placeholder="e.g. 150"
                  />
                </div>
              )}
            </div>
            <span style={{ display: 'block', fontSize: '11px', color: 'var(--text-dark)', marginTop: '8px' }}>
              Controls the number of channels/VOD items loaded per page to optimize scrolling performance on mobile and desktop devices.
            </span>
          </div>
        </section>

        {/* STREAM FORMAT SELECTION */}
        {playlistInfo?.type === 'xtream' && (
          <section className="settings-section">
            <div className="section-title">
              <Radio size={18} />
              <span>Live TV Stream Format</span>
            </div>
            <div className="section-body">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-dark)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Streaming Protocol / Extension</span>
                <select
                  value={xtreamStreamFormat}
                  onChange={e => onStreamFormatChange(e.target.value)}
                  className="settings-select"
                  style={{ width: '160px' }}
                >
                  <option value="ts">MPEG-TS (.ts)</option>
                  <option value="m3u8">HLS (.m3u8)</option>
                </select>
              </div>
              <span style={{ display: 'block', fontSize: '11px', color: 'var(--text-dark)', marginTop: '8px' }}>
                Note: HLS (.m3u8) streams allow your browser to decode and display Closed Captions (CC), but may take slightly longer to buffer initially. MPEG-TS (.ts) streams buffer faster but do not support browser-based captions.
              </span>
            </div>
          </section>
        )}

        {/* DATA MANAGEMENT */}
        <section className="settings-section">
          <div className="section-title" style={{ color: '#ef4444' }}>
            <Trash2 size={18} />
            <span>Cache &amp; Data Management</span>
          </div>
          <div className="section-body" style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
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

        .connection-card {
          background: rgba(0, 240, 255, 0.03);
          border: 1px solid rgba(0, 240, 255, 0.12);
          border-radius: var(--radius-sm);
          padding: 16px 20px;
          max-width: 420px;
        }
        .conn-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: var(--accent);
          box-shadow: 0 0 6px var(--accent);
          display: inline-block;
          flex-shrink: 0;
        }

        .settings-select {
          background: rgba(255,255,255,0.03);
          border: 1px solid var(--border-color);
          color: var(--text-main);
          border-radius: var(--radius-sm);
          padding: 8px 12px;
          outline: none;
          font-family: var(--font-sans);
          font-size: 13px;
          cursor: pointer;
          min-width: 150px;
          transition: all 0.2s ease;
        }
        .settings-select:hover {
          background: rgba(255,255,255,0.06);
          border-color: rgba(255,255,255,0.25);
        }
        .settings-select:focus {
          border-color: var(--primary);
          box-shadow: 0 0 6px var(--primary-glow);
        }
        .settings-select option {
          background: #0e111a;
          color: #fff;
        }
        .settings-input {
          background: rgba(255,255,255,0.03);
          border: 1px solid var(--border-color);
          color: #fff;
          border-radius: var(--radius-sm);
          padding: 8px 12px;
          outline: none;
          font-family: var(--font-sans);
          font-size: 13px;
          width: 100px;
          transition: all 0.2s ease;
        }
        .settings-input:focus {
          border-color: var(--primary);
          box-shadow: 0 0 6px var(--primary-glow);
        }
      `}</style>
    </div>
  );
}
