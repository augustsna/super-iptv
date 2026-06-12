import React, { useEffect, useRef, useState } from 'react';
import Hls from 'hls.js';
import mpegts from 'mpegts.js';
import { Play, Pause, Volume2, VolumeX, Maximize, Minimize, RefreshCw, BarChart2, Tv, Shrink } from 'lucide-react';

export default function Player({ channel }) {
  const videoRef = useRef(null);
  const hlsRef = useRef(null);
  const mpegtsRef = useRef(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(0.8);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [aspectRatio, setAspectRatio] = useState('fit'); // fit, fill, stretch, 16-9, 4-3
  const [showStats, setShowStats] = useState(false);
  const [stats, setStats] = useState({ format: 'None', resolution: '0x0', fps: 0, bitrate: 0 });
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Handle stream initialization
  useEffect(() => {
    if (!channel || !channel.url) return;
    
    initPlayer();

    return () => {
      destroyPlayer();
    };
  }, [channel]);

  const destroyPlayer = () => {
    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }
    if (mpegtsRef.current) {
      mpegtsRef.current.destroy();
      mpegtsRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.src = '';
      videoRef.current.load();
    }
    setIsPlaying(false);
    setLoading(false);
    setErrorMsg('');
  };

  const initPlayer = () => {
    destroyPlayer();
    setLoading(true);

    const video = videoRef.current;
    if (!video) return;

    video.volume = isMuted ? 0 : volume;

    const url = channel.url;
    
    // Check url extension and determine type
    const isHls = url.includes('.m3u8') || channel.type === 'hls';
    const isTs = url.includes('.ts') || url.includes('output=ts') || channel.url.endsWith('.ts');

    console.log(`Initializing play source: ${url} (HLS: ${isHls}, TS: ${isTs})`);

    if (isHls) {
      setStats(prev => ({ ...prev, format: 'HLS (.m3u8)' }));
      if (Hls.isSupported()) {
        const hls = new Hls({
          enableWorker: true,
          lowLatencyMode: true,
        });
        hlsRef.current = hls;
        hls.loadSource(url);
        hls.attachMedia(video);
        
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          video.play().catch(handlePlayError);
          setLoading(false);
        });

        hls.on(Hls.Events.ERROR, (event, data) => {
          console.error('HLS Error:', data);
          if (data.fatal) {
            switch (data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                setErrorMsg('Network error playing stream. Try reloading or checking your connection.');
                hls.startLoad();
                break;
              case Hls.ErrorTypes.MEDIA_ERROR:
                setErrorMsg('Media parsing error. Recovering...');
                hls.recoverMediaError();
                break;
              default:
                setErrorMsg('Fatal stream playback error.');
                destroyPlayer();
                break;
            }
          }
        });
      } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        // Native HLS (Safari)
        video.src = url;
        video.addEventListener('loadedmetadata', () => {
          video.play().catch(handlePlayError);
          setLoading(false);
        });
      } else {
        setErrorMsg('HLS playback is not supported in this browser.');
        setLoading(false);
      }
    } else if (isTs && mpegts.isSupported()) {
      setStats(prev => ({ ...prev, format: 'MPEG-TS (.ts)' }));
      try {
        const mpegtsPlayer = mpegts.createPlayer({
          type: 'mpegts',
          isLive: true,
          url: url,
        }, {
          enableWorker: true,
          enableStashBuffer: false,
          liveBufferLatencyChaser: true,
        });

        mpegtsRef.current = mpegtsPlayer;
        mpegtsPlayer.attachMediaElement(video);
        mpegtsPlayer.load();
        
        mpegtsPlayer.play()
          .then(() => {
            setLoading(false);
          })
          .catch(err => {
            handlePlayError(err);
          });

        mpegtsPlayer.on(mpegts.Events.ERROR, (type, detail, info) => {
          console.error('MPEG-TS Error:', type, detail, info);
          setErrorMsg(`Playback error: ${detail}. The stream might be offline or CORS-blocked.`);
          setLoading(false);
        });
      } catch (err) {
        setErrorMsg(`Failed to initialize TS decoder: ${err.message}`);
        setLoading(false);
      }
    } else {
      // Direct Mp4 / WebM / Generic Playback
      setStats(prev => ({ ...prev, format: 'Direct Video Source' }));
      video.src = url;
      video.load();
      video.play()
        .then(() => {
          setLoading(false);
        })
        .catch(err => {
          handlePlayError(err);
          setLoading(false);
        });
    }
  };

  const handlePlayError = (err) => {
    console.error('Play error caught:', err);
    setIsPlaying(false);
    setErrorMsg('Stream could not be played. This is common due to Mixed Content (HTTP on HTTPS site) or CORS blocking. Check Settings to apply a proxy.');
  };

  // Listen to video element state changes
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    const onPlaying = () => {
      setIsPlaying(true);
      setLoading(false);
      setErrorMsg('');
    };
    const onWaiting = () => setLoading(true);

    video.addEventListener('play', onPlay);
    video.addEventListener('pause', onPause);
    video.addEventListener('playing', onPlaying);
    video.addEventListener('waiting', onWaiting);

    return () => {
      video.removeEventListener('play', onPlay);
      video.removeEventListener('pause', onPause);
      video.removeEventListener('playing', onPlaying);
      video.removeEventListener('waiting', onWaiting);
    };
  }, []);

  // Update stats in loop
  useEffect(() => {
    let intervalId;
    if (showStats && isPlaying && videoRef.current) {
      intervalId = setInterval(() => {
        const video = videoRef.current;
        if (!video) return;
        
        let width = video.videoWidth || 0;
        let height = video.videoHeight || 0;
        
        let currentFps = 0;
        let decodedFrames = 0;

        // Try getting video stats
        if (video.getVideoPlaybackQuality) {
          const qual = video.getVideoPlaybackQuality();
          decodedFrames = qual.totalVideoFrames;
        } else if (video.webkitDecodedFrameCount) {
          decodedFrames = video.webkitDecodedFrameCount;
        }

        setStats(prev => ({
          ...prev,
          resolution: `${width}x${height}`,
          fps: isNaN(decodedFrames) ? 0 : Math.round(decodedFrames / (video.currentTime || 1)) % 60 || 30,
        }));
      }, 2000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [showStats, isPlaying]);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
    } else {
      videoRef.current.play().catch(handlePlayError);
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    videoRef.current.muted = nextMuted;
  };

  const handleVolumeChange = (e) => {
    const val = parseFloat(e.target.value);
    setVolume(val);
    setIsMuted(val === 0);
    if (videoRef.current) {
      videoRef.current.volume = val;
      videoRef.current.muted = val === 0;
    }
  };

  const toggleFullscreen = () => {
    const container = videoRef.current?.parentElement;
    if (!container) return;

    if (!document.fullscreenElement) {
      container.requestFullscreen().then(() => {
        setIsFullscreen(true);
      }).catch(err => {
        console.error('Fullscreen request error:', err);
      });
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  const togglePictureInPicture = async () => {
    const video = videoRef.current;
    if (!video || !document.pictureInPictureEnabled) return;

    try {
      if (document.pictureInPictureElement) {
        await document.exitPictureInPicture();
      } else {
        await video.requestPictureInPicture();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const getAspectClass = () => {
    switch (aspectRatio) {
      case 'fill': return 'video-aspect-fill';
      case 'stretch': return 'video-aspect-stretch';
      case '16-9': return 'video-aspect-16-9';
      case '4-3': return 'video-aspect-4-3';
      case 'fit':
      default:
        return 'video-aspect-fit';
    }
  };

  if (!channel) {
    return (
      <div className="player-empty-container glass-panel">
        <Tv size={48} style={{ color: 'var(--text-dark)', marginBottom: '16px' }} />
        <h3 style={{ color: 'var(--text-muted)' }}>Select a channel to start streaming</h3>
        <p style={{ color: 'var(--text-dark)', fontSize: '13px', marginTop: '4px' }}>Browse categories in the sidebar</p>
      </div>
    );
  }

  return (
    <div className="player-wrapper glass-panel">
      {/* Video Container */}
      <div className={`video-container-box`}>
        <video 
          ref={videoRef}
          className={`video-element ${getAspectClass()}`}
          playsInline
        />

        {/* Loading Spinner */}
        {loading && (
          <div className="spinner-overlay">
            <RefreshCw className="spin-animation" size={40} style={{ color: 'var(--primary)' }} />
          </div>
        )}

        {/* Error Overlay */}
        {errorMsg && (
          <div className="error-overlay">
            <p className="error-title">Playback Error</p>
            <p className="error-desc">{errorMsg}</p>
            <button className="btn btn-primary btn-sm" onClick={initPlayer} style={{ marginTop: '12px', padding: '8px 16px', fontSize: '12px' }}>
              <RefreshCw size={12} /> Retry Playback
            </button>
          </div>
        )}

        {/* Stats overlay */}
        {showStats && (
          <div className="stats-box text-digital">
            <div>Format: <span style={{ color: 'var(--primary)' }}>{stats.format}</span></div>
            <div>Resolution: <span style={{ color: 'var(--accent)' }}>{stats.resolution}</span></div>
            <div>Estimated FPS: <span style={{ color: 'var(--accent)' }}>{stats.fps}</span></div>
            <div>Connection: <span style={{ color: '#34d399' }}>Active</span></div>
          </div>
        )}

        {/* Custom Overlay Controls */}
        <div className="player-controls-overlay">
          {/* Top Header info */}
          <div className="overlay-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              {channel.logo && <img src={channel.logo} alt="" style={{ height: '32px', width: '32px', objectFit: 'contain', borderRadius: '4px', background: 'rgba(255,255,255,0.05)' }} onError={e => e.target.style.display = 'none'} />}
              <div>
                <h4 style={{ color: '#fff', fontSize: '15px', fontWeight: '600' }}>{channel.name}</h4>
                <p style={{ color: 'var(--text-muted)', fontSize: '11px' }}>{channel.category}</p>
              </div>
            </div>
            <button className={`control-btn ${showStats ? 'active' : ''}`} onClick={() => setShowStats(!showStats)} title="Toggle Stats">
              <BarChart2 size={16} />
            </button>
          </div>

          {/* Bottom Control Bar */}
          <div className="overlay-footer">
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: 1 }}>
              <button className="control-btn play-btn" onClick={togglePlay}>
                {isPlaying ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" />}
              </button>

              <button className="control-btn" onClick={initPlayer} title="Reload stream">
                <RefreshCw size={16} />
              </button>

              {/* Volume */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button className="control-btn" onClick={toggleMute}>
                  {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
                </button>
                <input 
                  type="range" 
                  min="0" 
                  max="1" 
                  step="0.05" 
                  value={isMuted ? 0 : volume} 
                  onChange={handleVolumeChange} 
                  className="volume-slider"
                />
              </div>

              {/* Live badge */}
              <span className="badge badge-live text-digital">
                ● Live
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              {/* Aspect Ratio select */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', padding: '2px' }}>
                {['fit', 'fill', 'stretch'].map((aspect) => (
                  <button 
                    key={aspect}
                    className={`aspect-select-btn ${aspectRatio === aspect ? 'active' : ''}`}
                    onClick={() => setAspectRatio(aspect)}
                    style={{ fontSize: '10px', textTransform: 'uppercase', border: 'none', background: 'transparent', padding: '4px 6px', color: aspectRatio === aspect ? 'var(--primary)' : 'var(--text-muted)', cursor: 'pointer', fontWeight: '600' }}
                  >
                    {aspect}
                  </button>
                ))}
              </div>

              {document.pictureInPictureEnabled && (
                <button className="control-btn" onClick={togglePictureInPicture} title="Picture in Picture">
                  <Shrink size={16} />
                </button>
              )}

              <button className="control-btn" onClick={toggleFullscreen} title="Toggle Fullscreen">
                {isFullscreen ? <Minimize size={18} /> : <Maximize size={18} />}
              </button>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        .player-wrapper {
          display: flex;
          flex-direction: column;
          background: #000;
          overflow: hidden;
          position: relative;
          height: 100%;
          border-radius: var(--radius-md);
        }
        .player-empty-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          border-radius: var(--radius-md);
          text-align: center;
          background: rgba(0, 0, 0, 0.3);
          padding: 24px;
        }
        .video-container-box {
          position: relative;
          width: 100%;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          overflow: hidden;
          background: #000;
        }
        .video-element {
          width: 100%;
          height: 100%;
          object-fit: contain;
          outline: none;
        }
        
        /* Aspect Ratio Styles */
        .video-aspect-fit {
          object-fit: contain;
        }
        .video-aspect-fill {
          object-fit: cover;
        }
        .video-aspect-stretch {
          object-fit: fill;
        }
        .video-aspect-16-9 {
          aspect-ratio: 16/9;
          height: auto;
          max-height: 100%;
        }
        .video-aspect-4-3 {
          aspect-ratio: 4/3;
          height: auto;
          max-height: 100%;
        }

        .spinner-overlay {
          position: absolute;
          inset: 0;
          background: rgba(0,0,0,0.6);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 10;
        }
        .error-overlay {
          position: absolute;
          inset: 0;
          background: rgba(10, 10, 15, 0.9);
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          z-index: 12;
          padding: 32px;
          text-align: center;
        }
        .error-title {
          color: #ef4444;
          font-weight: 700;
          font-size: 18px;
          margin-bottom: 8px;
        }
        .error-desc {
          color: var(--text-muted);
          font-size: 13px;
          max-width: 450px;
          line-height: 1.5;
        }
        
        .stats-box {
          position: absolute;
          top: 72px;
          left: 16px;
          background: rgba(0,0,0,0.75);
          border: 1px solid var(--border-color);
          border-radius: 6px;
          padding: 8px 12px;
          font-size: 10px;
          color: var(--text-muted);
          z-index: 15;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        /* Controls Hover Overlay */
        .player-controls-overlay {
          position: absolute;
          inset: 0;
          background: linear-gradient(to bottom, rgba(0,0,0,0.7) 0%, transparent 20%, transparent 80%, rgba(0,0,0,0.8) 100%);
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          padding: 16px;
          opacity: 0;
          transition: opacity 0.3s ease;
          z-index: 20;
        }
        .video-container-box:hover .player-controls-overlay {
          opacity: 1;
        }
        
        .overlay-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .overlay-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .control-btn {
          background: transparent;
          border: none;
          color: #fff;
          cursor: pointer;
          opacity: 0.8;
          transition: all 0.2s ease;
          padding: 6px;
          border-radius: 4px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .control-btn:hover {
          opacity: 1;
          color: var(--primary);
          background: rgba(255,255,255,0.08);
        }
        .control-btn.active {
          color: var(--primary);
          background: var(--primary-glow);
          opacity: 1;
        }
        .play-btn:hover {
          color: var(--primary);
          transform: scale(1.1);
        }
        
        .volume-slider {
          width: 70px;
          height: 4px;
          accent-color: var(--primary);
          cursor: pointer;
          background: rgba(255,255,255,0.2);
          border-radius: 2px;
          outline: none;
        }
        
        .aspect-select-btn {
          transition: all 0.2s ease;
          border-radius: 2px;
        }
        .aspect-select-btn:hover {
          background: rgba(255,255,255,0.1) !important;
        }
        .aspect-select-btn.active {
          background: rgba(255,255,255,0.15) !important;
        }
      `}</style>
    </div>
  );
}
