import test from 'node:test';
import assert from 'node:assert/strict';
import { toIndexCsv, toMetaJson, toLabelsJson } from '../src/lib/serializer.js';

test('toIndexCsv writes the expected header and rows', () => {
  const csv = toIndexCsv([{
    index: '001',
    sourceUrl: 'https://example.com/a.mp4',
    sourceType: 'html5-video',
    folderName: '001',
    createdAt: '2026-04-11T12:00:00.000Z'
  }]);

  assert.equal(
    csv,
    'index,source_url,source_type,folder_name,created_at\n001,https://example.com/a.mp4,html5-video,001,2026-04-11T12:00:00.000Z\n'
  );
});

test('toLabelsJson writes markers and clips arrays', () => {
  const json = toLabelsJson({
    videoIndex: '001',
    sourceUrl: 'https://example.com/a.mp4',
    markers: [{ id: 'm1', timestampSeconds: 10, createdAt: 'a', kind: 'marker' }],
    clips: [{ id: 'c1', startMarkerId: 'm1', endMarkerId: 'm2', startTimestampSeconds: 10, endTimestampSeconds: 20, description: '', createdAt: 'b' }]
  });

  assert.match(json, /"markers"/);
  assert.match(json, /"clips"/);
});

test('toMetaJson writes title and clip summary fields', () => {
  const json = toMetaJson({
    index: '001',
    folderName: '001',
    sourceUrl: 'https://example.com/a.mp4',
    sourceType: 'html5-video',
    title: 'a.mp4',
    titleSource: 'filename',
    createdAt: '2026-04-11T12:00:00.000Z',
    durationSeconds: 10,
    seekable: true,
    clipCount: 1,
    hasOpenStartMarker: false,
    capabilities: { timing: true, duration: true }
  });

  assert.match(json, /"title": "a.mp4"/);
  assert.match(json, /"clipCount": 1/);
});
