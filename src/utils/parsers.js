/**
 * Parse raw M3U / M3U Plus playlist text into structured categories and channels.
 */
export function parseM3U(rawText) {
  const channels = [];
  const categoriesMap = new Set();
  
  if (!rawText) return { channels, categories: [] };

  const lines = rawText.split(/\r?\n/);
  let currentChannel = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    if (line.startsWith('#EXTM3U')) {
      // Playlist header, can contain metadata but we usually skip it
      continue;
    }

    if (line.startsWith('#EXTINF:')) {
      // Parse EXTINF line
      currentChannel = {};
      
      // Parse length (usually -1 for live TV)
      const durationMatch = line.match(/#EXTINF:([-]?\d+)/);
      if (durationMatch) {
        currentChannel.duration = parseInt(durationMatch[1], 10);
      }

      // Parse attributes
      currentChannel.logo = getAttributeValue(line, 'tvg-logo') || getAttributeValue(line, 'tvg-logo-url');
      currentChannel.id = getAttributeValue(line, 'tvg-id');
      currentChannel.tvgName = getAttributeValue(line, 'tvg-name');
      currentChannel.category = getAttributeValue(line, 'group-title') || 'Uncategorized';
      
      // Extract channel name (everything after the last comma of the line)
      const commaIndex = line.lastIndexOf(',');
      if (commaIndex !== -1) {
        currentChannel.name = line.substring(commaIndex + 1).trim();
      } else {
        currentChannel.name = 'Unknown Channel';
      }

      // If tvgName is set but name is missing or placeholder
      if (!currentChannel.name && currentChannel.tvgName) {
        currentChannel.name = currentChannel.tvgName;
      }
    } else if (line.startsWith('#')) {
      // Skip other tags (like #EXTGRP, #EXTMYT, etc) unless they provide group information
      if (line.startsWith('#EXTGRP:') && currentChannel) {
        currentChannel.category = line.replace('#EXTGRP:', '').trim();
      }
    } else {
      // Must be the URL
      if (currentChannel) {
        currentChannel.url = line;
        
        // Filter: only fetch TV (exclude movies and series VODs)
        const isVod = line.includes('/movie/') || line.includes('/series/');
        if (!isVod) {
          // Generate a unique client-side ID if one doesn't exist
          currentChannel.uniqueId = currentChannel.id || `ch-${Math.random().toString(36).substr(2, 9)}`;
          channels.push(currentChannel);
          categoriesMap.add(currentChannel.category);
        }
        currentChannel = null;
      }
    }
  }

  return {
    channels,
    categories: Array.from(categoriesMap).sort(),
  };
}

/**
 * Helper to extract attributes like tvg-logo="url" from #EXTINF lines
 */
function getAttributeValue(line, attributeName) {
  const regex = new RegExp(`${attributeName}\\s*=\\s*["']([^"']+)["']`, 'i');
  const match = line.match(regex);
  return match ? match[1] : null;
}

/**
 * High-performance parser for XMLTV EPG data.
 * Returns a dictionary mapping tvg-id (channel) to an array of program objects.
 */
export function parseXMLTV(xmlText) {
  const epgData = {};
  if (!xmlText) return epgData;

  try {
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
    
    // Check for parse errors
    const parseError = xmlDoc.getElementsByTagName('parsererror');
    if (parseError.length > 0) {
      console.error('XML parsing error:', parseError[0].textContent);
      return epgData;
    }

    const programmes = xmlDoc.getElementsByTagName('programme');
    
    for (let i = 0; i < programmes.length; i++) {
      const progNode = programmes[i];
      const channelId = progNode.getAttribute('channel');
      if (!channelId) continue;

      const start = parseXMLTVDate(progNode.getAttribute('start'));
      const stop = parseXMLTVDate(progNode.getAttribute('stop'));
      
      const titleNode = progNode.getElementsByTagName('title')[0];
      const title = titleNode ? titleNode.textContent : 'No Title';
      
      const descNode = progNode.getElementsByTagName('desc')[0];
      const desc = descNode ? descNode.textContent : '';

      const categoryNode = progNode.getElementsByTagName('category')[0];
      const category = categoryNode ? categoryNode.textContent : '';

      const program = {
        start,
        stop,
        title,
        desc,
        category,
      };

      if (!epgData[channelId]) {
        epgData[channelId] = [];
      }
      epgData[channelId].push(program);
    }

    // Sort programs for each channel chronologically
    for (const channelId in epgData) {
      epgData[channelId].sort((a, b) => a.start - b.start);
    }
  } catch (e) {
    console.error('Failed to parse XMLTV EPG:', e);
  }

  return epgData;
}

/**
 * Parse XMLTV date string: e.g. "20260612123000 +0200" or "20260612123000"
 */
function parseXMLTVDate(dateStr) {
  if (!dateStr) return new Date();
  
  // Format: YYYYMMDDHHMMSS [+/-HHMM]
  const match = dateStr.match(/^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\s*(.*)$/);
  if (!match) return new Date(dateStr);

  const [_, year, month, day, hour, minute, second, tz] = match;
  
  // Create ISO format: YYYY-MM-DDTHH:MM:SS
  const isoStr = `${year}-${month}-${day}T${hour}:${minute}:${second}`;
  
  if (tz) {
    // Convert timezone offset like +0200 to +02:00 or -0500 to -05:00
    const tzMatch = tz.match(/^([+-])(\d{2})(\d{2})$/);
    if (tzMatch) {
      const [__, sign, tzHour, tzMin] = tzMatch;
      return new Date(`${isoStr}${sign}${tzHour}:${tzMin}`);
    }
  }

  // Fallback to local timezone parse
  return new Date(
    parseInt(year, 10),
    parseInt(month, 10) - 1,
    parseInt(day, 10),
    parseInt(hour, 10),
    parseInt(minute, 10),
    parseInt(second, 10)
  );
}

/**
 * Format Xtream API lists into normalized channel objects.
 */
export function formatXtreamLiveStream(stream, hostUrl, username, password, format = 'ts') {
  return {
    uniqueId: `xtream-live-${stream.stream_id}`,
    id: stream.epg_channel_id || `xtream-${stream.stream_id}`,
    name: stream.name,
    logo: stream.stream_icon,
    category: stream.category_name || 'Uncategorized',
    categoryId: stream.category_id,
    url: `${hostUrl}/live/${username}/${password}/${stream.stream_id}.${format}`,
    streamId: stream.stream_id,
    type: 'live'
  };
}

export function formatXtreamMovie(movie, hostUrl, username, password) {
  const ext = movie.container_extension || 'mp4';
  return {
    uniqueId: `xtream-movie-${movie.stream_id}`,
    id: `xtream-movie-${movie.stream_id}`,
    name: movie.name,
    logo: movie.stream_icon,
    category: movie.category_name || 'Movies',
    categoryId: movie.category_id,
    url: `${hostUrl}/movie/${username}/${password}/${movie.stream_id}.${ext}`,
    streamId: movie.stream_id,
    rating: movie.rating,
    year: movie.year,
    type: 'movie'
  };
}

export function formatXtreamSeries(series) {
  return {
    uniqueId: `xtream-series-${series.series_id}`,
    id: `xtream-series-${series.series_id}`,
    name: series.name,
    logo: series.cover,
    category: series.category_name || 'TV Series',
    categoryId: series.category_id,
    seriesId: series.series_id,
    rating: series.rating,
    releaseDate: series.releaseDate,
    type: 'series'
  };
}
