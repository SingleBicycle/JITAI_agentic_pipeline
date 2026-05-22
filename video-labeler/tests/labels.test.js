import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createMarker,
  applyMarkerAction,
  applyClipDescription,
  parseEvidenceSpans,
  createInteractionEpisode,
  applyInteractionEpisodeAction
} from '../src/lib/labels.js';

test('createMarker returns a persistent raw marker for the top-level label action', () => {
  const marker = createMarker({
    id: 'm1',
    timestampSeconds: 12.34,
    createdAt: '2026-04-11T12:00:00.000Z',
    kind: 'marker'
  });

  assert.deepEqual(marker, {
    id: 'm1',
    timestampSeconds: 12.34,
    createdAt: '2026-04-11T12:00:00.000Z',
    kind: 'marker'
  });
});

test('applyMarkerAction creates a clip when an end marker closes the most recent open start marker', () => {
  const result = applyMarkerAction({
    markers: [
      { id: 'm1', timestampSeconds: 10, createdAt: 'a', kind: 'start' }
    ],
    clips: []
  }, {
    marker: { id: 'm2', timestampSeconds: 18, createdAt: 'b', kind: 'end' },
    clipId: 'c1'
  });

  assert.equal(result.markers.length, 2);
  assert.deepEqual(result.clips, [{
    id: 'c1',
    startMarkerId: 'm1',
    endMarkerId: 'm2',
    startTimestampSeconds: 10,
    endTimestampSeconds: 18,
    description: '',
    createdAt: 'b'
  }]);
});

test('applyClipDescription updates the most recently completed clip description', () => {
  const result = applyClipDescription([
    {
      id: 'c1',
      startMarkerId: 'm1',
      endMarkerId: 'm2',
      startTimestampSeconds: 10,
      endTimestampSeconds: 18,
      description: '',
      createdAt: 'b'
    }
  ], 'speaker turns toward camera');

  assert.equal(result[0].description, 'speaker turns toward camera');
});

test('applyMarkerAction erase removes the latest marker and dependent clip', () => {
  const result = applyMarkerAction({
    markers: [
      { id: 'm1', timestampSeconds: 10, createdAt: 'a', kind: 'start' },
      { id: 'm2', timestampSeconds: 18, createdAt: 'b', kind: 'end' }
    ],
    clips: [
      {
        id: 'c1',
        startMarkerId: 'm1',
        endMarkerId: 'm2',
        startTimestampSeconds: 10,
        endTimestampSeconds: 18,
        description: 'clip',
        createdAt: 'b'
      }
    ]
  }, {
    eraseLast: true
  });

  assert.deepEqual(result.markers, [
    { id: 'm1', timestampSeconds: 10, createdAt: 'a', kind: 'start' }
  ]);
  assert.deepEqual(result.clips, []);
});

test('parseEvidenceSpans converts semicolon separated ranges into numeric spans', () => {
  assert.deepEqual(parseEvidenceSpans('13.20-14.80; 15.10-17.00'), [
    [13.2, 14.8],
    [15.1, 17]
  ]);
});

test('createInteractionEpisode stores cue access response linkage and latency', () => {
  const episode = createInteractionEpisode({
    id: 'ie1',
    createdAt: '2026-05-22T10:00:00.000Z',
    cueStartSeconds: 13.2,
    cueEndSeconds: 14.8,
    cueActor: 'P1',
    candidateRecipient: 'P2',
    cueType: 'speech_gesture',
    accessLabel: 'visible_and_audible',
    responseLabel: 'possible_response',
    responseStartSeconds: 15.1,
    responseEndSeconds: 17,
    responseType: 'object_action_response',
    cueResponseLink: 'linked',
    evidenceSpansText: '13.2-14.8; 15.1-17.0',
    ambiguityLabel: 'low',
    description: 'Adult presents the marker-like object; child looks toward the table materials.'
  });

  assert.deepEqual(episode, {
    id: 'ie1',
    createdAt: '2026-05-22T10:00:00.000Z',
    cueEvent: {
      startSeconds: 13.2,
      endSeconds: 14.8,
      actor: 'P1',
      candidateRecipient: 'P2',
      cueType: 'speech_gesture'
    },
    recipientAccess: {
      recipient: 'P2',
      accessLabel: 'visible_and_audible'
    },
    responseEvent: {
      label: 'possible_response',
      startSeconds: 15.1,
      endSeconds: 17,
      responseType: 'object_action_response'
    },
    cueResponseLink: {
      label: 'linked',
      latencySeconds: 0.3
    },
    evidenceSpans: [
      [13.2, 14.8],
      [15.1, 17]
    ],
    ambiguityLabel: 'low',
    description: 'Adult presents the marker-like object; child looks toward the table materials.'
  });
});

test('createInteractionEpisode supports explicit no-response observations', () => {
  const episode = createInteractionEpisode({
    id: 'ie2',
    createdAt: '2026-05-22T10:05:00.000Z',
    cueStartSeconds: 21,
    cueEndSeconds: 22,
    cueActor: 'P1',
    candidateRecipient: 'P2',
    cueType: 'gesture',
    accessLabel: 'orientation_unclear',
    responseLabel: 'no_observed_response',
    responseStartSeconds: '',
    responseEndSeconds: '',
    responseType: 'none',
    cueResponseLink: 'no_observed_response',
    evidenceSpansText: '21-22',
    ambiguityLabel: 'medium'
  });

  assert.equal(episode.responseEvent.startSeconds, null);
  assert.equal(episode.responseEvent.endSeconds, null);
  assert.equal(episode.cueResponseLink.latencySeconds, null);
});

test('createInteractionEpisode rejects cue ranges that end before they start', () => {
  assert.throws(() => createInteractionEpisode({
    id: 'ie3',
    createdAt: '2026-05-22T10:10:00.000Z',
    cueStartSeconds: 22,
    cueEndSeconds: 21,
    cueActor: 'P1',
    candidateRecipient: 'P2',
    cueType: 'gesture',
    accessLabel: 'visible_only',
    responseLabel: 'direct_response',
    responseStartSeconds: 23,
    responseEndSeconds: 24,
    responseType: 'gesture_response',
    cueResponseLink: 'linked',
    evidenceSpansText: '22-24',
    ambiguityLabel: 'low'
  }), /Cue end must be after cue start/);
});

test('applyInteractionEpisodeAction appends or erases the latest episode', () => {
  const first = { id: 'ie1', cueEvent: { actor: 'P1' } };
  const second = { id: 'ie2', cueEvent: { actor: 'P2' } };

  const appended = applyInteractionEpisodeAction([first], { episode: second });
  assert.deepEqual(appended, [first, second]);

  const erased = applyInteractionEpisodeAction(appended, { eraseLast: true });
  assert.deepEqual(erased, [first]);
});
