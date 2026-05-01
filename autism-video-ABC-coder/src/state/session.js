import {
  clearSegmentTag,
  endEventClip,
  eraseLastAnnotation,
  startEventClip,
  startSegmentTag
} from '../lib/annotations.js';
import {
  addHumanNote,
  eraseLastHumanNote
} from '../lib/notes.js';

export function createSessionState() {
  return {
    videoDirectoryHandle: null,
    items: [],
    currentIndex: null,
    lastSaveError: null,
    nextEventNumber: 1,
    nextSegmentNumber: 1,
    nextNoteNumber: 1
  };
}

function normalizeItem(item) {
  return {
    ...item,
    events: item.events ?? [],
    notes: item.notes ?? [],
    durationSeconds: item.durationSeconds ?? null,
    fileSizeBytes: item.fileSizeBytes ?? null,
    mimeType: item.mimeType ?? ''
  };
}

export function appendVideoItems(state, items) {
  state.items.push(...items.map(normalizeItem));

  if (!state.currentIndex && state.items.length > 0) {
    state.currentIndex = state.items[0].index;
  }
}

export function replaceVideoItems(state, items) {
  state.items = [];
  state.currentIndex = null;
  appendVideoItems(state, items);
  state.nextEventNumber = 1;
  state.nextSegmentNumber = 1;
  state.nextNoteNumber = 1;
}

export function selectVideo(state, index) {
  state.currentIndex = index;
}

export function selectRelativeVideo(state, offset) {
  const currentPosition = state.items.findIndex((item) => item.index === state.currentIndex);
  if (currentPosition === -1) return;

  const nextPosition = currentPosition + offset;
  if (nextPosition < 0 || nextPosition >= state.items.length) return;
  state.currentIndex = state.items[nextPosition].index;
}

export function getCurrentItem(state) {
  return state.items.find((item) => item.index === state.currentIndex) ?? null;
}

export function startEventForCurrentItem(state, payload) {
  const item = getCurrentItem(state);
  if (!item) return;

  item.events = startEventClip(item.events, {
    ...payload,
    id: payload.id ?? `e${state.nextEventNumber++}`
  });
}

export function startTagForCurrentItem(state, payload) {
  const item = getCurrentItem(state);
  if (!item) return;

  item.events = startSegmentTag(item.events, {
    ...payload,
    id: payload.id ?? `s${state.nextSegmentNumber++}`
  });
}

export function clearTagForCurrentItem(state, payload) {
  const item = getCurrentItem(state);
  if (!item) return;
  item.events = clearSegmentTag(item.events, payload);
}

export function endEventForCurrentItem(state, payload) {
  const item = getCurrentItem(state);
  if (!item) return;
  item.events = endEventClip(item.events, payload);
}

export function eraseLastForCurrentItem(state) {
  const item = getCurrentItem(state);
  if (!item) return;
  item.events = eraseLastAnnotation(item.events);
}

export function addNoteForCurrentItem(state, payload) {
  const item = getCurrentItem(state);
  if (!item) return;

  item.notes = addHumanNote(item.notes, {
    ...payload,
    id: payload.id ?? `n${state.nextNoteNumber++}`
  });
}

export function eraseLastNoteForCurrentItem(state) {
  const item = getCurrentItem(state);
  if (!item) return;
  item.notes = eraseLastHumanNote(item.notes);
}
