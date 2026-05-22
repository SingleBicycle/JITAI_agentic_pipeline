import {
  createMarker,
  applyMarkerAction,
  applyClipDescription,
  applyLabelAction,
  createInteractionEpisode,
  applyInteractionEpisodeAction
} from '../lib/labels.js';

export function createSessionState() {
  return {
    outputDirectoryHandle: null,
    items: [],
    currentIndex: null,
    importErrors: [],
    importSummary: null,
    lastSaveError: null,
    nextMarkerNumber: 1,
    nextClipNumber: 1,
    nextEpisodeNumber: 1
  };
}

export function appendImportedUrls(state, items) {
  state.items.push(...items.map((item) => ({
    ...item,
    markers: item.markers ?? [],
    clips: item.clips ?? [],
    interactionEpisodes: item.interactionEpisodes ?? [],
    title: item.title ?? '',
    titleSource: item.titleSource ?? 'unknown',
    labels: item.labels ?? []
  })));

  if (!state.currentIndex && state.items.length > 0) {
    state.currentIndex = state.items[0].index;
  }
}

export function selectVideo(state, index) {
  state.currentIndex = index;
}

export function getCurrentItem(state) {
  return state.items.find((item) => item.index === state.currentIndex) ?? null;
}

export function addMarkerForCurrentItem(state, payload) {
  const item = getCurrentItem(state);
  if (!item) return;

  const result = applyMarkerAction(
    { markers: item.markers, clips: item.clips },
    {
      marker: createMarker(payload),
      clipId: `c${state.nextClipNumber++}`
    }
  );

  item.markers = result.markers;
  item.clips = result.clips;
}

export function eraseLastForCurrentItem(state) {
  const item = getCurrentItem(state);
  if (!item) return;

  const result = applyMarkerAction(
    { markers: item.markers, clips: item.clips },
    { eraseLast: true }
  );

  item.markers = result.markers;
  item.clips = result.clips;
}

export function describeLastClipForCurrentItem(state, description) {
  const item = getCurrentItem(state);
  if (!item) return;
  item.clips = applyClipDescription(item.clips, description);
}

export function recordInteractionEpisodeForCurrentItem(state, payload) {
  const item = getCurrentItem(state);
  if (!item) return;

  item.interactionEpisodes = applyInteractionEpisodeAction(
    item.interactionEpisodes,
    {
      episode: createInteractionEpisode({
        ...payload,
        id: `ie${state.nextEpisodeNumber++}`
      })
    }
  );
}

export function eraseInteractionEpisodeForCurrentItem(state) {
  const item = getCurrentItem(state);
  if (!item) return;

  item.interactionEpisodes = applyInteractionEpisodeAction(
    item.interactionEpisodes,
    { eraseLast: true }
  );
}

export function recordLabelForCurrentItem(state, payload) {
  const item = getCurrentItem(state);
  if (!item) return;
  item.labels = applyLabelAction(item.labels, payload);
}

export function eraseLabelForCurrentItem(state) {
  const item = getCurrentItem(state);
  if (!item) return;
  item.labels = applyLabelAction(item.labels, { action: 'erase' });
}

export function selectRelativeVideo(state, offset) {
  const currentPosition = state.items.findIndex((item) => item.index === state.currentIndex);
  if (currentPosition === -1) return;

  const nextPosition = currentPosition + offset;
  if (nextPosition < 0 || nextPosition >= state.items.length) return;

  state.currentIndex = state.items[nextPosition].index;
}
