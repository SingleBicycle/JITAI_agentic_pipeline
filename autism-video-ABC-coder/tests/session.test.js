import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createSessionState,
  appendVideoItems,
  getCurrentItem,
  addNoteForCurrentItem,
  startEventForCurrentItem,
  startTagForCurrentItem,
  endEventForCurrentItem
} from '../src/state/session.js';

test('appendVideoItems adds local videos and auto-selects the first item', () => {
  const state = createSessionState();

  appendVideoItems(state, [{
    index: '001',
    fileName: 'video1.mp4',
    sourceType: 'local-video',
    folderName: '001',
    createdAt: '2026-04-30T12:00:00.000Z',
    fileHandle: { name: 'video1.mp4' }
  }]);

  assert.equal(state.items.length, 1);
  assert.equal(state.currentIndex, '001');
  assert.deepEqual(state.items[0].events, []);
  assert.deepEqual(state.items[0].notes, []);
});

test('current item event and tag helpers update the selected video only', () => {
  const state = createSessionState();
  appendVideoItems(state, [
    {
      index: '001',
      fileName: 'video1.mp4',
      sourceType: 'local-video',
      folderName: '001',
      createdAt: '2026-04-30T12:00:00.000Z',
      fileHandle: { name: 'video1.mp4' }
    },
    {
      index: '002',
      fileName: 'video2.mp4',
      sourceType: 'local-video',
      folderName: '002',
      createdAt: '2026-04-30T12:00:00.000Z',
      fileHandle: { name: 'video2.mp4' }
    }
  ]);

  startEventForCurrentItem(state, {
    id: 'e1',
    timestampSeconds: 3,
    createdAt: 'clip-start'
  });
  startTagForCurrentItem(state, {
    id: 's1',
    tag: 'behavior',
    timestampSeconds: 4,
    createdAt: 'tag'
  });
  endEventForCurrentItem(state, {
    timestampSeconds: 8,
    createdAt: 'clip-end'
  });

  assert.equal(getCurrentItem(state).events.length, 1);
  assert.equal(state.items[1].events.length, 0);
  assert.equal(state.nextEventNumber, 1);
  assert.equal(state.nextSegmentNumber, 1);
});

test('addNoteForCurrentItem stores timestamped human notes on the selected video', () => {
  const state = createSessionState();
  appendVideoItems(state, [{
    index: '001',
    fileName: 'video1.mp4',
    sourceType: 'local-video',
    folderName: '001',
    createdAt: '2026-04-30T12:00:00.000Z',
    fileHandle: { name: 'video1.mp4' }
  }]);

  addNoteForCurrentItem(state, {
    id: 'n1',
    kind: 'comment',
    timestampSeconds: 9.5,
    text: 'possible transition trigger',
    createdAt: '2026-05-01T06:00:00.000Z'
  });

  assert.deepEqual(state.items[0].notes, [{
    id: 'n1',
    kind: 'comment',
    timestampSeconds: 9.5,
    text: 'possible transition trigger',
    createdAt: '2026-05-01T06:00:00.000Z'
  }]);
});
