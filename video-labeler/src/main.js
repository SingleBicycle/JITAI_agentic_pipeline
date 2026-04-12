import { getDom } from './ui/dom.js';
import {
  renderQueue,
  renderSaveStatus,
  renderImportReport,
  renderMarkerHistory,
  renderClipHistory
} from './ui/render.js';
import {
  createSessionState,
  appendImportedUrls,
  selectVideo,
  getCurrentItem,
  selectRelativeVideo,
  addMarkerForCurrentItem,
  eraseLastForCurrentItem,
  describeLastClipForCurrentItem
} from './state/session.js';
import { parseImportedText } from './lib/parser.js';
import { appendIndexedUrls } from './lib/indexer.js';
import { createStorageClient } from './lib/storage.js';
import { createPlayerController } from './player/create-player-controller.js';

const state = createSessionState();
const dom = getDom();
const player = createPlayerController(dom);
let storage = null;
const labelsConfig = await fetch(new URL('../config/labels.json', import.meta.url)).then((response) => response.json());

function nowIso() {
  return new Date().toISOString();
}

function hasOpenStartMarker(item) {
  const closedStartIds = new Set(item.clips.map((clip) => clip.startMarkerId));
  return item.markers.some((marker) => marker.kind === 'start' && !closedStartIds.has(marker.id));
}

function buildMeta(item) {
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
    hasOpenStartMarker: hasOpenStartMarker(item),
    capabilities: item.capabilities ?? { timing: false, duration: false }
  };
}

async function persistState() {
  if (!storage) return;

  try {
    await storage.writeIndex(state.items.map((item) => ({
      index: item.index,
      sourceUrl: item.sourceUrl,
      sourceType: item.sourceType,
      folderName: item.folderName,
      createdAt: item.createdAt
    })));

    for (const item of state.items) {
      await storage.writeVideoFiles({
        item,
        meta: buildMeta(item),
        labels: {
          videoIndex: item.index,
          sourceUrl: item.sourceUrl,
          markers: item.markers,
          clips: item.clips
        }
      });
    }

    state.lastSaveError = null;
  } catch (error) {
    state.lastSaveError = error instanceof Error ? error.message : String(error);
  }

  renderSaveStatus(dom, state);
}

async function loadCurrentItem() {
  const item = getCurrentItem(state);
  if (!item) {
    dom.playerStatus.textContent = 'No video selected';
    renderMarkerHistory(dom, null);
    renderClipHistory(dom, null);
    return;
  }

  const detected = await player.load(item);
  item.sourceType = detected.sourceType;
  item.capabilities = player.getCapabilities();
  item.durationSeconds = player.getDuration();
  item.seekable = player.isSeekable();
  const titleInfo = player.getTitleInfo(item);
  item.title = titleInfo.title;
  item.titleSource = titleInfo.titleSource;
  dom.playerStatus.textContent = item.capabilities.timing
    ? `Loaded ${item.index} (${item.sourceType})`
    : `Loaded ${item.index}, but timestamp capture is unavailable for this source`;

  renderQueue(dom, state);
  renderMarkerHistory(dom, item);
  renderClipHistory(dom, item);
  await persistState();
}

async function importUrlsFromText(rawText) {
  const parsed = parseImportedText(rawText);
  const indexed = appendIndexedUrls(state.items, parsed.urls);

  state.importErrors = parsed.rejected;
  state.importSummary = {
    addedCount: indexed.added.length,
    duplicateCount: parsed.urls.length - indexed.added.length,
    rejectedCount: parsed.rejected.length
  };

  appendImportedUrls(state, indexed.added.map((item) => ({
    ...item,
    createdAt: nowIso(),
    markers: [],
    clips: [],
    title: '',
    titleSource: 'unknown'
  })));

  renderQueue(dom, state);
  renderImportReport(dom, state);
  await persistState();
  await loadCurrentItem();
}

dom.importTextButton.addEventListener('click', async () => {
  await importUrlsFromText(dom.linkInput.value);
});

dom.fileInput.addEventListener('change', async () => {
  const file = dom.fileInput.files?.[0];
  if (!file) return;
  await importUrlsFromText(await file.text());
  dom.fileInput.value = '';
});

dom.chooseFolderButton.addEventListener('click', async () => {
  state.outputDirectoryHandle = await window.showDirectoryPicker();
  storage = createStorageClient(state.outputDirectoryHandle);
  renderSaveStatus(dom, state);
  await persistState();
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

dom.captureMarkerButton.addEventListener('click', async () => {
  const currentTime = player.getCurrentTime();
  if (currentTime == null) return;

  addMarkerForCurrentItem(state, {
    id: `m${state.nextMarkerNumber++}`,
    timestampSeconds: currentTime,
    createdAt: nowIso(),
    kind: 'marker'
  });

  const item = getCurrentItem(state);
  renderMarkerHistory(dom, item);
  renderClipHistory(dom, item);
  await persistState();
});

dom.markerActions.innerHTML = labelsConfig.defaults.map((label) => `
  <button type="button" data-marker-kind="${label}">${label}</button>
`).join('');

dom.markerActions.addEventListener('click', async (event) => {
  const button = event.target.closest('[data-marker-kind]');
  if (!button) return;

  const currentTime = player.getCurrentTime();
  if (button.dataset.markerKind === 'erase') {
    eraseLastForCurrentItem(state);
  } else {
    if (currentTime == null) return;
    addMarkerForCurrentItem(state, {
      id: `m${state.nextMarkerNumber++}`,
      timestampSeconds: currentTime,
      createdAt: nowIso(),
      kind: button.dataset.markerKind
    });
  }

  const item = getCurrentItem(state);
  renderMarkerHistory(dom, item);
  renderClipHistory(dom, item);
  await persistState();
});

dom.applyDescriptionButton.addEventListener('click', async () => {
  const description = dom.clipDescriptionInput.value.trim();
  if (!description) return;

  const item = getCurrentItem(state);
  if (!item?.clips.length) {
    dom.playerStatus.textContent = 'Create a start/end clip before applying a description.';
    return;
  }

  describeLastClipForCurrentItem(state, description);
  dom.clipDescriptionInput.value = '';
  renderClipHistory(dom, getCurrentItem(state));
  await persistState();
});

renderQueue(dom, state);
renderSaveStatus(dom, state);
renderMarkerHistory(dom, null);
renderClipHistory(dom, null);
renderImportReport(dom, state);
