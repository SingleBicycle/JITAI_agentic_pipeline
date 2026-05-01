import { collectVideoFilesFromDirectory } from './lib/videos.js';
import { createStorageClient } from './lib/storage.js';
import { getDom } from './ui/dom.js';
import {
  renderCodingControls,
  renderEventHistory,
  renderFolderStatus,
  renderNoteHistory,
  renderNoteKindOptions,
  renderQueue,
  renderSaveStatus,
  renderTagButtons,
  renderTimeline,
  renderTransport
} from './ui/render.js';
import {
  clearTagForCurrentItem,
  addNoteForCurrentItem,
  createSessionState,
  endEventForCurrentItem,
  eraseLastNoteForCurrentItem,
  eraseLastForCurrentItem,
  getCurrentItem,
  replaceVideoItems,
  selectRelativeVideo,
  selectVideo,
  startEventForCurrentItem,
  startTagForCurrentItem
} from './state/session.js';

const state = createSessionState();
const dom = getDom();
let storage = null;
let activeObjectUrl = null;

function nowIso() {
  return new Date().toISOString();
}

function getCurrentTime() {
  return Number.isFinite(dom.video.currentTime) ? dom.video.currentTime : null;
}

function buildMeta(item) {
  const completedEvents = item.events.filter((event) => event.endTimestampSeconds != null);
  const openEvent = item.events.find((event) => event.endTimestampSeconds == null) ?? null;

  return {
    index: item.index,
    folderName: item.folderName,
    fileName: item.fileName,
    sourceType: item.sourceType,
    createdAt: item.createdAt,
    durationSeconds: item.durationSeconds,
    fileSizeBytes: item.fileSizeBytes,
    mimeType: item.mimeType,
    eventCount: item.events.length,
    completedEventCount: completedEvents.length,
    noteCount: item.notes.length,
    captionCount: item.notes.filter((note) => note.kind === 'caption').length,
    commentCount: item.notes.filter((note) => note.kind === 'comment').length,
    openEventId: openEvent?.id ?? null
  };
}

function buildLabels(item) {
  return {
    videoIndex: item.index,
    fileName: item.fileName,
    events: item.events,
    notes: item.notes
  };
}

async function persistState() {
  if (!storage) return;

  try {
    await storage.writeIndex(state.items.map((item) => ({
      index: item.index,
      fileName: item.fileName,
      sourceType: item.sourceType,
      folderName: item.folderName,
      createdAt: item.createdAt
    })));

    for (const item of state.items) {
      await storage.writeVideoFiles({
        item,
        meta: buildMeta(item),
        labels: buildLabels(item)
      });
    }

    state.lastSaveError = null;
  } catch (error) {
    state.lastSaveError = error instanceof Error ? error.message : String(error);
  }

  renderSaveStatus(dom, state);
}

function renderCurrent() {
  const item = getCurrentItem(state);
  const currentTimeSeconds = getCurrentTime();

  renderFolderStatus(dom, state);
  renderSaveStatus(dom, state);
  renderQueue(dom, state);
  renderTransport(dom, state);
  renderCodingControls(dom, item);
  renderEventHistory(dom, item);
  renderNoteHistory(dom, item);
  renderTimeline(dom, item ? {
    ...item,
    currentTimeSeconds: currentTimeSeconds ?? 0
  } : null);
}

async function loadCurrentItem() {
  const item = getCurrentItem(state);
  if (!item) {
    dom.playerStatus.textContent = 'Choose a video folder to begin.';
    dom.video.removeAttribute('src');
    renderCurrent();
    return;
  }

  if (activeObjectUrl) {
    URL.revokeObjectURL(activeObjectUrl);
    activeObjectUrl = null;
  }

  const file = await item.fileHandle.getFile();
  item.fileSizeBytes = file.size;
  item.mimeType = file.type || '';
  activeObjectUrl = URL.createObjectURL(file);
  dom.video.src = activeObjectUrl;
  dom.video.load();
  dom.playerStatus.textContent = `Loaded ${item.index}: ${item.fileName}`;
  renderCurrent();
  await persistState();
}

