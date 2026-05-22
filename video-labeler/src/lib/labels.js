export function createMarker(payload) {
  return {
    id: payload.id,
    timestampSeconds: payload.timestampSeconds,
    createdAt: payload.createdAt,
    kind: payload.kind
  };
}

function findLatestOpenStart(markers, clips) {
  const closedStartIds = new Set(clips.map((clip) => clip.startMarkerId));
  return [...markers]
    .reverse()
    .find((marker) => marker.kind === 'start' && !closedStartIds.has(marker.id)) ?? null;
}

export function applyMarkerAction(state, payload) {
  if (payload.eraseLast) {
    const nextMarkers = state.markers.slice(0, -1);
    const removedMarker = state.markers.at(-1);
    const nextClips = removedMarker
      ? state.clips.filter((clip) => clip.startMarkerId !== removedMarker.id && clip.endMarkerId !== removedMarker.id)
      : state.clips;
    return { markers: nextMarkers, clips: nextClips };
  }

  const markers = [...state.markers, payload.marker];
  const clips = [...state.clips];

  if (payload.marker.kind === 'end') {
    const openStart = findLatestOpenStart(state.markers, state.clips);
    if (openStart) {
      clips.push({
        id: payload.clipId,
        startMarkerId: openStart.id,
        endMarkerId: payload.marker.id,
        startTimestampSeconds: openStart.timestampSeconds,
        endTimestampSeconds: payload.marker.timestampSeconds,
        description: '',
        createdAt: payload.marker.createdAt
      });
    }
  }

  return { markers, clips };
}

export function applyClipDescription(clips, description) {
  if (!clips.length) return clips;
  const nextClips = [...clips];
  const lastClip = nextClips.at(-1);
  nextClips[nextClips.length - 1] = {
    ...lastClip,
    description
  };
  return nextClips;
}

function secondsOrNull(value) {
  if (value === '' || value == null) return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function requireSeconds(value, fieldName) {
  const numeric = secondsOrNull(value);
  if (numeric == null) {
    throw new Error(`${fieldName} is required`);
  }
  return numeric;
}

function roundSeconds(value) {
  return Math.round(value * 1000) / 1000;
}

export function parseEvidenceSpans(rawText) {
  if (!rawText?.trim()) return [];

  return rawText
    .split(/[;\n]+/)
    .map((entry) => entry.trim())
    .filter(Boolean)
    .map((entry) => {
      const match = entry.match(/^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$/);
      if (!match) {
        throw new Error(`Evidence span "${entry}" must use start-end seconds`);
      }

      const start = Number(match[1]);
      const end = Number(match[2]);
      if (end < start) {
        throw new Error(`Evidence span "${entry}" ends before it starts`);
      }

      return [start, end];
    });
}

export function createInteractionEpisode(payload) {
  const cueStartSeconds = requireSeconds(payload.cueStartSeconds, 'Cue start');
  const cueEndSeconds = requireSeconds(payload.cueEndSeconds, 'Cue end');
  if (cueEndSeconds < cueStartSeconds) {
    throw new Error('Cue end must be after cue start');
  }

  const noObservedResponse = payload.responseLabel === 'no_observed_response';
  const responseStartSeconds = noObservedResponse ? null : secondsOrNull(payload.responseStartSeconds);
  const responseEndSeconds = noObservedResponse ? null : secondsOrNull(payload.responseEndSeconds);
  if (responseStartSeconds != null && responseEndSeconds != null && responseEndSeconds < responseStartSeconds) {
    throw new Error('Response end must be after response start');
  }

  const latencySeconds = responseStartSeconds == null ? null : roundSeconds(responseStartSeconds - cueEndSeconds);

  return {
    id: payload.id,
    createdAt: payload.createdAt,
    cueEvent: {
      startSeconds: cueStartSeconds,
      endSeconds: cueEndSeconds,
      actor: payload.cueActor?.trim() || '',
      candidateRecipient: payload.candidateRecipient?.trim() || '',
      cueType: payload.cueType
    },
    recipientAccess: {
      recipient: payload.candidateRecipient?.trim() || '',
      accessLabel: payload.accessLabel
    },
    responseEvent: {
      label: payload.responseLabel,
      startSeconds: responseStartSeconds,
      endSeconds: responseEndSeconds,
      responseType: payload.responseType
    },
    cueResponseLink: {
      label: payload.cueResponseLink,
      latencySeconds
    },
    evidenceSpans: parseEvidenceSpans(payload.evidenceSpansText),
    ambiguityLabel: payload.ambiguityLabel,
    description: payload.description?.trim() || ''
  };
}

export function applyInteractionEpisodeAction(existingEpisodes, payload) {
  if (payload.eraseLast) {
    return existingEpisodes.slice(0, -1);
  }

  return [...existingEpisodes, payload.episode];
}

export function applyLabelAction(existingLabels, payload) {
  if (payload.action === 'erase') {
    return existingLabels.slice(0, -1);
  }

  return [...existingLabels, {
    label: payload.action,
    timestampSeconds: payload.timestampSeconds,
    createdAt: payload.createdAt
  }];
}
