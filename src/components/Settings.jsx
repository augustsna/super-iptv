import React from 'react';
import { Sliders, Trash2 } from 'lucide-react';

export default function Settings({ 
  onClearPlaylist, 
  onClearFavorites
}) {
  return (
    <div className="settings-container animate-slide-in">
      <div className="settings-content glass-panel">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '24px', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
          <Sliders size={24} style={{ color: 'var(--primary)' }} />
          <h2 className="text-digital glow-text-primary" style={{ fontSize: '20px', color: 'var(--primary)' }}>Application Settings</h2>
        </div>

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
      `}</style>
    </div>
  );
}
