function getYouTubeId(url) {
  const parsed = new URL(url);
  if (parsed.hostname.includes('youtu.be')) {
    return parsed.pathname.slice(1) || null;
  }
  if (parsed.hostname.includes('youtube.com')) {
    const pathMatch = parsed.pathname.match(/^\/(?:shorts|embed)\/([^/]+)/);
    if (pathMatch) {
      return pathMatch[1];
    }
    return parsed.searchParams.get('v');
  }
  return null;
}

export function detectSource(url) {
  const youtubeId = getYouTubeId(url);
  if (youtubeId) {
    return { sourceType: 'youtube', embedId: youtubeId };
  }

  if (/\.(mp4|webm|ogg)(\?|#|$)/i.test(url)) {
    return { sourceType: 'html5-video', embedId: null };
  }

  return { sourceType: 'unsupported', embedId: null };
}

export function deriveTitleFromUrl(url) {
  const parsed = new URL(url);
  const lastSegment = parsed.pathname.split('/').filter(Boolean).at(-1);

  return {
    title: lastSegment || parsed.hostname,
    titleSource: lastSegment ? 'filename' : 'url'
  };
}
