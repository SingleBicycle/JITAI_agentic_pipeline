import {
  ABC_TAGS,
  getActiveSegment,
  getOpenEventClip
} from '../lib/annotations.js';
import { NOTE_KINDS } from '../lib/notes.js';
import { buildTimelineBands } from '../lib/timeline.js';

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function formatSeconds(value) {
  return `${Number(value).toFixed(2)}s`;
}

function formatDuration(value) {
  if (value == null || Number.isNaN(value)) return 'duration pending';
  return formatSeconds(value);
}

function formatPercent(value) {
  return `${Number(value).toFixed(4)}%`;
}

function countCompletedEvents(item) {
  return (item?.events ?? []).filter((event) => event.endTimestampSeconds != null).length;
}

function countNotes(item) {
  return (item?.notes ?? []).length;
}

export function renderFolderStatus(dom, state) {
  if (!dom.folderStatus) return;

  if (!state.videoDirectoryHandle) {
    dom.folderStatus.textContent = 'No video folder selected';
    return;
  }

  dom.folderStatus.textContent = `${state.items.length} video${state.items.length === 1 ? '' : 's'} loaded`;
}

export function renderSaveStatus(dom, state) {
  if (!dom.saveStatus) return;

  if (state.lastSaveError) {
    dom.saveStatus.textContent = `Save error: ${state.lastSaveError}`;
    dom.saveStatus.dataset.state = 'error';
    return;
  }

  dom.saveStatus.textContent = state.videoDirectoryHandle
    ? 'Annotations and notes save to the selected folder'
    : 'Choose a folder to enable saving';
  dom.saveStatus.dataset.state = state.videoDirectoryHandle ? 'ready' : 'idle';
}

export function renderQueue(dom, state) {
  dom.queueList.innerHTML = state.items.map((item) => `
    <li>
      <button
        type="button"
        class="queue-button${item.index === state.currentIndex ? ' is-active' : ''}"
        data-select-index="${escapeHtml(item.index)}"
      >
          <span class="queue-index">${escapeHtml(item.index)}</span>
        <span class="queue-copy">
          <strong>${escapeHtml(item.fileName)}</strong>
          <span>${countCompletedEvents(item)} event${countCompletedEvents(item) === 1 ? '' : 's'} · ${countNotes(item)} note${countNotes(item) === 1 ? '' : 's'} · ${escapeHtml(formatDuration(item.durationSeconds))}</span>
        </span>
      </button>
    </li>
  `).join('');
}

export function renderTransport(dom, state) {
  const hasItems = state.items.length > 0;
  const currentPosition = state.items.findIndex((item) => item.index === state.currentIndex);
  dom.previousButton.disabled = !hasItems || currentPosition <= 0;
  dom.nextButton.disabled = !hasItems || currentPosition === -1 || currentPosition >= state.items.length - 1;
}

export function renderCodingControls(dom, item) {
  const openEvent = item ? getOpenEventClip(item.events) : null;
  const activeSegment = item ? getActiveSegment(item.events) : null;
  const hasItem = Boolean(item);

  dom.startClipButton.disabled = !hasItem || Boolean(openEvent);
  dom.endClipButton.disabled = !hasItem || !openEvent;
  dom.clearTagButton.disabled = !hasItem || !activeSegment;
  dom.undoButton.disabled = !hasItem || !(item.events ?? []).length;

  if (dom.noteKindSelect) dom.noteKindSelect.disabled = !hasItem;
  if (dom.noteTextInput) dom.noteTextInput.disabled = !hasItem;
  if (dom.addNoteButton) dom.addNoteButton.disabled = !hasItem;
  if (dom.eraseNoteButton) dom.eraseNoteButton.disabled = !hasItem || !(item.notes ?? []).length;

  for (const button of dom.tagButtons) {
    const tag = button.dataset.tag;
    button.disabled = !hasItem || !openEvent;
    button.classList.toggle('is-active', activeSegment?.tag === tag);
  }
}

