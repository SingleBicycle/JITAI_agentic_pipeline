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

test('createStorageClient writes the local video index in the selected folder', async () => {
  const root = createFakeDirectoryHandle();
  const client = createStorageClient(root);

  await client.writeIndex([{
    index: '001',
    fileName: 'video1.mp4',
    sourceType: 'local-video',
    folderName: '001',
    createdAt: '2026-04-30T12:00:00.000Z'
  }]);

  assert.equal(root.files.get('index.csv').content, [
    'index,file_name,source_type,folder_name,created_at',
    '001,video1.mp4,local-video,001,2026-04-30T12:00:00.000Z',
    ''
  ].join('\n'));
});

test('createStorageClient writes meta.json and labels.json per video folder', async () => {
  const root = createFakeDirectoryHandle();
  const client = createStorageClient(root);

  await client.writeVideoFiles({
    item: { folderName: '001' },
    meta: { index: '001', eventCount: 1 },
    labels: { videoIndex: '001', events: [] }
  });

  const videoDir = root.dirs.get('001');
  assert.equal(videoDir.files.get('meta.json').content, '{\n  "index": "001",\n  "eventCount": 1\n}\n');
  assert.equal(videoDir.files.get('labels.json').content, '{\n  "videoIndex": "001",\n  "events": []\n}\n');
});
