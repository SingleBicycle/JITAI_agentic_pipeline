import test from 'node:test';
import assert from 'node:assert/strict';
import {
  collectVideoFilesFromDirectory,
  isSupportedVideoFile
} from '../src/lib/videos.js';

function createFakeDirectoryHandle(entries) {
  return {
    async *entries() {
      for (const entry of entries) {
        yield entry;
      }
    }
  };
}

test('isSupportedVideoFile accepts common browser video extensions', () => {
  assert.equal(isSupportedVideoFile('session-01.mp4'), true);
  assert.equal(isSupportedVideoFile('SESSION-02.WEBM'), true);
  assert.equal(isSupportedVideoFile('notes.csv'), false);
});

test('collectVideoFilesFromDirectory indexes direct video files in stable filename order', async () => {
  const folder = createFakeDirectoryHandle([
    ['z-last.mp4', { kind: 'file', name: 'z-last.mp4' }],
    ['notes.txt', { kind: 'file', name: 'notes.txt' }],
    ['nested', { kind: 'directory', name: 'nested' }],
    ['a-first.webm', { kind: 'file', name: 'a-first.webm' }]
  ]);

  const items = await collectVideoFilesFromDirectory(folder, () => '2026-04-30T12:00:00.000Z');

  assert.deepEqual(items.map((item) => ({
    index: item.index,
    fileName: item.fileName,
    folderName: item.folderName,
    sourceType: item.sourceType,
    createdAt: item.createdAt
  })), [
    {
      index: '001',
      fileName: 'a-first.webm',
      folderName: '001',
      sourceType: 'local-video',
      createdAt: '2026-04-30T12:00:00.000Z'
    },
    {
      index: '002',
      fileName: 'z-last.mp4',
      folderName: '002',
      sourceType: 'local-video',
      createdAt: '2026-04-30T12:00:00.000Z'
    }
  ]);
  assert.equal(items[0].fileHandle.name, 'a-first.webm');
});
