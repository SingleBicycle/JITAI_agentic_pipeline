import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createSessionState,
  appendImportedUrls,
  selectVideo,
  addMarkerForCurrentItem,
  describeLastClipForCurrentItem,
  recordInteractionEpisodeForCurrentItem,
  eraseInteractionEpisodeForCurrentItem
} from '../src/state/session.js';

test('appendImportedUrls adds new queue items and auto-selects the first item', () => {
  const state = createSessionState();
  appendImportedUrls(state, [
    {
      index: '001',
      sourceUrl: 'https://example.com/a.mp4',
      sourceType: 'html5-video',
      folderName: '001',
      status: 'ready',
      createdAt: '2026-04-11T12:00:00.000Z',
      markers: [],
      clips: []
    }
  ]);

  assert.equal(state.items.length, 1);
  assert.equal(state.currentIndex, '001');
  assert.deepEqual(state.items[0].markers, []);
  assert.deepEqual(state.items[0].clips, []);
  assert.deepEqual(state.items[0].interactionEpisodes, []);
});

test('selectVideo switches the active item by index', () => {
  const state = createSessionState();
  state.items = [
    { index: '001', markers: [], clips: [] },
    { index: '002', markers: [], clips: [] }
  ];

  selectVideo(state, '002');

  assert.equal(state.currentIndex, '002');
});

test('addMarkerForCurrentItem stores a persistent raw marker', () => {
  const state = createSessionState();
  appendImportedUrls(state, [{
    index: '001',
    sourceUrl: 'https://example.com/a.mp4',
    sourceType: 'html5-video',
    folderName: '001',
    createdAt: '2026-04-11T12:00:00.000Z',
    markers: [],
    clips: []
  }]);

  addMarkerForCurrentItem(state, {
    id: 'm1',
    timestampSeconds: 1.25,
    createdAt: '2026-04-11T12:01:00.000Z',
    kind: 'marker'
  });

  assert.equal(state.items[0].markers.length, 1);
  assert.equal(state.items[0].markers[0].kind, 'marker');
});

test('describeLastClipForCurrentItem updates the latest completed clip', () => {
  const state = createSessionState();
  appendImportedUrls(state, [{
    index: '001',
    sourceUrl: 'https://example.com/a.mp4',
    sourceType: 'html5-video',
    folderName: '001',
    createdAt: '2026-04-11T12:00:00.000Z',
    markers: [],
    clips: [{
      id: 'c1',
      startMarkerId: 'm1',
      endMarkerId: 'm2',
      startTimestampSeconds: 1,
      endTimestampSeconds: 2,
      description: '',
      createdAt: 'b'
    }]
  }]);

  describeLastClipForCurrentItem(state, 'opening reaction');

  assert.equal(state.items[0].clips[0].description, 'opening reaction');
});

test('recordInteractionEpisodeForCurrentItem appends CARE cue access response labels to active item', () => {
  const state = createSessionState();
  appendImportedUrls(state, [{
    index: '001',
    sourceUrl: 'http://localhost:4173/video1.mp4',
    sourceType: 'html5-video',
    folderName: '001',
    createdAt: '2026-05-22T10:00:00.000Z',
    markers: [],
    clips: []
  }]);

  recordInteractionEpisodeForCurrentItem(state, {
    createdAt: '2026-05-22T10:01:00.000Z',
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
    description: 'Adult presents materials; child visually orients toward the table.'
  });

  assert.equal(state.items[0].interactionEpisodes.length, 1);
  assert.equal(state.items[0].interactionEpisodes[0].id, 'ie1');
  assert.equal(state.items[0].interactionEpisodes[0].cueResponseLink.latencySeconds, 0.3);
  assert.equal(state.items[0].interactionEpisodes[0].description, 'Adult presents materials; child visually orients toward the table.');
});

test('eraseInteractionEpisodeForCurrentItem removes the latest interaction episode', () => {
  const state = createSessionState();
  appendImportedUrls(state, [{
    index: '001',
    sourceUrl: 'http://localhost:4173/video1.mp4',
    sourceType: 'html5-video',
    folderName: '001',
    createdAt: '2026-05-22T10:00:00.000Z',
    markers: [],
    clips: [],
    interactionEpisodes: [{ id: 'ie1' }, { id: 'ie2' }]
  }]);

  eraseInteractionEpisodeForCurrentItem(state);

  assert.deepEqual(state.items[0].interactionEpisodes, [{ id: 'ie1' }]);
});
