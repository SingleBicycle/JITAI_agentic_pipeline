import test from 'node:test';
import assert from 'node:assert/strict';
import { detectSource, deriveTitleFromUrl } from '../src/player/detect-source.js';

test('detectSource identifies YouTube URLs', () => {
  assert.deepEqual(detectSource('https://www.youtube.com/watch?v=abc123'), {
    sourceType: 'youtube',
    embedId: 'abc123'
  });
});

test('detectSource identifies YouTube Shorts URLs', () => {
  assert.deepEqual(detectSource('https://www.youtube.com/shorts/-VZ_F5h6fTk'), {
    sourceType: 'youtube',
    embedId: '-VZ_F5h6fTk'
  });
});

test('deriveTitleFromUrl falls back to the final path segment for direct media', () => {
  assert.deepEqual(deriveTitleFromUrl('https://cdn.example.com/folder/clip-01.mp4'), {
    title: 'clip-01.mp4',
    titleSource: 'filename'
  });
});

test('detectSource identifies direct video URLs', () => {
  assert.deepEqual(detectSource('https://cdn.example.com/video.mp4'), {
    sourceType: 'html5-video',
    embedId: null
  });
});

test('detectSource marks unsupported URLs clearly', () => {
  assert.deepEqual(detectSource('https://example.com/page'), {
    sourceType: 'unsupported',
    embedId: null
  });
});
