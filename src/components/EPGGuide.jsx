import React, { useState, useEffect } from 'react';
import { Calendar, Info, RefreshCw, Upload, FileText, AlertCircle } from 'lucide-react';
import { parseXMLTV } from '../utils/parsers';

export default function EPGGuide({ channel, epgData, onEpgLoaded, useProxy, proxyUrl }) {
  const [loading, setLoading] = useState(false);
  const [epgUrlInput, setEpgUrlInput] = useState('http://s1.dnspass.xyz/xmltv.php?username=yaevqytp&password=i1D45f9uCd');
  const [errorMsg, setErrorMsg] = useState('');
  const [currentShow, setCurrentShow] = useState(null);
  const [upcomingShows, setUpcomingShows] = useState([]);
  const [progress, setProgress] = useState(0);
  const [timeRemaining, setTimeRemaining] = useState('');

  // Fetch / parse from URL
  const loadEpgFromUrl = async (e) => {
    if (e) e.preventDefault();
    if (!epgUrlInput) return;

    setLoading(true);
    setErrorMsg('');

    try {
      const fetchUrl = useProxy ? `${proxyUrl}${encodeURIComponent(epgUrlInput)}` : epgUrlInput;
      const response = await fetch(fetchUrl);
      if (!response.ok) throw new Error('Failed to fetch EPG XML. Server returned error.');

      const text = await response.text();
      const parsed = parseXMLTV(text);
      
      if (Object.keys(parsed).length === 0) {
        throw new Error('No program data parsed. Verify this is a valid XMLTV XML file.');
      }

      onEpgLoaded(parsed);
    } catch (err) {
      console.error(err);
      setErrorMsg(`Failed to load EPG: ${err.message}. If this is a CORS block, download the XMLTV file and upload it below.`);
    } finally {
      setLoading(false);
    }
  };

  // Parse from Local File
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setLoading(true);
    setErrorMsg('');

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target.result;
        const parsed = parseXMLTV(text);

        if (Object.keys(parsed).length === 0) {
          throw new Error('No program data parsed. Verify this is a valid XMLTV file.');
        }

        onEpgLoaded(parsed);
      } catch (err) {
        setErrorMsg(err.message);
      } finally {
        setLoading(false);
      }
    };
    reader.onerror = () => {
      setErrorMsg('Failed to read EPG file.');
      setLoading(false);
    };
    reader.readAsText(file);
  };

  // Find programs matching selected channel
  useEffect(() => {
    if (!channel || !epgData || Object.keys(epgData).length === 0) {
      setCurrentShow(null);
      setUpcomingShows([]);
      return;
    }

    // Try finding programs using channel tvg-id, channel name, or id
    const targetKeys = [channel.id, channel.tvgName, channel.name].filter(Boolean);
    let matchedPrograms = null;

    for (const key of targetKeys) {
      if (epgData[key]) {
        matchedPrograms = epgData[key];
        break;
      }
    }

    // Direct search if key contains spaces/casing discrepancies
    if (!matchedPrograms) {
      const epgKeys = Object.keys(epgData);
      const matchedKey = epgKeys.find(k => 
        targetKeys.some(target => k.toLowerCase() === target.toLowerCase() || k.toLowerCase().includes(target.toLowerCase()))
      );
      if (matchedKey) {
        matchedPrograms = epgData[matchedKey];
      }
    }

    if (!matchedPrograms || matchedPrograms.length === 0) {
      setCurrentShow(null);
      setUpcomingShows([]);
      return;
    }

    const now = new Date();
    
    // Find current program
    const current = matchedPrograms.find(prog => prog.start <= now && prog.stop >= now);
    setCurrentShow(current || null);

    // Find all future programs
    const upcoming = matchedPrograms.filter(prog => prog.start > now);
    setUpcomingShows(upcoming.slice(0, 10)); // limit to next 10 shows
  }, [channel, epgData]);

  // Track progress of current show in real-time
  useEffect(() => {
    if (!currentShow) return;

    const updateProgress = () => {
      const now = new Date();
      const start = new Date(currentShow.start);
      const stop = new Date(currentShow.stop);

      const total = stop - start;
      const elapsed = now - start;
      const calcProgress = Math.min(Math.max((elapsed / total) * 100, 0), 100);
      setProgress(calcProgress);

      const diffMs = stop - now;
      if (diffMs <= 0) {
        // Show ended
        setTimeRemaining('Ending now');
        return;
      }

      const diffMins = Math.round(diffMs / 1000 / 60);
      if (diffMins < 60) {
        setTimeRemaining(`${diffMins} min remaining`);
      } else {
        const hrs = Math.floor(diffMins / 60);
        const mins = diffMins % 60;
        setTimeRemaining(`${hrs}h ${mins}m remaining`);
      }
    };

    updateProgress();
    const timer = setInterval(updateProgress, 30000); // update every 30 seconds

    return () => clearInterval(timer);
  }, [currentShow]);

  const formatTime = (date) => {
    return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const hasLoadedEpg = epgData && Object.keys(epgData).length > 0;

  return (
    <div className="epg-container glass-panel">
      <div className="epg-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Calendar size={18} style={{ color: 'var(--primary)' }} />
          <h3 style={{ fontSize: '15px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            TV Guide
          </h3>
        </div>
        {hasLoadedEpg && (
          <span className="badge badge-hd text-digital">
            EPG Connected ({Object.keys(epgData).length} Chs)
          </span>
        )}
      </div>

      <div className="epg-body">
        {!hasLoadedEpg ? (
          // EPG Loading portal
          <div className="epg-setup-box">
            <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '16px', textAlign: 'center' }}>
              No EPG data loaded. Set up XMLTV guide to display schedules:
            </p>

            {errorMsg && (
              <div style={{
                display: 'flex',
                gap: '8px',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.2)',
                borderRadius: '6px',
                padding: '10px',
                marginBottom: '12px',
                color: '#f87171',
                fontSize: '12px',
              }}>
                <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '1px' }} />
                <span>{errorMsg}</span>
              </div>
            )}

            {loading ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', padding: '16px' }}>
                <RefreshCw size={20} className="spin-animation" style={{ color: 'var(--primary)' }} />
                <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Parsing EPG XML...</span>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {/* XMLTV url form */}
                <form onSubmit={loadEpgFromUrl} style={{ display: 'flex', gap: '8px' }}>
                  <input 
                    type="url" 
                    className="input-field" 
                    value={epgUrlInput} 
                    onChange={e => setEpgUrlInput(e.target.value)} 
                    placeholder="XMLTV URL" 
                    style={{ padding: '8px 12px', fontSize: '13px' }}
                  />
                  <button type="submit" className="btn btn-primary" style={{ padding: '8px 16px', fontSize: '13px' }}>
                    Load
                  </button>
                </form>

                <div style={{ textAlign: 'center', color: 'var(--text-dark)', fontSize: '11px' }}>— OR —</div>

                {/* Local file upload */}
                <div className="epg-file-upload">
                  <Upload size={16} style={{ marginRight: '6px' }} />
                  <span>Upload EPG .xml File</span>
                  <input 
                    type="file" 
                    accept=".xml,.gz" 
                    onChange={handleFileUpload} 
                    style={{ position: 'absolute', inset: 0, opacity: 0, cursor: 'pointer' }}
                  />
                </div>
              </div>
            )}
          </div>
        ) : !channel ? (
          <div className="epg-empty-state">
            <Info size={24} style={{ color: 'var(--text-dark)', marginBottom: '8px' }} />
            <p>Select a channel to check streaming guides</p>
          </div>
        ) : currentShow ? (
          // Schedule is matched
          <div className="epg-schedule-view">
            {/* Current program details */}
            <div className="current-program">
              <div className="current-program-header">
                <span className="current-title">{currentShow.title}</span>
                <span className="current-time-badge text-digital">{timeRemaining}</span>
              </div>
              
              <div className="progress-bar-container">
                <div className="progress-bar" style={{ width: `${progress}%` }}></div>
              </div>

              <div className="current-time-duration text-digital">
                <span>{formatTime(currentShow.start)}</span>
                <span>{formatTime(currentShow.stop)}</span>
              </div>

              {currentShow.desc && (
                <p className="current-desc">{currentShow.desc}</p>
              )}
            </div>

            {/* Timetable of future programs */}
            {upcomingShows.length > 0 && (
              <div className="upcoming-list-container">
                <h4 style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-dark)', fontWeight: '700', marginBottom: '8px', letterSpacing: '0.05em' }}>
                  Next Up
                </h4>
                <div className="upcoming-shows-scroll">
                  {upcomingShows.map((prog, index) => (
                    <div key={index} className="upcoming-show-item">
                      <div className="upcoming-time text-digital">
                        {formatTime(prog.start)}
                      </div>
                      <div className="upcoming-details">
                        <div className="upcoming-title">{prog.title}</div>
                        {prog.desc && <div className="upcoming-desc">{prog.desc}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          // EPG loaded but channel has no scheduling details
          <div className="epg-empty-state">
            <Info size={24} style={{ color: 'var(--text-dark)', marginBottom: '8px' }} />
            <p>No program details available for this channel</p>
            <span style={{ fontSize: '11px', color: 'var(--text-dark)', marginTop: '4px' }}>
              ID matched: "{channel.id || channel.name}"
            </span>
          </div>
        )}
      </div>

      <style>{`
        .epg-container {
          display: flex;
          flex-direction: column;
          height: 100%;
          min-height: 250px;
          background: var(--bg-card);
          border-radius: var(--radius-md);
          overflow: hidden;
        }
        
        .epg-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 14px 16px;
          border-bottom: 1px solid var(--border-color);
        }

        .epg-body {
          flex: 1;
          display: flex;
          flex-direction: column;
          padding: 16px;
          overflow: hidden;
        }

        .epg-setup-box {
          display: flex;
          flex-direction: column;
          justify-content: center;
          height: 100%;
        }

        .epg-file-upload {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
          border: 1px dashed var(--border-color);
          border-radius: var(--radius-sm);
          padding: 10px;
          font-size: 13px;
          color: var(--text-muted);
          background: rgba(255,255,255,0.01);
          cursor: pointer;
          transition: all 0.2s ease;
        }
        .epg-file-upload:hover {
          border-color: var(--primary);
          background: var(--primary-glow);
          color: var(--primary);
        }

        .epg-empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          flex: 1;
          text-align: center;
          color: var(--text-muted);
          font-size: 13px;
        }

        .epg-schedule-view {
          display: flex;
          flex-direction: column;
          height: 100%;
          overflow: hidden;
          gap: 16px;
        }

        .current-program {
          background: rgba(255,255,255,0.02);
          border: 1px solid var(--border-color);
          border-radius: var(--radius-sm);
          padding: 12px;
        }
        .current-program-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 12px;
          margin-bottom: 8px;
        }
        .current-title {
          font-size: 14px;
          font-weight: 600;
          color: #fff;
        }
        .current-time-badge {
          font-size: 10px;
          color: var(--accent);
          background: var(--accent-glow);
          border: 1px solid rgba(5,255,197,0.2);
          padding: 1px 6px;
          border-radius: 4px;
          white-space: nowrap;
        }
        
        .progress-bar-container {
          width: 100%;
          height: 4px;
          background: rgba(255,255,255,0.1);
          border-radius: 2px;
          overflow: hidden;
          margin-bottom: 6px;
        }
        .progress-bar {
          height: 100%;
          background: linear-gradient(to right, var(--primary), var(--accent));
          box-shadow: 0 0 6px var(--primary);
        }
        
        .current-time-duration {
          display: flex;
          justify-content: space-between;
          font-size: 10px;
          color: var(--text-dark);
          margin-bottom: 8px;
        }
        
        .current-desc {
          font-size: 12px;
          color: var(--text-muted);
          line-height: 1.4;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .upcoming-list-container {
          flex: 1;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .upcoming-shows-scroll {
          flex: 1;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 8px;
          padding-right: 4px;
        }

        .upcoming-show-item {
          display: flex;
          gap: 12px;
          padding: 8px;
          border-radius: 6px;
          background: rgba(255,255,255,0.01);
          border-bottom: 1px solid rgba(255,255,255,0.02);
          transition: background 0.2s ease;
        }
        .upcoming-show-item:hover {
          background: rgba(255,255,255,0.03);
        }
        
        .upcoming-time {
          font-size: 11px;
          color: var(--primary);
          font-weight: 600;
          white-space: nowrap;
        }
        .upcoming-details {
          flex: 1;
        }
        .upcoming-title {
          font-size: 12px;
          font-weight: 500;
          color: var(--text-main);
          margin-bottom: 2px;
        }
        .upcoming-desc {
          font-size: 11px;
          color: var(--text-dark);
          line-height: 1.3;
          display: -webkit-box;
          -webkit-line-clamp: 1;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>
    </div>
  );
}
