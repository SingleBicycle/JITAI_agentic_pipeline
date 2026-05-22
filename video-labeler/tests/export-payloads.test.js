import test from 'node:test';
import assert from 'node:assert/strict';
import { buildMeta, buildLabelsPayload } from '../src/lib/export-payloads.js';

test('buildLabelsPayload includes interaction episodes alongside existing marker and clip data', () => {
  const payload = buildLabelsPayload({
    index: '001',
    sourceUrl: 'http://localhost:4173/video1.mp4',
    markers: [{ id: 'm1', timestampSeconds: 13.2, createdAt: 'a', kind: 'start' }],
    clips: [{ id: 'c1', startTimestampSeconds: 13.2, endTimestampSeconds: 17, description: 'episode window' }],
    interactionEpisodes: [{ id: 'ie1', ambiguityLabel: 'low' }]
  });

  assert.deepEqual(payload, {
    videoIndex: '001',
    sourceUrl: 'http://localhost:4173/video1.mp4',
    markers: [{ id: 'm1', timestampSeconds: 13.2, createdAt: 'a', kind: 'start' }],
    clips: [{ id: 'c1', startTimestampSeconds: 13.2, endTimestampSeconds: 17, description: 'episode window' }],
    interactionEpisodes: [{ id: 'ie1', ambiguityLabel: 'low' }]
  });
});

test('buildMeta counts interaction episodes without dropping existing summary fields', () => {
  const meta = buildMeta({
    index: '001',
    folderName: '001',
    sourceUrl: 'http://localhost:4173/video1.mp4',
    sourceType: 'html5-video',
    title: 'video1.mp4',
    titleSource: 'filename',
    createdAt: '2026-05-22T10:00:00.000Z',
    durationSeconds: 42,
    seekable: true,
    clips: [{ id: 'c1', startMarkerId: 'm1' }],
    markers: [{ id: 'm1', kind: 'start' }],
    interactionEpisodes: [{ id: 'ie1' }],
    capabilities: { timing: true, duration: true }
  });

  assert.equal(meta.clipCount, 1);
  assert.equal(meta.interactionEpisodeCount, 1);
  assert.equal(meta.hasOpenStartMarker, false);
  assert.equal(meta.title, 'video1.mp4');
});
