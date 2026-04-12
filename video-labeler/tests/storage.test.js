import test from 'node:test';
import assert from 'node:assert/strict';
import { createStorageClient } from '../src/lib/storage.js';

function createFakeDirectoryHandle() {
  const files = new Map();
  const dirs = new Map();

  return {
    files,
    dirs,
    async getFileHandle(name, options = {}) {
      if (!files.has(name) && options.create) {
        files.set(name, { name, content: '' });
      }
      return {
        async createWritable() {
          return {
            async write(content) {
              files.get(name).content = content;
            },
            async close() {}
          };
        }
      };
    },
    async getDirectoryHandle(name, options = {}) {
      if (!dirs.has(name) && options.create) {
        dirs.set(name, createFakeDirectoryHandle());
      }
      return dirs.get(name);
    }
  };
}

test('createStorageClient writes index.csv in the root folder', async () => {
  const root = createFakeDirectoryHandle();
  const client = createStorageClient(root);

  await client.writeIndex([{
    index: '001',
    sourceUrl: 'https://example.com/a.mp4',
    sourceType: 'html5-video',
    folderName: '001',
    createdAt: '2026-04-11T12:00:00.000Z'
  }]);

  assert.match(root.files.get('index.csv').content, /^index,/);
});

test('createStorageClient writes meta.json and labels.json in a video folder', async () => {
  const root = createFakeDirectoryHandle();
  const client = createStorageClient(root);

  await client.writeVideoFiles({
    item: {
      index: '001',
      folderName: '001',
      sourceUrl: 'https://example.com/a.mp4',
      sourceType: 'html5-video',
      createdAt: '2026-04-11T12:00:00.000Z'
    },
    meta: { index: '001' },
    labels: { videoIndex: '001', labels: [] }
  });

  const videoDir = root.dirs.get('001');
  assert.ok(videoDir.files.get('meta.json'));
  assert.ok(videoDir.files.get('labels.json'));
});
