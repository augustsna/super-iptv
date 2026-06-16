import React, { useState, useEffect } from 'react';
import { Search, Heart, RefreshCw, AlertCircle, Play, Film, Tv, PlayCircle, Star, Settings as SettingsIcon, LogOut, Radio, Clapperboard } from 'lucide-react';
import Sidebar from './components/Sidebar';
import Player from './components/Player';
import PlaylistSelector from './components/PlaylistSelector';
import Settings from './components/Settings';
import { formatXtreamLiveStream, formatXtreamMovie, formatXtreamSeries } from './utils/parsers';

const SESSION_KEY = 'superstream_session';
const SESSION_TTL_MS = 12 * 60 * 60 * 1000; // 12 hours

function loadSavedSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const { playlistInfo, loginTimestamp } = JSON.parse(raw);
    if (Date.now() - loginTimestamp > SESSION_TTL_MS) {
      localStorage.removeItem(SESSION_KEY);
      return null;
    }
    return playlistInfo;
  } catch {
    return null;
  }
}

export default function App() {
  const [playlistInfo, setPlaylistInfo] = useState(() => loadSavedSession());
  const [activeTab, setActiveTab] = useState('live'); // live, movies, series, favorites, settings
  const [channels, setChannels] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  const [selectedChannel, setSelectedChannel] = useState(null);
  const [favorites, setFavorites] = useState([]);


  // Xtream Codes extra state
  const [movies, setMovies] = useState([]);
  const [movieCategories, setMovieCategories] = useState([]);
  const [selectedMovieCategory, setSelectedMovieCategory] = useState('All');

  const [series, setSeries] = useState([]);
  const [seriesCategories, setSeriesCategories] = useState([]);
  const [selectedSeriesCategory, setSelectedSeriesCategory] = useState('All');
  const [selectedSeriesItem, setSelectedSeriesItem] = useState(null); // Active series for detailed episodes
  const [seriesEpisodes, setSeriesEpisodes] = useState([]); // Season-grouped episodes for active series

  const [loadingMedia, setLoadingMedia] = useState(false);
  const [loadingEpisodes, setLoadingEpisodes] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');


  // Proxy state (synced with PlaylistSelector)
  const [useProxy, setUseProxy] = useState(true);
  const [proxyUrl, setProxyUrl] = useState('https://api.allorigins.win/raw?url=');

  const [loadStep, setLoadStep] = useState(() => {
    const saved = localStorage.getItem('streampulse_load_step');
    if (saved) {
      if (saved === 'all') return 1000000;
      const parsed = parseInt(saved, 10);
      if (!isNaN(parsed) && parsed > 0) return parsed;
    }
    return 50;
  });
  const [isCustomLoad, setIsCustomLoad] = useState(() => {
    const saved = localStorage.getItem('streampulse_is_custom_load');
    return saved === 'true';
  });
  const [customLoadValue, setCustomLoadValue] = useState(() => {
    const saved = localStorage.getItem('streampulse_custom_load_value');
    return saved ? parseInt(saved, 10) : 150;
  });
  const [displayLimit, setDisplayLimit] = useState(loadStep);

  const handleLoadStepChange = (val) => {
    if (val === 'all') {
      setIsCustomLoad(false);
      setLoadStep(1000000);
      localStorage.setItem('streampulse_is_custom_load', 'false');
      localStorage.setItem('streampulse_load_step', '1000000');
    } else if (val === 'custom') {
      setIsCustomLoad(true);
      setLoadStep(customLoadValue);
      localStorage.setItem('streampulse_is_custom_load', 'true');
      localStorage.setItem('streampulse_load_step', String(customLoadValue));
    } else {
      setIsCustomLoad(false);
      const num = parseInt(val, 10);
      setLoadStep(num);
      localStorage.setItem('streampulse_is_custom_load', 'false');
      localStorage.setItem('streampulse_load_step', String(num));
    }
  };
  const handleCustomValueChange = (val) => {
    const num = Math.max(1, parseInt(val, 10) || 1);
    setCustomLoadValue(num);
    setLoadStep(num);
    localStorage.setItem('streampulse_custom_load_value', String(num));
    localStorage.setItem('streampulse_load_step', String(num));
  };

  const selectValue = isCustomLoad
    ? 'custom'
    : (loadStep === 1000000
      ? 'all'
      : ([50, 100, 200, 500, 1000].includes(loadStep) ? String(loadStep) : 'custom'));

  // Reset display limit when filtering changes
  useEffect(() => {
    setDisplayLimit(loadStep);
  }, [activeTab, selectedCategory, selectedMovieCategory, selectedSeriesCategory, searchQuery, loadStep]);

  // Sync favorites from LocalStorage
  useEffect(() => {
    const savedFavs = localStorage.getItem('streampulse_favs');
    if (savedFavs) {
      try {
        setFavorites(JSON.parse(savedFavs));
      } catch (e) {
        console.error(e);
      }
    }
  }, []);

  const saveFavorites = (newFavs) => {
    setFavorites(newFavs);
    localStorage.setItem('streampulse_favs', JSON.stringify(newFavs));
  };

  const toggleFavorite = (channelId, e) => {
    if (e) e.stopPropagation();
    if (favorites.includes(channelId)) {
      saveFavorites(favorites.filter(id => id !== channelId));
    } else {
      saveFavorites([...favorites, channelId]);
    }
  };

  // Restore session on first mount (re-fetch streams if session was saved)
  useEffect(() => {
    const saved = loadSavedSession();
    if (!saved) return;
    setUseProxy(saved.useProxy ?? true);
    setProxyUrl(saved.proxyUrl ?? 'https://api.allorigins.win/raw?url=');
    setActiveTab('live'); // Always default to Live TV tab on start
    if (saved.type === 'xtream') {
      fetchXtreamLive(saved.credentials, saved.useProxy, saved.proxyUrl);
    } else if (saved.type === 'm3u') {
      setChannels(saved.channels || []);
      const cats = saved.categories || [];
      setCategories(cats);
      setSelectedCategory(cats[0] || 'All');
    }
  }, []);

  // Sync proxy settings back and forth
  const handlePlaylistLoaded = (info) => {
    setPlaylistInfo(info);
    // Persist session
    localStorage.setItem(SESSION_KEY, JSON.stringify({ playlistInfo: info, loginTimestamp: Date.now() }));
    setUseProxy(info.useProxy ?? true);
    setProxyUrl(info.proxyUrl ?? 'https://api.allorigins.win/raw?url=');
    setErrorMsg('');

    if (info.type === 'm3u') {
      setChannels(info.channels);
      const hasWorldCup = info.categories.includes('World Cup 2026');
      setCategories(hasWorldCup ? ['All Channels', 'World Cup 2026', 'Sports'] : ['All Channels', 'Sports']);
      setSelectedCategory('All Channels');
      setActiveTab('live');
    } else if (info.type === 'xtream') {
      // Fetch Live categories and streams
      fetchXtreamLive(info.credentials, info.useProxy, info.proxyUrl);
    }
  };

  const fetchXtreamLive = async (creds, proxy, pUrl) => {
    setLoadingMedia(true);
    setErrorMsg('');
    try {
      const { host, username, password } = creds;

      // Fetch Live categories
      const catUrl = `${host}/player_api.php?username=${username}&password=${password}&action=get_live_categories`;
      const catFetchUrl = proxy ? `${pUrl}${encodeURIComponent(catUrl)}` : catUrl;
      const catResponse = await fetch(catFetchUrl);
      if (!catResponse.ok) throw new Error('Live categories load failed');
      const catsJson = await catResponse.json();

      // Fetch Live Streams
      const streamsUrl = `${host}/player_api.php?username=${username}&password=${password}&action=get_live_streams`;
      const streamsFetchUrl = proxy ? `${pUrl}${encodeURIComponent(streamsUrl)}` : streamsUrl;
      const streamsResponse = await fetch(streamsFetchUrl);
      if (!streamsResponse.ok) throw new Error('Live streams load failed');
      const streamsJson = await streamsResponse.json();

      // Formulate categories
      const serverCats = Array.isArray(catsJson) ? catsJson.map(c => c.category_name).filter(Boolean) : [];
      setCategories([...new Set(['All Channels', '🏆 Sports', ...serverCats])]);

      // Parse and format streams
      const catMap = {};
      if (Array.isArray(catsJson)) {
        catsJson.forEach(c => {
          catMap[c.category_id] = c.category_name;
        });
      }

      const formattedChannels = Array.isArray(streamsJson)
        ? streamsJson.map(s => {
          s.category_name = catMap[s.category_id] || 'Uncategorized';
          return formatXtreamLiveStream(s, host, username, password);
        })
        : [];

      setChannels(formattedChannels);
      setSelectedCategory('All Channels');
      setActiveTab('live');
    } catch (err) {
      console.error(err);
      setErrorMsg(`Failed to load portal channels: ${err.message}. Try switching CORS proxy or loading via M3U URL.`);
    } finally {
      setLoadingMedia(false);
    }
  };

  // Fetch Xtream Movies on Tab Switch
  useEffect(() => {
    if (activeTab === 'movies' && playlistInfo?.type === 'xtream' && movies.length === 0) {
      fetchXtreamMovies();
    } else if (activeTab === 'series' && playlistInfo?.type === 'xtream' && series.length === 0) {
      fetchXtreamSeries();
    }
  }, [activeTab]);

  const fetchXtreamMovies = async () => {
    setLoadingMedia(true);
    setErrorMsg('');
    try {
      const { host, username, password } = playlistInfo.credentials;

      // Fetch categories
      const catUrl = `${host}/player_api.php?username=${username}&password=${password}&action=get_vod_categories`;
      const catFetchUrl = useProxy ? `${proxyUrl}${encodeURIComponent(catUrl)}` : catUrl;
      const catResponse = await fetch(catFetchUrl);
      const catsJson = await catResponse.json();

      // Fetch streams
      const streamsUrl = `${host}/player_api.php?username=${username}&password=${password}&action=get_vod_streams`;
      const streamsFetchUrl = useProxy ? `${proxyUrl}${encodeURIComponent(streamsUrl)}` : streamsUrl;
      const streamsResponse = await fetch(streamsFetchUrl);
      const streamsJson = await streamsResponse.json();

      const catMap = {};
      if (Array.isArray(catsJson)) {
        catsJson.forEach(c => {
          catMap[c.category_id] = c.category_name;
        });
      }

      const formattedMovies = Array.isArray(streamsJson)
        ? streamsJson.map(m => {
          m.category_name = catMap[m.category_id] || 'Movies';
          return formatXtreamMovie(m, host, username, password);
        })
        : [];

      const serverMovieCats = Array.isArray(catsJson) ? catsJson.map(c => c.category_name).filter(Boolean) : [];
      setMovieCategories(['All Movies', ...new Set(serverMovieCats)]);
      setMovies(formattedMovies);
      setSelectedMovieCategory('All Movies');
    } catch (err) {
      console.error(err);
      setErrorMsg(`Failed to fetch movies: ${err.message}`);
    } finally {
      setLoadingMedia(false);
    }
  };

  const fetchXtreamSeries = async () => {
    setLoadingMedia(true);
    setErrorMsg('');
    try {
      const { host, username, password } = playlistInfo.credentials;

      // Fetch categories
      const catUrl = `${host}/player_api.php?username=${username}&password=${password}&action=get_series_categories`;
      const catFetchUrl = useProxy ? `${proxyUrl}${encodeURIComponent(catUrl)}` : catUrl;
      const catResponse = await fetch(catFetchUrl);
      const catsJson = await catResponse.json();

      // Fetch streams
      const streamsUrl = `${host}/player_api.php?username=${username}&password=${password}&action=get_series`;
      const streamsFetchUrl = useProxy ? `${proxyUrl}${encodeURIComponent(streamsUrl)}` : streamsUrl;
      const streamsResponse = await fetch(streamsFetchUrl);
      const streamsJson = await streamsResponse.json();

      const catMap = {};
      if (Array.isArray(catsJson)) {
        catsJson.forEach(c => {
          catMap[c.category_id] = c.category_name;
        });
      }

      const formattedSeries = Array.isArray(streamsJson)
        ? streamsJson.map(s => {
          s.category_name = catMap[s.category_id] || 'TV Series';
          return formatXtreamSeries(s);
        })
        : [];

      const serverSeriesCats = Array.isArray(catsJson) ? catsJson.map(c => c.category_name).filter(Boolean) : [];
      setSeriesCategories(['All Series', ...new Set(serverSeriesCats)]);
      setSeries(formattedSeries);
      setSelectedSeriesCategory('All Series');
    } catch (err) {
      console.error(err);
      setErrorMsg(`Failed to fetch series: ${err.message}`);
    } finally {
      setLoadingMedia(false);
    }
  };

  const handleSelectSeries = async (seriesItem) => {
    setSelectedSeriesItem(seriesItem);
    setLoadingEpisodes(true);
    setSeriesEpisodes([]);
    try {
      const { host, username, password } = playlistInfo.credentials;
      const url = `${host}/player_api.php?username=${username}&password=${password}&action=get_series_info&series_id=${seriesItem.seriesId}`;
      const fetchUrl = useProxy ? `${proxyUrl}${encodeURIComponent(url)}` : url;

      const response = await fetch(fetchUrl);
      const json = await response.json();

      // Episodes are structured as an object of seasons: { "1": [ { id, title, container_extension }, ... ] }
      if (json && json.episodes) {
        setSeriesEpisodes(json.episodes);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingEpisodes(false);
    }
  };

  const playEpisode = (episode, seriesName) => {
    const { host, username, password } = playlistInfo.credentials;
    const ext = episode.container_extension || 'mp4';
    const streamUrl = `${host}/series/${username}/${password}/${episode.id}.${ext}`;

    setSelectedChannel({
      uniqueId: `xtream-episode-${episode.id}`,
      id: `xtream-episode-${episode.id}`,
      name: `${seriesName} - S${episode.season}E${episode.episode_num}: ${episode.title}`,
      logo: selectedSeriesItem.logo,
      category: selectedSeriesItem.category,
      url: streamUrl,
      type: 'video'
    });
  };

  const handleLogout = () => {
    localStorage.removeItem(SESSION_KEY);
    setPlaylistInfo(null);
    setChannels([]);
    setMovies([]);
    setSeries([]);
    setSelectedChannel(null);
    setSelectedSeriesItem(null);
  };

  const handleGoHome = () => {
    setActiveTab('live');
    setSearchQuery('');
    setSelectedChannel(null);
    setSelectedSeriesItem(null);
  };

  // Get active items to render
  const getFilteredChannels = () => {
    let list = [];
    if (activeTab === 'live') {
      list = channels;
      if (selectedCategory === '🏆 Sports') {
        list = list.filter(ch => {
          const cat = (ch.category || '').toLowerCase();
          return cat.includes('sport') || cat.includes('esporte') || cat.includes('desporto');
        });
      } else if (selectedCategory !== 'All' && selectedCategory !== 'All Channels') {
        list = list.filter(ch => ch.category === selectedCategory);
      }
    } else if (activeTab === 'favorites') {
      // Merge live channels, movies and series
      list = [...channels, ...movies].filter(ch => favorites.includes(ch.uniqueId));
    }

    if (searchQuery) {
      list = list.filter(ch => ch.name.toLowerCase().includes(searchQuery.toLowerCase()));
    }
    return list;
  };

  const getFilteredMovies = () => {
    let list = movies;
    if (selectedMovieCategory !== 'All Movies') {
      list = list.filter(m => m.category === selectedMovieCategory);
    }
    if (searchQuery) {
      list = list.filter(m => m.name.toLowerCase().includes(searchQuery.toLowerCase()));
    }
    return list;
  };

  const getFilteredSeries = () => {
    let list = series;
    if (selectedSeriesCategory !== 'All Series') {
      list = list.filter(s => s.category === selectedSeriesCategory);
    }
    if (searchQuery) {
      list = list.filter(s => s.name.toLowerCase().includes(searchQuery.toLowerCase()));
    }
    return list;
  };

  if (!playlistInfo) {
    return <PlaylistSelector onPlaylistLoaded={handlePlaylistLoaded} onError={(err) => setErrorMsg(err)} />;
  }

  return (
    <div className="app-container">
      {/* Mobile Top Header */}
      <header className="mobile-header">
        <button
          onClick={handleGoHome}
          style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px', borderRadius: '6px', opacity: 1, transition: 'opacity 0.2s ease' }}
          title="Go to Home"
          onMouseEnter={e => e.currentTarget.style.opacity = '0.7'}
          onMouseLeave={e => e.currentTarget.style.opacity = '1'}
        >
          <Radio className="brand-icon glow-text-primary" size={20} style={{ color: 'var(--primary)' }} />
          <span className="brand-title text-digital glow-text-primary" style={{ fontSize: '15px', fontWeight: '800', color: 'var(--primary)' }}>
            Super Stream
          </span>
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button className="mobile-logout-btn" onClick={handleLogout}>
            <LogOut size={12} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'middle' }} />
            Disconnect
          </button>
        </div>
      </header>

      {/* Sidebar (Desktop only) */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab);
          setSearchQuery('');
          setSelectedSeriesItem(null);
        }}
        playlistInfo={playlistInfo}
        onLogout={handleLogout}
        onHome={handleGoHome}
        favoritesCount={favorites.length}
      />

      {/* Main dashboard content */}
      <main className="main-content">
        {activeTab === 'settings' ? (
          <Settings
            onClearPlaylist={handleLogout}
            onClearFavorites={() => saveFavorites([])}
            playlistInfo={playlistInfo}
            loadStep={loadStep}
            handleLoadStepChange={handleLoadStepChange}
            customLoadValue={customLoadValue}
            handleCustomValueChange={handleCustomValueChange}
            selectValue={selectValue}
          />
        ) : (
          <div className="dashboard-grid">

            {/* Left side: player only */}
            <div className="player-column">
              <div className={`player-wrapper-container ${!selectedChannel ? 'placeholder' : ''}`}>
                <Player channel={selectedChannel} />
              </div>
            </div>

            {/* Right side: Categories & Lists */}
            <div className="glass-panel main-list-panel">
              {/* Search Header */}
              <div className="list-search-bar">
                <div style={{ position: 'relative', flex: 1 }}>
                  <Search size={16} className="search-icon" />
                  <input
                    type="text"
                    placeholder={`Search ${activeTab}...`}
                    className="input-field"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    style={{ paddingLeft: '36px', height: '40px' }}
                  />
                </div>
              </div>

              {/* Body: vertical category sidebar + content */}
              <div className="panel-body">

                {/* Vertical Category Sidebar */}
                {activeTab === 'live' && (
                  <div className="cat-sidebar">
                    <div className="cat-sidebar-title">Categories</div>
                    {categories.map((cat, idx) => (
                      <button
                        key={idx}
                        className={`cat-sidebar-item ${selectedCategory === cat ? 'active' : ''}`}
                        onClick={() => setSelectedCategory(cat)}
                        title={cat}
                      >
                        {cat}
                      </button>
                    ))}
                  </div>
                )}

                {activeTab === 'movies' && (
                  <div className="cat-sidebar">
                    <div className="cat-sidebar-title">Categories</div>
                    {movieCategories.map((cat, idx) => (
                      <button
                        key={idx}
                        className={`cat-sidebar-item ${selectedMovieCategory === cat ? 'active' : ''}`}
                        onClick={() => setSelectedMovieCategory(cat)}
                        title={cat}
                      >
                        {cat}
                      </button>
                    ))}
                  </div>
                )}

                {activeTab === 'series' && !selectedSeriesItem && (
                  <div className="cat-sidebar">
                    <div className="cat-sidebar-title">Categories</div>
                    {seriesCategories.map((cat, idx) => (
                      <button
                        key={idx}
                        className={`cat-sidebar-item ${selectedSeriesCategory === cat ? 'active' : ''}`}
                        onClick={() => setSelectedSeriesCategory(cat)}
                        title={cat}
                      >
                        {cat}
                      </button>
                    ))}
                  </div>
                )}

                {/* If no sidebar (favorites tab or series episode view), no left column */}
                <div className="content-col">

              {/* Primary list renderer */}
              <div className="list-items-container">
                {loadingMedia ? (
                  <div className="list-loading-state">
                    <RefreshCw className="spin-animation" size={24} style={{ color: 'var(--primary)', marginBottom: '8px' }} />
                    <p>Updating catalogs...</p>
                  </div>
                ) : errorMsg ? (
                  <div className="list-error-state">
                    <AlertCircle size={24} style={{ color: '#ef4444', marginBottom: '8px' }} />
                    <p>{errorMsg}</p>
                  </div>
                ) : activeTab === 'live' || activeTab === 'favorites' ? (
                  /* Live TV or Favorites List */
                  <div className="channels-list">
                    {getFilteredChannels().slice(0, displayLimit).map((ch) => {
                      const isActive = selectedChannel?.uniqueId === ch.uniqueId;
                      const isFav = favorites.includes(ch.uniqueId);
                      return (
                        <div
                          key={ch.uniqueId}
                          className={`channel-item-card ${isActive ? 'active' : ''}`}
                          onClick={() => setSelectedChannel(ch)}
                        >
                          <div className="channel-logo-container">
                            {ch.logo ? (
                              <img src={ch.logo} alt="" onError={(e) => e.target.style.display = 'none'} />
                            ) : (
                              <Tv size={18} style={{ color: 'var(--text-dark)' }} />
                            )}
                          </div>

                          <div className="channel-details">
                            <div className="channel-name-txt">{ch.name}</div>
                            <div className="channel-category-txt">{ch.category}</div>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <button className={`fav-btn ${isFav ? 'active' : ''}`} onClick={(e) => toggleFavorite(ch.uniqueId, e)}>
                              <Star size={14} fill={isFav ? 'currentColor' : 'none'} />
                            </button>
                            {isActive && <Play size={12} fill="var(--primary)" style={{ color: 'var(--primary)' }} />}
                          </div>
                        </div>
                      );
                    })}
                    {getFilteredChannels().length > displayLimit && (
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', margin: '16px auto' }}>
                        <button
                          className="btn btn-secondary"
                          onClick={() => setDisplayLimit(prev => prev + loadStep)}
                          style={{ display: 'block', width: '200px' }}
                        >
                          Load More ({getFilteredChannels().length - displayLimit} remaining)
                        </button>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: 'var(--text-dark)' }}>
                          <span>Load amount:</span>
                          <select
                            value={selectValue}
                            onChange={e => handleLoadStepChange(e.target.value)}
                            style={{
                              background: 'rgba(255,255,255,0.03)',
                              border: '1px solid var(--border-color)',
                              color: 'var(--text-muted)',
                              borderRadius: '4px',
                              padding: '4px 8px',
                              cursor: 'pointer',
                              outline: 'none',
                              fontSize: '11px'
                            }}
                          >
                            <option value="50" style={{ background: '#0e111a', color: '#fff' }}>50</option>
                            <option value="100" style={{ background: '#0e111a', color: '#fff' }}>100</option>
                            <option value="200" style={{ background: '#0e111a', color: '#fff' }}>200</option>
                            <option value="500" style={{ background: '#0e111a', color: '#fff' }}>500</option>
                            <option value="1000" style={{ background: '#0e111a', color: '#fff' }}>1000</option>
                            <option value="custom" style={{ background: '#0e111a', color: '#fff' }}>Custom...</option>
                            <option value="all" style={{ background: '#0e111a', color: '#fff' }}>Show All</option>
                          </select>
                          {selectValue === 'custom' && (
                            <input
                              type="number"
                              min="1"
                              value={customLoadValue}
                              onChange={e => handleCustomValueChange(e.target.value)}
                              style={{
                                background: 'rgba(255,255,255,0.03)',
                                border: '1px solid var(--border-color)',
                                color: '#fff',
                                borderRadius: '4px',
                                padding: '4px 8px',
                                outline: 'none',
                                fontSize: '11px',
                                width: '70px'
                              }}
                              placeholder="Amount"
                            />
                          )}
                        </div>
                      </div>
                    )}
                    {getFilteredChannels().length === 0 && (
                      <div className="list-empty-state">No matching streams found</div>
                    )}
                  </div>
                ) : activeTab === 'movies' ? (
                  /* VOD Movie Grid */
                  <div className="vod-grid">
                    {getFilteredMovies().slice(0, displayLimit).map((mv) => {
                      const isActive = selectedChannel?.uniqueId === mv.uniqueId;
                      const isFav = favorites.includes(mv.uniqueId);
                      return (
                        <div key={mv.uniqueId} className="vod-card" onClick={() => setSelectedChannel(mv)}>
                          <div className="vod-thumbnail">
                            {mv.logo ? (
                              <img src={mv.logo} alt={mv.name} loading="lazy" />
                            ) : (
                              <Film size={32} style={{ color: 'var(--text-dark)' }} />
                            )}
                            <div className="vod-overlay-play">
                              <PlayCircle size={40} style={{ color: 'var(--primary)' }} />
                            </div>
                            {mv.rating && <span className="vod-badge-rating">{mv.rating}</span>}
                          </div>
                          <div className="vod-title" title={mv.name}>{mv.name}</div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
                            <span style={{ fontSize: '10px', color: 'var(--text-dark)' }}>{mv.year || 'VOD'}</span>
                            <button className={`fav-btn ${isFav ? 'active' : ''}`} onClick={(e) => toggleFavorite(mv.uniqueId, e)}>
                              <Star size={11} fill={isFav ? 'currentColor' : 'none'} />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                    {getFilteredMovies().length > displayLimit && (
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', margin: '16px auto', gridColumn: '1 / -1' }}>
                        <button
                          className="btn btn-secondary"
                          onClick={() => setDisplayLimit(prev => prev + loadStep)}
                          style={{ display: 'block', width: '200px' }}
                        >
                          Load More ({getFilteredMovies().length - displayLimit} remaining)
                        </button>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: 'var(--text-dark)' }}>
                          <span>Load amount:</span>
                          <select
                            value={selectValue}
                            onChange={e => handleLoadStepChange(e.target.value)}
                            style={{
                              background: 'rgba(255,255,255,0.03)',
                              border: '1px solid var(--border-color)',
                              color: 'var(--text-muted)',
                              borderRadius: '4px',
                              padding: '4px 8px',
                              cursor: 'pointer',
                              outline: 'none',
                              fontSize: '11px'
                            }}
                          >
                            <option value="50" style={{ background: '#0e111a', color: '#fff' }}>50</option>
                            <option value="100" style={{ background: '#0e111a', color: '#fff' }}>100</option>
                            <option value="200" style={{ background: '#0e111a', color: '#fff' }}>200</option>
                            <option value="500" style={{ background: '#0e111a', color: '#fff' }}>500</option>
                            <option value="1000" style={{ background: '#0e111a', color: '#fff' }}>1000</option>
                            <option value="custom" style={{ background: '#0e111a', color: '#fff' }}>Custom...</option>
                            <option value="all" style={{ background: '#0e111a', color: '#fff' }}>Show All</option>
                          </select>
                          {selectValue === 'custom' && (
                            <input
                              type="number"
                              min="1"
                              value={customLoadValue}
                              onChange={e => handleCustomValueChange(e.target.value)}
                              style={{
                                background: 'rgba(255,255,255,0.03)',
                                border: '1px solid var(--border-color)',
                                color: '#fff',
                                borderRadius: '4px',
                                padding: '4px 8px',
                                outline: 'none',
                                fontSize: '11px',
                                width: '70px'
                              }}
                              placeholder="Amount"
                            />
                          )}
                        </div>
                      </div>
                    )}
                    {getFilteredMovies().length === 0 && (
                      <div className="list-empty-state">No movies found</div>
                    )}
                  </div>
                ) : activeTab === 'series' ? (
                  /* Series Browser and Episode Selector */
                  selectedSeriesItem ? (
                    <div className="series-episodes-view">
                      <button className="btn btn-secondary btn-sm" onClick={() => setSelectedSeriesItem(null)} style={{ marginBottom: '16px', padding: '6px 12px', fontSize: '11px' }}>
                        ← Back to Series List
                      </button>

                      <div className="series-details-header">
                        {selectedSeriesItem.logo && <img src={selectedSeriesItem.logo} alt="" style={{ height: '70px', borderRadius: '4px', objectFit: 'cover' }} />}
                        <div>
                          <h3 style={{ fontSize: '15px', color: '#fff' }}>{selectedSeriesItem.name}</h3>
                          <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{selectedSeriesItem.category}</p>
                          {selectedSeriesItem.rating && <span style={{ fontSize: '10px', color: 'var(--accent)' }}>★ {selectedSeriesItem.rating}</span>}
                        </div>
                      </div>

                      {loadingEpisodes ? (
                        <div style={{ textAlign: 'center', padding: '24px' }}>
                          <RefreshCw className="spin-animation" size={20} style={{ color: 'var(--primary)', marginBottom: '8px' }} />
                          <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Fetching season guides...</p>
                        </div>
                      ) : (
                        <div className="seasons-container">
                          {Object.keys(seriesEpisodes).map((seasonNum) => (
                            <div key={seasonNum} style={{ marginBottom: '16px' }}>
                              <h4 style={{ fontSize: '12px', color: 'var(--primary)', borderBottom: '1px solid var(--border-color)', paddingBottom: '4px', marginBottom: '8px', fontWeight: '700' }}>
                                Season {seasonNum}
                              </h4>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                {seriesEpisodes[seasonNum].map((ep) => (
                                  <div
                                    key={ep.id}
                                    className="episode-item"
                                    onClick={() => playEpisode(ep, selectedSeriesItem.name)}
                                  >
                                    <span style={{ fontWeight: '700', color: 'var(--primary)', minWidth: '36px' }}>E{ep.episode_num}</span>
                                    <span style={{ flex: 1, color: '#fff', fontSize: '12px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ep.title}</span>
                                    <Play size={10} style={{ color: 'var(--text-dark)' }} />
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                          {Object.keys(seriesEpisodes).length === 0 && (
                            <div className="list-empty-state">No episodes available</div>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="vod-grid">
                      {getFilteredSeries().slice(0, displayLimit).map((sr) => (
                        <div key={sr.uniqueId} className="vod-card" onClick={() => handleSelectSeries(sr)}>
                          <div className="vod-thumbnail">
                            {sr.logo ? (
                              <img src={sr.logo} alt={sr.name} loading="lazy" />
                            ) : (
                              <Film size={32} style={{ color: 'var(--text-dark)' }} />
                            )}
                            <div className="vod-overlay-play">
                              <PlayCircle size={40} style={{ color: 'var(--primary)' }} />
                            </div>
                            {sr.rating && <span className="vod-badge-rating">{sr.rating}</span>}
                          </div>
                          <div className="vod-title" title={sr.name}>{sr.name}</div>
                          <div style={{ fontSize: '10px', color: 'var(--text-dark)', marginTop: '4px' }}>
                            {sr.releaseDate || 'Series'}
                          </div>
                        </div>
                      ))}
                      {getFilteredSeries().length > displayLimit && (
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', margin: '16px auto', gridColumn: '1 / -1' }}>
                          <button
                            className="btn btn-secondary"
                            onClick={() => setDisplayLimit(prev => prev + loadStep)}
                            style={{ display: 'block', width: '200px' }}
                          >
                            Load More ({getFilteredSeries().length - displayLimit} remaining)
                          </button>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: 'var(--text-dark)' }}>
                            <span>Load amount:</span>
                            <select
                              value={selectValue}
                              onChange={e => handleLoadStepChange(e.target.value)}
                              style={{
                                background: 'rgba(255,255,255,0.03)',
                                border: '1px solid var(--border-color)',
                                color: 'var(--text-muted)',
                                borderRadius: '4px',
                                padding: '4px 8px',
                                cursor: 'pointer',
                                outline: 'none',
                                fontSize: '11px'
                              }}
                            >
                              <option value="50" style={{ background: '#0e111a', color: '#fff' }}>50</option>
                              <option value="100" style={{ background: '#0e111a', color: '#fff' }}>100</option>
                              <option value="200" style={{ background: '#0e111a', color: '#fff' }}>200</option>
                              <option value="500" style={{ background: '#0e111a', color: '#fff' }}>500</option>
                              <option value="1000" style={{ background: '#0e111a', color: '#fff' }}>1000</option>
                              <option value="custom" style={{ background: '#0e111a', color: '#fff' }}>Custom...</option>
                              <option value="all" style={{ background: '#0e111a', color: '#fff' }}>Show All</option>
                            </select>
                            {selectValue === 'custom' && (
                              <input
                                type="number"
                                min="1"
                                value={customLoadValue}
                                onChange={e => handleCustomValueChange(e.target.value)}
                                style={{
                                  background: 'rgba(255,255,255,0.03)',
                                  border: '1px solid var(--border-color)',
                                  color: '#fff',
                                  borderRadius: '4px',
                                  padding: '4px 8px',
                                  outline: 'none',
                                  fontSize: '11px',
                                  width: '70px'
                                }}
                                placeholder="Amount"
                              />
                            )}
                          </div>
                        </div>
                      )}
                      {getFilteredSeries().length === 0 && (
                        <div className="list-empty-state">No series found</div>
                      )}
                    </div>
                  )
                ) : null}
              </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Mobile Bottom Navigation */}
      <nav className="mobile-bottom-nav">
        <button
          className={`mobile-nav-item ${activeTab === 'live' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('live');
            setSearchQuery('');
            setSelectedSeriesItem(null);
          }}
        >
          <Tv size={20} />
          <span>Live TV</span>
        </button>

        {playlistInfo?.type === 'xtream' && (
          <>
            <button
              className={`mobile-nav-item ${activeTab === 'movies' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('movies');
                setSearchQuery('');
                setSelectedSeriesItem(null);
              }}
            >
              <Film size={20} />
              <span>Movies</span>
            </button>

            <button
              className={`mobile-nav-item ${activeTab === 'series' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('series');
                setSearchQuery('');
                setSelectedSeriesItem(null);
              }}
            >
              <Clapperboard size={20} />
              <span>Series</span>
            </button>
          </>
        )}

        <button
          className={`mobile-nav-item ${activeTab === 'favorites' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('favorites');
            setSearchQuery('');
            setSelectedSeriesItem(null);
          }}
        >
          <div style={{ position: 'relative', display: 'inline-flex' }}>
            <Heart size={20} fill={activeTab === 'favorites' ? 'currentColor' : 'none'} />
            {favorites.length > 0 && (
              <span className="mobile-fav-badge text-digital">{favorites.length}</span>
            )}
          </div>
          <span>Favorites</span>
        </button>

        <button
          className={`mobile-nav-item ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('settings');
            setSearchQuery('');
            setSelectedSeriesItem(null);
          }}
        >
          <SettingsIcon size={20} />
          <span>Settings</span>
        </button>
      </nav>

      <style>{`
        .player-column {
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .player-wrapper-container {
          width: 100%;
          height: 100%;
          max-height: 70vh;
          min-height: 400px;
        }
        .player-wrapper-container.placeholder {
          height: 100%;
          max-height: 70vh;
          min-height: 400px;
          max-width: none;
          width: 100%;
        }

        @media (min-width: 1025px) {
          .player-wrapper-container {
            max-height: 90vh;
          }
          .player-wrapper-container.placeholder {
            max-height: 90vh;
          }
        }

        .main-list-panel {
          height: 100%;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          background: rgba(10, 12, 22, 0.4);
        }
        
        .list-search-bar {
          padding: 16px;
          border-bottom: 1px solid var(--border-color);
        }
        .search-icon {
          position: absolute;
          left: 12px;
          top: 50%;
          transform: translateY(-50%);
          color: var(--text-dark);
          pointer-events: none;
        }

        /* Panel body: side-by-side category sidebar + content */
        .panel-body {
          display: flex;
          flex: 1;
          overflow: hidden;
          min-height: 0;
        }

        /* Vertical category sidebar */
        .cat-sidebar {
          flex: 40;
          display: flex;
          flex-direction: column;
          overflow-y: auto;
          border-right: 1px solid var(--border-color);
          background: rgba(0,0,0,0.15);
          padding: 8px 0;
          gap: 8px;
        }
        .cat-sidebar::-webkit-scrollbar { width: 3px; }
        .cat-sidebar-title {
          font-size: 10px;
          font-weight: 700;
          color: var(--text-dark);
          text-transform: uppercase;
          letter-spacing: 0.08em;
          padding: 4px 12px 8px;
        }
        .cat-sidebar-item {
          display: block;
          width: 100%;
          text-align: left;
          background: transparent;
          border: none;
          border-left: 2px solid transparent;
          color: var(--text-muted);
          font-size: 14px;
          font-weight: 500;
          padding: 12px 16px;
          cursor: pointer;
          transition: all 0.15s ease;
          white-space: normal;
          word-wrap: break-word;
          line-height: 1.4;
          font-family: var(--font-sans);
        }
        .cat-sidebar-item:hover {
          background: rgba(255,255,255,0.04);
          color: var(--text-main);
          border-left-color: rgba(255,255,255,0.15);
        }
        .cat-sidebar-item.active {
          background: rgba(0,240,255,0.07);
          border-left-color: var(--primary);
          color: var(--primary);
          font-weight: 600;
        }

        /* Content column to the right of sidebar */
        .content-col {
          flex: 60;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          min-width: 0;
        }

        .list-items-container {
          flex: 1;
          overflow-y: auto;
          padding: 12px;
        }
        
        .list-loading-state, .list-error-state, .list-empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          color: var(--text-muted);
          font-size: 13px;
          text-align: center;
          padding: 40px;
        }
        
        .channels-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        
        .channel-item-card {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px 12px;
          border-radius: var(--radius-sm);
          background: rgba(255,255,255,0.01);
          border: 1px solid var(--border-color);
          cursor: pointer;
          transition: all 0.2s ease;
        }
        .channel-item-card:hover {
          background: rgba(255,255,255,0.04);
          border-color: rgba(255,255,255,0.15);
        }
        .channel-item-card.active {
          background: var(--primary-glow);
          border-color: var(--primary);
          box-shadow: 0 0 10px var(--primary-glow);
        }
        
        .channel-logo-container {
          width: 36px;
          height: 36px;
          border-radius: 4px;
          background: rgba(0,0,0,0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          overflow: hidden;
          flex-shrink: 0;
        }
        .channel-logo-container img {
          width: 100%;
          height: 100%;
          object-fit: contain;
        }
        
        .channel-details {
          flex: 1;
          overflow: hidden;
        }
        .channel-name-txt {
          font-size: 13px;
          font-weight: 600;
          color: #fff;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .channel-item-card.active .channel-name-txt {
          color: var(--primary);
        }
        .channel-category-txt {
          font-size: 11px;
          color: var(--text-dark);
          margin-top: 2px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        
        .fav-btn {
          background: transparent;
          border: none;
          color: var(--text-dark);
          cursor: pointer;
          padding: 4px;
          transition: all 0.2s ease;
        }
        .fav-btn:hover {
          color: #f59e0b;
        }
        .fav-btn.active {
          color: #f59e0b;
        }

        /* VOD & Series Grid */
        .vod-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
          gap: 12px;
        }
        .vod-card {
          cursor: pointer;
          transition: all 0.2s ease;
        }
        .vod-card:hover {
          transform: translateY(-2px);
        }
        .vod-thumbnail {
          aspect-ratio: 2/3;
          border-radius: 6px;
          background: rgba(0,0,0,0.3);
          border: 1px solid var(--border-color);
          overflow: hidden;
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .vod-thumbnail img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
        .vod-overlay-play {
          position: absolute;
          inset: 0;
          background: rgba(0,0,0,0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          opacity: 0;
          transition: opacity 0.2s ease;
        }
        .vod-card:hover .vod-overlay-play {
          opacity: 1;
        }
        .vod-badge-rating {
          position: absolute;
          top: 6px;
          right: 6px;
          background: rgba(0,0,0,0.8);
          color: var(--accent);
          font-size: 8px;
          font-weight: 700;
          padding: 2px 4px;
          border-radius: 4px;
          border: 1px solid rgba(5,255,197,0.3);
        }
        
        .vod-title {
          font-size: 11px;
          font-weight: 600;
          color: #fff;
          margin-top: 6px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        /* Series view details */
        .series-details-header {
          display: flex;
          gap: 16px;
          background: rgba(255,255,255,0.02);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          padding: 12px;
          margin-bottom: 16px;
        }
        
        .seasons-container {
          max-height: 400px;
          overflow-y: auto;
        }
        
        .episode-item {
          display: flex;
          align-items: center;
          padding: 8px 12px;
          background: rgba(255,255,255,0.01);
          border: 1px solid var(--border-color);
          border-radius: 4px;
          cursor: pointer;
          transition: all 0.2s ease;
          font-size: 12px;
        }
        .episode-item:hover {
          background: rgba(255,255,255,0.03);
          border-color: var(--primary);
        }

        /* Mobile Responsive Layout Styles */
        .mobile-header {
          display: none;
          height: 56px;
          background: rgba(10, 12, 22, 0.85);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border-bottom: 1px solid var(--border-color);
          padding: 0 16px;
          align-items: center;
          justify-content: space-between;
          position: sticky;
          top: 0;
          z-index: 40;
        }

        .mobile-bottom-nav {
          display: none;
          height: 60px;
          background: rgba(10, 12, 20, 0.9);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border-top: 1px solid var(--border-color);
          position: fixed;
          bottom: 0;
          left: 0;
          right: 0;
          z-index: 40;
          justify-content: space-around;
          align-items: center;
        }

        .mobile-nav-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          background: transparent;
          border: none;
          color: var(--text-muted);
          font-size: 10px;
          font-weight: 500;
          cursor: pointer;
          gap: 4px;
          transition: all 0.2s ease;
        }

        .mobile-nav-item:hover, .mobile-nav-item.active {
          color: var(--primary);
        }

        .mobile-fav-badge {
          position: absolute;
          top: -4px;
          right: -10px;
          background: var(--secondary);
          color: #fff;
          font-size: 8px;
          padding: 1px 4px;
          border-radius: 6px;
          font-weight: 800;
          box-shadow: 0 0 6px var(--secondary-glow);
        }

        .mobile-logout-btn {
          background: rgba(255,255,255,0.05);
          border: 1px solid var(--border-color);
          color: var(--text-muted);
          font-size: 11px;
          font-weight: 600;
          padding: 4px 10px;
          border-radius: 4px;
          cursor: pointer;
        }
        .mobile-logout-btn:hover {
          color: #f87171;
          border-color: rgba(239,68,68,0.3);
        }

        @media (max-width: 768px) {
          .app-container {
            flex-direction: column;
            overflow: hidden;
            height: 100vh;
            height: 100dvh;
          }
          
          .sidebar-container {
            display: none !important;
          }

          .mobile-header {
            display: flex;
            flex-shrink: 0;
          }

          .mobile-bottom-nav {
            display: flex;
            flex-shrink: 0;
            position: relative;
            bottom: auto;
            left: auto;
            right: auto;
            /* Push above browser address bar on Android/iOS */
            padding-bottom: env(safe-area-inset-bottom, 12px);
            height: calc(60px + env(safe-area-inset-bottom, 12px));
          }

          .main-content {
            flex: 1;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            min-height: 0;
          }

          .dashboard-grid {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 8px;
            gap: 8px;
            overflow: hidden;
            min-height: 0;
          }

          /* Player fixed height on mobile */
          .player-column {
            display: flex !important;
            flex-direction: column !important;
            gap: 0 !important;
            height: auto !important;
            flex-shrink: 0;
            overflow: visible !important;
          }
          
          .player-wrapper-container {
            position: static !important;
            top: auto !important;
            z-index: auto !important;
            background: #000;
            margin: -8px -8px 0 -8px;
            border-radius: 0 !important;
            width: calc(100% + 16px);
            aspect-ratio: 16 / 9;
            height: auto !important;
            max-height: none !important;
            min-height: unset !important;
          }
          .player-wrapper-container.placeholder {
            display: block !important;
            aspect-ratio: 16 / 9;
            height: auto !important;
            max-height: none !important;
            min-height: unset !important;
            margin-bottom: 0;
          }
          .player-wrapper-container .player-wrapper,
          .player-wrapper-container .player-empty-container {
            border-radius: 0 !important;
          }

          /* Channel list panel fills remaining space and scrolls */
          .main-list-panel {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden !important;
            min-height: 0;
            border-radius: var(--radius-sm);
          }
          /* 40/60 split on mobile as well */
          .cat-sidebar {
            flex: 40 !important;
            width: auto !important;
            min-width: 0 !important;
          }
          .cat-sidebar-item {
            font-size: 14px;
            padding: 10px 12px;
          }
          .cat-sidebar-title {
            font-size: 11px;
            padding: 4px 8px 8px;
          }
          .content-col {
            flex: 60 !important;
            min-height: 0;
          }
          .list-items-container {
            flex: 1;
            overflow-y: auto !important;
            -webkit-overflow-scrolling: touch;
            min-height: 0;
            padding-bottom: 12px;
          }
          
          .seasons-container {
            max-height: none !important;
          }
        }
      `}</style>
    </div>
  );
}
