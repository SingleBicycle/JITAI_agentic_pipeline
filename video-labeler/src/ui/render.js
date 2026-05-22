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

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function formatSeconds(value) {
  return value == null ? 'none' : `${Number(value).toFixed(2)}s`;
}

function formatSpan(span) {
  return `${Number(span[0]).toFixed(2)}-${Number(span[1]).toFixed(2)}`;
}

export function renderInteractionEpisodeHistory(dom, item) {
  if (!item || !item.interactionEpisodes?.length) {
    dom.interactionEpisodesList.innerHTML = '<li class="empty-state">No interaction episodes yet.</li>';
    return;
  }

  dom.interactionEpisodesList.innerHTML = item.interactionEpisodes.map((episode) => {
    const cue = episode.cueEvent;
    const response = episode.responseEvent;
    const access = episode.recipientAccess;
    const link = episode.cueResponseLink;
    const latency = link.latencySeconds == null ? 'no latency' : `${Number(link.latencySeconds).toFixed(2)}s latency`;
    const evidence = episode.evidenceSpans.length
      ? episode.evidenceSpans.map(formatSpan).join(', ')
      : 'no evidence spans';
    const description = episode.description
      ? `<div class="interaction-description">${escapeHtml(episode.description)}</div>`
      : '';

    return `
      <li class="interaction-item">
        <div class="interaction-main">
          <strong>${escapeHtml(cue.actor)} -> ${escapeHtml(cue.candidateRecipient)}</strong>
          <span>${escapeHtml(cue.cueType)} cue, ${escapeHtml(access.accessLabel)} access</span>
        </div>
        <div class="interaction-detail">
          cue ${formatSeconds(cue.startSeconds)}-${formatSeconds(cue.endSeconds)};
          response ${escapeHtml(response.label)} (${escapeHtml(response.responseType)})
          ${formatSeconds(response.startSeconds)}-${formatSeconds(response.endSeconds)}
        </div>
        <div class="interaction-detail">
          ${escapeHtml(link.label)}; ${latency}; evidence ${escapeHtml(evidence)}; ambiguity ${escapeHtml(episode.ambiguityLabel)}
        </div>
        ${description}
      </li>
    `;
  }).join('');
}
