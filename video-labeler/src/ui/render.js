export function renderQueue(dom, state) {
  dom.queueList.innerHTML = state.items.map((item) => `
    <li data-index="${item.index}">
      <button
        type="button"
        class="queue-button${item.index === state.currentIndex ? ' is-active' : ''}"
        data-select-index="${item.index}"
      >
        <span class="queue-index">${item.index}</span>
        <span class="queue-copy">
          <strong>${item.title || 'Untitled video'}</strong>
          <span>${item.sourceUrl}</span>
        </span>
      </button>
    </li>
  `).join('');
}

export function renderSaveStatus(dom, state) {
  if (state.lastSaveError) {
    dom.saveStatus.textContent = `Save error: ${state.lastSaveError}`;
    return;
  }

  dom.saveStatus.textContent = state.outputDirectoryHandle
    ? 'Output folder ready'
    : 'No folder selected';
}

export function renderImportReport(dom, state) {
  if (!state.importSummary) {
    dom.importReport.textContent = '';
    return;
  }

  const { addedCount, duplicateCount, rejectedCount } = state.importSummary;
  dom.importReport.textContent = `Added ${addedCount}, skipped ${duplicateCount} duplicates, rejected ${rejectedCount} malformed entries.`;
}

export function renderMarkerHistory(dom, item) {
  if (!item || !item.markers.length) {
    dom.markersList.innerHTML = '<li class="empty-state">No markers yet.</li>';
    return;
  }

  dom.markersList.innerHTML = item.markers.map((marker) => `
    <li class="history-item">
      <span class="history-kind">${marker.kind}</span>
      <span class="history-time">${marker.timestampSeconds.toFixed(2)}s</span>
    </li>
  `).join('');
}

export function renderClipHistory(dom, item) {
  if (!item || !item.clips.length) {
    dom.clipsList.innerHTML = '<li class="empty-state">No clips yet.</li>';
    return;
  }

  dom.clipsList.innerHTML = item.clips.map((clip) => `
    <li class="clip-item">
      <div class="clip-range">${clip.startTimestampSeconds.toFixed(2)}s → ${clip.endTimestampSeconds.toFixed(2)}s</div>
      <div class="clip-description">${clip.description || 'No description yet'}</div>
    </li>
  `).join('');
}
