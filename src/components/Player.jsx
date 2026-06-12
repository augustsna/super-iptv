import React, { useEffect, useRef, useState } from 'react';
import Hls from 'hls.js';
import mpegts from 'mpegts.js';
import { Play, Pause, Volume2, VolumeX, Maximize, Minimize, RefreshCw, BarChart2, Tv, Shrink } from 'lucide-react';

export default function Player({ channel }) {
  const videoRef = useRef(null);
  const hlsRef = useRef(null);
  const mpegtsRef = useRef(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(() => {
    const saved = localStorage.getItem('superstream_volume');
    return saved !== null ? parseFloat(saved) : 1;
  });
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const aspectRatio = 'fit';
  const [showStats, setShowStats] = useState(false);
  const [stats, setStats] = useState({ format: 'None', resolution: '0x0', fps: 0, bitrate: 0 });
  const [loading, setLoading] = useState(false);
  const [showSpinner, setShowSpinner] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [isMobile, setIsMobile] = useState(() => window.innerWidth <= 768);
  const [showControls, setShowControls] = useState(true);
  const controlsTimerRef = useRef(null);
  const isDestroyingRef = useRef(false);

  const [badges, setBadges] = useState({
    fps: '',
    resolution: '',
    videoCodec: '',
    audioChannels: '',
    audioCodec: ''
  });

  const resetBadges = () => {
    setBadges({
      fps: '',
      resolution: '',
      videoCodec: '',
      audioChannels: '',
      audioCodec: ''
    });
  };

  const [dismissAudioWarning, setDismissAudioWarning] = useState(false);
  const [codecUnsupported, setCodecUnsupported] = useState(false);

  useEffect(() => {
    if (badges.audioCodec) {
      const codec = badges.audioCodec.toLowerCase();
      if (codec === 'ac3' || codec === 'eac3') {
        const video = document.createElement('video');
        const mime = codec === 'ac3' ? 'audio/mp4; codecs="ac-3"' : 'audio/mp4; codecs="ec-3"';
        const canPlay = video.canPlayType(mime);
        const supported = canPlay === 'probably' || canPlay === 'maybe';
        setCodecUnsupported(!supported);
      } else {
        setCodecUnsupported(false);
      }
    } else {
      setCodecUnsupported(false);
    }
  }, [badges.audioCodec]);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Debounce the loading spinner to prevent it from flashing during rapid micro-stalls
  // while actively playing. Show it immediately on initial channel switch.
  useEffect(() => {
    let timer;
    if (loading) {
      if (isPlaying) {
        // Debounce showing spinner during active playback to prevent flickering
        timer = setTimeout(() => {
          setShowSpinner(true);
        }, 350);
      } else {
        // Show immediately during initial load / channel switch
        setShowSpinner(true);
      }
    } else {
      setShowSpinner(false);
    }
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [loading, isPlaying]);

  // Handle stream initialization
  useEffect(() => {
    if (!channel || !channel.url) return;

    initPlayer();

    return () => {
      destroyPlayer();
    };
  }, [channel]);

  const destroyPlayer = () => {
    isDestroyingRef.current = true;
    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }
    if (mpegtsRef.current) {
      mpegtsRef.current.destroy();
      mpegtsRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.removeAttribute('src');
      // Do NOT call video.load() here — it triggers onWaiting and races with re-init
    }
    setIsPlaying(false);
    setLoading(false);
    setErrorMsg('');
    resetBadges();
    setDismissAudioWarning(false);
    setCodecUnsupported(false);
  };

  const updateHlsBadges = (level) => {
    if (!level) return;
    let videoCodec = '';
    let audioCodec = '';

    if (level.attrs && level.attrs.CODECS) {
      const codecs = level.attrs.CODECS.split(',');
      codecs.forEach(c => {
        const codecStr = c.trim().toLowerCase();
        if (codecStr.startsWith('avc') || codecStr.startsWith('h264')) {
          videoCodec = 'h264';
        } else if (codecStr.startsWith('hvc') || codecStr.startsWith('hev') || codecStr.startsWith('h265')) {
          videoCodec = 'hevc';
        } else if (codecStr.startsWith('mp4a') || codecStr.startsWith('aac')) {
          audioCodec = 'aac';
        } else if (codecStr.startsWith('ac-3') || codecStr.startsWith('ac3')) {
          audioCodec = 'ac3';
        } else if (codecStr.startsWith('ec-3') || codecStr.startsWith('eac3')) {
          audioCodec = 'eac3';
        }
      });
    }

    if (!videoCodec && level.videoCodec) {
      const v = level.videoCodec.toLowerCase();
      if (v.includes('avc') || v.includes('h264')) videoCodec = 'h264';
      else if (v.includes('hvc') || v.includes('hev') || v.includes('h265')) videoCodec = 'hevc';
    }
    if (!audioCodec && level.audioCodec) {
      const a = level.audioCodec.toLowerCase();
      if (a.includes('mp4a')) audioCodec = 'aac';
      else if (a.includes('ac-3') || a.includes('ac3')) audioCodec = 'ac3';
      else if (a.includes('ec-3') || a.includes('eac3')) audioCodec = 'eac3';
    }

    setBadges(prev => ({
      ...prev,
      videoCodec: videoCodec || prev.videoCodec,
      audioCodec: audioCodec || prev.audioCodec
    }));
  };

  const updateMpegtsBadges = (mediaInfo) => {
    if (!mediaInfo) return;

    let videoCodec = '';
    if (mediaInfo.videoCodec) {
      const v = mediaInfo.videoCodec.toLowerCase();
      if (v.includes('h264') || v.includes('avc')) videoCodec = 'h264';
      else if (v.includes('h265') || v.includes('hevc') || v.includes('hvc')) videoCodec = 'hevc';
      else videoCodec = v;
    }

    let audioCodec = '';
    if (mediaInfo.audioCodec) {
      const a = mediaInfo.audioCodec.toLowerCase();
      if (a.includes('aac')) audioCodec = 'aac';
      else if (a.includes('ac3') || a.includes('ac-3')) audioCodec = 'ac3';
      else if (a.includes('ec-3') || a.includes('eac3')) audioCodec = 'eac3';
      else if (a.includes('mp3')) audioCodec = 'mp3';
      else audioCodec = a;
    }

    let audioChannels = '';
    if (mediaInfo.audioChannelCount) {
      audioChannels = mediaInfo.audioChannelCount === 6 ? '5.1' : `${mediaInfo.audioChannelCount}.0`;
    }

    setBadges(prev => ({
      ...prev,
      videoCodec: videoCodec || prev.videoCodec,
      audioCodec: audioCodec || prev.audioCodec,
      audioChannels: audioChannels || prev.audioChannels
    }));
  };

  const initPlayer = () => {
    destroyPlayer();
    setLoading(true);

    // Small delay so the video element fully settles after destroy before re-init.
    // Without this, video.load() from destroyPlayer races with the new source assignment.
    setTimeout(() => {
      isDestroyingRef.current = false;
      setErrorMsg('');
      const video = videoRef.current;
      if (!video) return;

      // Use muted property — never set volume=0 to mute, as it can stall playback
      video.muted = isMuted;
      video.volume = volume;

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
            if (hls.levels && hls.levels.length > 0) {
              updateHlsBadges(hls.levels[hls.currentLevel] || hls.levels[0]);
            }
          });

          hls.on(Hls.Events.LEVEL_SWITCHED, (event, data) => {
            if (hls.levels && hls.levels[data.level]) {
              updateHlsBadges(hls.levels[data.level]);
            }
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

          mpegtsPlayer.on(mpegts.Events.MEDIA_INFO, (mediaInfo) => {
            updateMpegtsBadges(mediaInfo);
          });

          mpegtsPlayer.on(mpegts.Events.ERROR, (type, detail, info) => {
            console.error('MPEG-TS Error:', type, detail, info);

            // Check if video is actually playing.
            // Non-fatal media errors (such as decoding warnings or transient buffer append issues)
            // can occur while the video continues playing smoothly in the background.
            const video = videoRef.current;
            if (video && !video.paused && video.currentTime > 0) {
              console.warn(`Non-fatal MPEG-TS error ignored because video is playing: ${type} - ${detail}`, info);
              return;
            }

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
    }, 50); // end setTimeout
  };

  const handlePlayError = (err) => {
    console.error('Play error caught:', err);
    setIsPlaying(false);
    setErrorMsg('Stream could not be played. This is common due to Mixed Content (HTTP on HTTPS site) or CORS blocking. Check Settings to apply a proxy.');
  };



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

  // Update video badges dynamically
  useEffect(() => {
    let intervalId;
    if (isPlaying && videoRef.current) {
      intervalId = setInterval(() => {
        const video = videoRef.current;
        if (!video) return;

        let width = video.videoWidth || 0;
        let height = video.videoHeight || 0;

        let decodedFrames = 0;

        if (video.getVideoPlaybackQuality) {
          const qual = video.getVideoPlaybackQuality();
          decodedFrames = qual.totalVideoFrames;
        } else if (video.webkitDecodedFrameCount) {
          decodedFrames = video.webkitDecodedFrameCount;
        }

        const estimatedFps = isNaN(decodedFrames) ? 0 : Math.round(decodedFrames / (video.currentTime || 1)) % 60 || 30;

        let resLabel = '';
        if (height >= 2160) resLabel = '4K';
        else if (height >= 1080) resLabel = '1080p';
        else if (height >= 720) resLabel = '720p';
        else if (height >= 480) resLabel = '480p';
        else if (height > 0) resLabel = `${height}p`;

        setBadges(prev => ({
          ...prev,
          fps: estimatedFps > 0 ? `${estimatedFps} fps` : prev.fps || '30 fps',
          resolution: resLabel || prev.resolution,
        }));
      }, 2000);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isPlaying]);

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
    // Use the muted property only — never set volume=0 to mute
    // Setting volume=0 can stall HLS streams or trigger unexpected pause events
    videoRef.current.muted = nextMuted;
  };

  const handleVolumeChange = (e) => {
    const val = parseFloat(e.target.value);
    setVolume(val);
    setIsMuted(val === 0);
    localStorage.setItem('superstream_volume', String(val));
    if (videoRef.current) {
      videoRef.current.volume = val;
      videoRef.current.muted = val === 0;
    }
  };

  const toggleFullscreen = () => {
    const video = videoRef.current;
    const container = video?.parentElement;
    if (!container) return;

    // Standard Fullscreen API (works on desktop and Android Chrome)
    if (document.fullscreenEnabled && container.requestFullscreen) {
      if (!document.fullscreenElement) {
        container.requestFullscreen().then(() => {
          setIsFullscreen(true);
        }).catch(err => {
          console.error('Fullscreen request error:', err);
          // Fallback to video native fullscreen (iOS Safari)
          if (video && video.webkitEnterFullscreen) {
            video.webkitEnterFullscreen();
          }
        });
      } else {
        document.exitFullscreen();
        setIsFullscreen(false);
      }
    } else if (video && video.webkitEnterFullscreen) {
      // iOS Safari: request native video fullscreen
      if (!document.webkitFullscreenElement && !video.webkitDisplayingFullscreen) {
        video.webkitEnterFullscreen();
      } else if (video.webkitExitFullscreen) {
        video.webkitExitFullscreen();
      }
    }
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
    };
  }, []);

  // Sync iOS native video fullscreen state
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const onWebKitBeginFS = () => setIsFullscreen(true);
    const onWebKitEndFS = () => setIsFullscreen(false);
    video.addEventListener('webkitbeginfullscreen', onWebKitBeginFS);
    video.addEventListener('webkitendfullscreen', onWebKitEndFS);
    return () => {
      video.removeEventListener('webkitbeginfullscreen', onWebKitBeginFS);
      video.removeEventListener('webkitendfullscreen', onWebKitEndFS);
    };
  }, []);

  // Auto-hide controls on mobile after 3 seconds of inactivity
  const resetControlsTimer = () => {
    setShowControls(true);
    if (controlsTimerRef.current) clearTimeout(controlsTimerRef.current);
    if (isMobile && isPlaying) {
      controlsTimerRef.current = setTimeout(() => setShowControls(false), 3000);
    }
  };

  useEffect(() => {
    if (!isMobile) {
      setShowControls(true);
      if (controlsTimerRef.current) clearTimeout(controlsTimerRef.current);
    }
    return () => {
      if (controlsTimerRef.current) clearTimeout(controlsTimerRef.current);
    };
  }, [isMobile]);

  useEffect(() => {
    if (!isMobile) return;
    if (!isPlaying) {
      setShowControls(true);
      if (controlsTimerRef.current) clearTimeout(controlsTimerRef.current);
    } else {
      controlsTimerRef.current = setTimeout(() => setShowControls(false), 3000);
    }
    return () => {
      if (controlsTimerRef.current) clearTimeout(controlsTimerRef.current);
    };
  }, [isPlaying, isMobile]);

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

  return (
    <div style={{ height: '100%', width: '100%' }}>
      {!channel ? (
        <div className="player-empty-container glass-panel">
          <Tv size={isMobile ? 32 : 64} style={{ color: 'var(--text-dark)', marginBottom: isMobile ? '8px' : '20px' }} />
          <h3 style={{ color: 'var(--text-muted)', fontSize: isMobile ? '14px' : '20px', fontWeight: '700' }}>Select a channel to start streaming</h3>
          <p style={{ color: 'var(--text-dark)', fontSize: isMobile ? '11px' : '14px', marginTop: '8px' }}>
            {isMobile ? 'Browse categories in the bottom navigation bar' : 'Browse categories in the sidebar'}
          </p>
        </div>
      ) : (
        <div className="player-wrapper glass-panel">
          {/* Video Container */}
          <div
            className="video-container-box"
            onClick={(e) => {
              // Only handle clicks directly on the container, not bubbled from children
              if (e.target !== e.currentTarget && e.target !== videoRef.current) return;
              if (isMobile) {
                resetControlsTimer();
              } else {
                togglePlay();
              }
            }}
          >
            <video
              ref={videoRef}
              className={`video-element ${getAspectClass()}`}
              playsInline
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              onPlaying={() => {
                setIsPlaying(true);
                setLoading(false);
                setErrorMsg('');
              }}
              onWaiting={() => setLoading(true)}
              onError={(e) => {
                console.error("Video element error event:", e);
                if (isDestroyingRef.current) {
                  console.log("Ignored video error during channel destroy/transition");
                  return;
                }
                if (!channel || !channel.url) return;
                const videoErr = videoRef.current?.error;
                let detail = "Unknown";
                if (videoErr) {
                  if (videoErr.code === 1) detail = "Aborted";
                  else if (videoErr.code === 2) detail = "Network Error";
                  else if (videoErr.code === 3) detail = "Decode Error";
                  else if (videoErr.code === 4) detail = "Format Not Supported";
                }
                setErrorMsg(`Playback error: ${detail}. The stream might be offline or CORS-blocked.`);
                setIsPlaying(false);
                setLoading(false);
              }}
              onClick={(e) => {
                // Prevent click from bubbling to the container which would double-fire togglePlay
                e.stopPropagation();
                if (isMobile) {
                  resetControlsTimer();
                } else {
                  togglePlay();
                }
              }}
            />

            {/* Loading Spinner */}
            {showSpinner && (
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

            {/* Audio codec compatibility warning */}
            {codecUnsupported && !dismissAudioWarning && isPlaying && (
              <div className="audio-warning-banner">
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
                  <div style={{ fontWeight: '700', fontSize: '13px', color: '#ffb703', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>⚠️ No Sound?</span>
                  </div>
                  <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.85)', lineHeight: '1.4', textAlign: 'left' }}>
                    AC3/EAC3 audio is not supported on PC browsers.
                  </div>
                  <div style={{ fontSize: '11px', color: '#03ffeaff', lineHeight: '1.4', textAlign: 'left' }}>
                    Try other channels, Safari browser, or our Windows app.
                  </div>
                </div>
                <button
                  className="audio-warning-dismiss"
                  onClick={(e) => {
                    e.stopPropagation();
                    setDismissAudioWarning(true);
                  }}
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* Custom Overlay Controls */}
            <div
              className="player-controls-overlay"
              style={isMobile ? { opacity: showControls ? 1 : 0, pointerEvents: showControls ? 'auto' : 'none' } : {}}
            >
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

              {/* Bottom Controls Area (Badges Row + Control Buttons Bar) */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', width: '100%' }}>
                {/* Metadata Badges */}
                {isPlaying && (
                  <div className="player-meta-badges">
                    {badges.fps && <span className="meta-badge">{badges.fps}</span>}
                    {badges.resolution && <span className="meta-badge">{badges.resolution}</span>}
                    {badges.videoCodec && <span className="meta-badge">{badges.videoCodec}</span>}
                    {badges.audioChannels && <span className="meta-badge">{badges.audioChannels}</span>}
                    {badges.audioCodec && <span className="meta-badge">{badges.audioCodec}</span>}
                  </div>
                )}

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
                      <button className="control-btn" onClick={toggleMute} title={isMobile ? 'Mute / Unmute (use hardware buttons for volume)' : 'Mute'} >
                        {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
                      </button>
                      {/* Desktop only: software volume slider */}
                      {!isMobile && (
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={isMuted ? 0 : volume}
                          onChange={handleVolumeChange}
                          className="volume-slider"
                        />
                      )}
                      {/* Mobile: hardware volume hint */}
                      {isMobile && (
                        <span className="mobile-vol-hint">Use ± buttons</span>
                      )}
                    </div>

                    {/* Live badge */}
                    <span className="badge badge-live text-digital">
                      ● Live
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
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
          </div>
        </div>
      )}

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
          cursor: pointer;
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
        
        .mobile-vol-hint {
          font-size: 9px;
          color: rgba(255,255,255,0.35);
          font-family: var(--font-sans);
          letter-spacing: 0.03em;
          white-space: nowrap;
          pointer-events: none;
          user-select: none;
        }

        .player-meta-badges {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-left: 12px;
          flex-wrap: wrap;
        }
        .meta-badge {
          font-size: 10px;
          font-weight: 600;
          color: #fff;
          border: 1px solid rgba(255, 255, 255, 0.65);
          border-radius: 20px;
          padding: 2px 10px;
          text-transform: lowercase;
          letter-spacing: 0.02em;
          background: rgba(255, 255, 255, 0.05);
          display: inline-block;
          line-height: 1.2;
          font-family: var(--font-sans);
        }

        .audio-warning-banner {
          position: absolute;
          top: 72px;
          right: 16px;
          max-width: 320px;
          background: rgba(20, 20, 25, 0.9);
          border: 1px solid rgba(255, 183, 3, 0.3);
          border-left: 4px solid #ffb703;
          border-radius: 6px;
          padding: 12px;
          z-index: 25;
          display: flex;
          align-items: flex-start;
          gap: 12px;
          box-shadow: 0 4px 20px rgba(0,0,0,0.5);
          backdrop-filter: blur(8px);
          animation: slideInRight 0.3s ease;
        }
        .audio-warning-dismiss {
          background: rgba(255,255,255,0.08);
          border: none;
          color: #fff;
          font-size: 10px;
          font-weight: 600;
          padding: 4px 8px;
          border-radius: 4px;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        .audio-warning-dismiss:hover {
          background: rgba(255,255,255,0.18);
        }
        @keyframes slideInRight {
          from {
            transform: translateX(30px);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }

      `}</style>
    </div>
  );
}
