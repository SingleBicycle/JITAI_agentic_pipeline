import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createSessionState,
  appendImportedUrls,
  selectVideo,
  addMarkerForCurrentItem,
  describeLastClipForCurrentItem
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