export function renderEventHistory(dom, item) {
  if (!item || !item.events.length) {
    dom.eventsList.innerHTML = '<li class="empty-state">No event clips yet.</li>';
    return;
  }

  dom.eventsList.innerHTML = item.events.map((event) => {
    const eventEnd = event.endTimestampSeconds == null ? 'open' : formatSeconds(event.endTimestampSeconds);
    const segments = event.segments.length
      ? event.segments.map((segment) => `
          <li>
            <span class="tag-chip tag-${escapeHtml(segment.tag)}">${escapeHtml(segment.tag)}</span>
            <span>${formatSeconds(segment.startTimestampSeconds)} → ${segment.endTimestampSeconds == null ? 'open' : formatSeconds(segment.endTimestampSeconds)}</span>
          </li>
        `).join('')
      : '<li class="empty-state">No ABC segments in this clip.</li>';

    return `
      <li class="event-card">
        <div class="event-card-header">
          <strong>Event ${escapeHtml(event.id)}</strong>
          <span>${formatSeconds(event.startTimestampSeconds)} → ${eventEnd}</span>
        </div>
        <ul class="segment-list">${segments}</ul>
      </li>
    `;
  }).join('');
}

export function renderNoteHistory(dom, item) {
  if (!dom.notesList) return;

  if (!item || !(item.notes ?? []).length) {
    dom.notesList.innerHTML = '<li class="empty-state">No human notes yet.</li>';
    return;
  }

  dom.notesList.innerHTML = item.notes.map((note) => `
    <li class="note-card note-${escapeHtml(note.kind)}">
      <div class="note-card-header">
        <span class="note-kind">${escapeHtml(note.kind)}</span>
        <span>${formatSeconds(note.timestampSeconds)}</span>
      </div>
      <p>${escapeHtml(note.text)}</p>
    </li>
  `).join('');
}

export function renderTimeline(dom, item) {
  if (!item || !(item.events ?? []).length) {
    dom.timeline.innerHTML = '<div class="timeline-empty">No coded event windows yet.</div>';
    return;
  }

  const bands = buildTimelineBands(item);
  if (!bands.length) {
    dom.timeline.innerHTML = '<div class="timeline-empty">Timeline appears after video duration is available.</div>';
    return;
  }

  dom.timeline.innerHTML = bands.map((band) => `
    <div
      class="timeline-event"
      data-event-id="${escapeHtml(band.id)}"
      style="left: ${formatPercent(band.leftPercent)}; width: ${formatPercent(band.widthPercent)};"
    >
      <div class="timeline-event-label">
        <span>${escapeHtml(band.startLabel)}</span>
        <span>${escapeHtml(band.endLabel)}</span>
      </div>
      ${band.segments.map((segment) => {
        const leftWithinEvent = band.widthPercent
          ? (segment.leftPercent / band.widthPercent) * 100
          : 0;
        const widthWithinEvent = band.widthPercent
          ? (segment.widthPercent / band.widthPercent) * 100
          : 0;

        return `
          <div
            class="timeline-segment tag-${escapeHtml(segment.tag)}"
            data-tag="${escapeHtml(segment.tag)}"
            title="${escapeHtml(`${segment.tag}: ${segment.startLabel} to ${segment.endLabel}`)}"
            style="left: ${formatPercent(leftWithinEvent)}; width: ${formatPercent(widthWithinEvent)};"
          >
            <span>${escapeHtml(segment.tag)}</span>
          </div>
        `;
      }).join('')}
    </div>
  `).join('');
}

export function renderTagButtons(dom) {
  dom.tagActions.innerHTML = ABC_TAGS.map((tag) => `
    <button type="button" data-tag="${escapeHtml(tag)}" class="tag-button tag-${escapeHtml(tag)}">
      ${escapeHtml(tag)}
    </button>
  `).join('');
  dom.tagButtons = [...dom.tagActions.querySelectorAll('[data-tag]')];
}

export function renderNoteKindOptions(dom) {
  if (!dom.noteKindSelect) return;

  dom.noteKindSelect.innerHTML = NOTE_KINDS.map((kind) => `
    <option value="${escapeHtml(kind)}">${escapeHtml(kind)}</option>
  `).join('');
}
