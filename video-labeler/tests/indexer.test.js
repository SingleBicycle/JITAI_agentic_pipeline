import test from 'node:test';
import assert from 'node:assert/strict';
import { appendIndexedUrls } from '../src/lib/indexer.js';

test('appendIndexedUrls assigns zero-padded indexes and folder names', () => {
  const result = appendIndexedUrls([], [
    'https://example.com/a.mp4',
    'https://example.com/b.mp4'
  ]);

  assert.deepEqual(result.items.map((item) => item.index), ['001', '002']);
  assert.deepEqual(result.items.map((item) => item.folderName), ['001', '002']);
});

test('appendIndexedUrls skips duplicates already present in the session', () => {
  const existing = [{
    index: '001',
    sourceUrl: 'https://example.com/a.mp4',
    sourceType: 'html5-video',
    folderName: '001',
    status: 'ready'
  }];

  const result = appendIndexedUrls(existing, [
    'https://example.com/a.mp4',
    'https://youtu.be/abc123'
  ]);

  assert.equal(result.items.length, 2);
  assert.deepEqual(result.added.map((item) => item.index), ['002']);
  assert.equal(result.added[0].sourceUrl, 'https://youtu.be/abc123');
});