async function chooseVideoFolder() {
  if (!window.showDirectoryPicker) {
    dom.playerStatus.textContent = 'Folder access requires Chrome or Edge on localhost.';
    return;
  }

  state.videoDirectoryHandle = await window.showDirectoryPicker({ mode: 'readwrite' });
  storage = createStorageClient(state.videoDirectoryHandle);
  const items = await collectVideoFilesFromDirectory(state.videoDirectoryHandle, nowIso);
  replaceVideoItems(state, items);
  dom.playerStatus.textContent = items.length
    ? `Loaded ${items.length} video${items.length === 1 ? '' : 's'} from folder.`
    : 'No supported video files found in that folder.';
  renderCurrent();
  await loadCurrentItem();
}

async function recordAndPersist(action) {
  const currentTime = getCurrentTime();
  if (currentTime == null) return;

  action(currentTime);
  renderCurrent();
  await persistState();
}

dom.chooseFolderButton.addEventListener('click', async () => {
  try {
    await chooseVideoFolder();
  } catch (error) {
    if (error?.name === 'AbortError') return;
    dom.playerStatus.textContent = error instanceof Error ? error.message : String(error);
  }
});

dom.queueList.addEventListener('click', async (event) => {
  const button = event.target.closest('[data-select-index]');
  if (!button) return;
  selectVideo(state, button.dataset.selectIndex);
  await loadCurrentItem();
});

dom.previousButton.addEventListener('click', async () => {
  selectRelativeVideo(state, -1);
  await loadCurrentItem();
});

dom.nextButton.addEventListener('click', async () => {
  selectRelativeVideo(state, 1);
  await loadCurrentItem();
});

dom.startClipButton.addEventListener('click', async () => {
  await recordAndPersist((timestampSeconds) => {
    startEventForCurrentItem(state, {
      id: `e${state.nextEventNumber++}`,
      timestampSeconds,
      createdAt: nowIso()
    });
  });
});

dom.endClipButton.addEventListener('click', async () => {
  await recordAndPersist((timestampSeconds) => {
    endEventForCurrentItem(state, {
      timestampSeconds,
      createdAt: nowIso()
    });
  });
});

dom.clearTagButton.addEventListener('click', async () => {
  await recordAndPersist((timestampSeconds) => {
    clearTagForCurrentItem(state, {
      timestampSeconds,
      createdAt: nowIso()
    });
  });
});

dom.undoButton.addEventListener('click', async () => {
  eraseLastForCurrentItem(state);
  renderCurrent();
  await persistState();
});

dom.tagActions.addEventListener('click', async (event) => {
  const button = event.target.closest('[data-tag]');
  if (!button) return;

  await recordAndPersist((timestampSeconds) => {
    startTagForCurrentItem(state, {
      id: `s${state.nextSegmentNumber++}`,
      tag: button.dataset.tag,
      timestampSeconds,
      createdAt: nowIso()
    });
  });
});

dom.addNoteButton.addEventListener('click', async () => {
  const currentTime = getCurrentTime();
  const text = dom.noteTextInput.value.trim();
  if (currentTime == null || !text) return;

  addNoteForCurrentItem(state, {
    id: `n${state.nextNoteNumber++}`,
    kind: dom.noteKindSelect.value,
    timestampSeconds: currentTime,
    text,
    createdAt: nowIso()
  });
  dom.noteTextInput.value = '';
  renderCurrent();
  await persistState();
});

dom.eraseNoteButton.addEventListener('click', async () => {
  eraseLastNoteForCurrentItem(state);
  renderCurrent();
  await persistState();
});

dom.video.addEventListener('loadedmetadata', async () => {
  const item = getCurrentItem(state);
  if (!item) return;
  item.durationSeconds = Number.isFinite(dom.video.duration) ? dom.video.duration : null;
  renderCurrent();
  await persistState();
});

dom.video.addEventListener('timeupdate', renderCurrent);
dom.video.addEventListener('seeked', renderCurrent);

renderTagButtons(dom);
renderNoteKindOptions(dom);
renderCurrent();
