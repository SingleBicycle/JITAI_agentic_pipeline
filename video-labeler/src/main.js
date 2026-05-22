import { getDom } from './ui/dom.js';
import {
  renderQueue,
  renderSaveStatus,
  renderImportReport,
  renderInteractionEpisodeHistory
} from './ui/render.js';
import {
  createSessionState,
  appendImportedUrls,
  selectVideo,
  getCurrentItem,
  selectRelativeVideo,
  recordInteractionEpisodeForCurrentItem,
  eraseInteractionEpisodeForCurrentItem
} from './state/session.js';
import { parseImportedText } from './lib/parser.js';
import { appendIndexedUrls } from './lib/indexer.js';
import { createStorageClient } from './lib/storage.js';
import { buildMeta, buildLabelsPayload } from './lib/export-payloads.js';
import { createPlayerController } from './player/create-player-controller.js';

const state = createSessionState();
const dom = getDom();
const player = createPlayerController(dom);
let storage = null;
const labelsConfig = await fetch(new URL('../config/labels.json', import.meta.url)).then((response) => response.json());

function nowIso() {
  return new Date().toISOString();
}

function renderCurrentItemHistories() {
  const item = getCurrentItem(state);
  renderInteractionEpisodeHistory(dom, item);
}

function setSelectOptions(select, options) {
  select.innerHTML = options.map((option) => `
    <option value="${option}">${option}</option>
  `).join('');
}

function setCurrentTimeField(input) {
  const currentTime = player.getCurrentTime();
  if (currentTime == null) return false;
  input.value = currentTime.toFixed(2);
  return true;
}

function numericRange(startInput, endInput) {
  if (!startInput.value || !endInput.value) return null;
  return `${Number(startInput.value).toFixed(2)}-${Number(endInput.value).toFixed(2)}`;
}

function clearInteractionForm() {
  dom.cueActorInput.value = '';
  dom.candidateRecipientInput.value = '';
  dom.cueStartInput.value = '';
  dom.cueEndInput.value = '';
  dom.responseStartInput.value = '';
  dom.responseEndInput.value = '';
  dom.evidenceSpansInput.value = '';
  dom.episodeDescriptionInput.value = '';
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
          ...buildLabelsPayload(item)
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
    renderInteractionEpisodeHistory(dom, null);
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
  renderCurrentItemHistories();
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
    interactionEpisodes: [],
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

dom.timeCaptureButtons.forEach((button) => {
  button.addEventListener('click', () => {
    const input = document.querySelector(`#${button.dataset.timeTarget}`);
    setCurrentTimeField(input);
  });
});

dom.useCueResponseEvidenceButton.addEventListener('click', () => {
  const spans = [
    numericRange(dom.cueStartInput, dom.cueEndInput),
    numericRange(dom.responseStartInput, dom.responseEndInput)
  ].filter(Boolean);
  dom.evidenceSpansInput.value = spans.join('; ');
});

dom.saveInteractionButton.addEventListener('click', async () => {
  try {
    recordInteractionEpisodeForCurrentItem(state, {
      createdAt: nowIso(),
      cueStartSeconds: dom.cueStartInput.value,
      cueEndSeconds: dom.cueEndInput.value,
      cueActor: dom.cueActorInput.value,
      candidateRecipient: dom.candidateRecipientInput.value,
      cueType: dom.cueTypeSelect.value,
      accessLabel: dom.accessLabelSelect.value,
      responseLabel: dom.responseLabelSelect.value,
      responseStartSeconds: dom.responseStartInput.value,
      responseEndSeconds: dom.responseEndInput.value,
      responseType: dom.responseTypeSelect.value,
      cueResponseLink: dom.cueResponseLinkSelect.value,
      evidenceSpansText: dom.evidenceSpansInput.value,
      ambiguityLabel: dom.ambiguityLabelSelect.value,
      description: dom.episodeDescriptionInput.value
    });
    clearInteractionForm();
    dom.playerStatus.textContent = 'Interaction episode saved';
  } catch (error) {
    dom.playerStatus.textContent = error instanceof Error ? error.message : String(error);
  }

  renderCurrentItemHistories();
  await persistState();
});

dom.eraseInteractionButton.addEventListener('click', async () => {
  eraseInteractionEpisodeForCurrentItem(state);
  renderCurrentItemHistories();
  await persistState();
});

setSelectOptions(dom.cueTypeSelect, labelsConfig.socialInteraction.cueTypes);
setSelectOptions(dom.accessLabelSelect, labelsConfig.socialInteraction.accessLabels);
setSelectOptions(dom.responseLabelSelect, labelsConfig.socialInteraction.responseLabels);
setSelectOptions(dom.responseTypeSelect, labelsConfig.socialInteraction.responseTypes);
setSelectOptions(dom.cueResponseLinkSelect, labelsConfig.socialInteraction.cueResponseLinks);
setSelectOptions(dom.ambiguityLabelSelect, labelsConfig.socialInteraction.ambiguityLabels);

renderQueue(dom, state);
renderSaveStatus(dom, state);
renderInteractionEpisodeHistory(dom, null);
renderImportReport(dom, state);
