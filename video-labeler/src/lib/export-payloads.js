function hasOpenStartMarker(item) {
  const closedStartIds = new Set(item.clips.map((clip) => clip.startMarkerId));
  return item.markers.some((marker) => marker.kind === 'start' && !closedStartIds.has(marker.id));
}

export function buildMeta(item) {
  return {
    index: item.index,
    folderName: item.folderName,
    sourceUrl: item.sourceUrl,
    sourceType: item.sourceType,
    title: item.title,
    titleSource: item.titleSource,
    createdAt: item.createdAt,
    durationSeconds: item.durationSeconds ?? null,
    seekable: item.seekable ?? false,
    clipCount: item.clips.length,
    interactionEpisodeCount: item.interactionEpisodes?.length ?? 0,
    hasOpenStartMarker: hasOpenStartMarker(item),
    capabilities: item.capabilities ?? { timing: false, duration: false }
  };
}

export function buildLabelsPayload(item) {
  return {
    videoIndex: item.index,
    sourceUrl: item.sourceUrl,
    markers: item.markers,
    clips: item.clips,
    interactionEpisodes: item.interactionEpisodes ?? []
  };
}
