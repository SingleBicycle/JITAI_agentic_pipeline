import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createMarker,
  applyMarkerAction,
  applyClipDescription
} from '../src/lib/labels.js';

test('createMarker returns a persistent raw marker for the top-level label action', () => {
  const marker = createMarker({
    id: 'm1',
    timestampSeconds: 12.34,
    createdAt: '2026-04-11T12:00:00.000Z',
    kind: 'marker'
  });

  assert.deepEqual(marker, {
    id: 'm1',
    timestampSeconds: 12.34,
    createdAt: '2026-04-11T12:00:00.000Z',
    kind: 'marker'
  });
});

test('applyMarkerAction creates a clip when an end marker closes the most recent open start marker', () => {
  const result = applyMarkerAction({
    markers: [
      { id: 'm1', timestampSeconds: 10, createdAt: 'a', kind: 'start' }
    ],
    clips: []
  }, {
    marker: { id: 'm2', timestampSeconds: 18, createdAt: 'b', kind: 'end' },
    clipId: 'c1'
  });

  assert.equal(result.markers.length, 2);
  assert.deepEqual(result.clips, [{
    id: 'c1',
    startMarkerId: 'm1',
    endMarkerId: 'm2',
    startTimestampSeconds: 10,
    endTimestampSeconds: 18,
    description: '',
    createdAt: 'b'
  }]);
});

test('applyClipDescription updates the most recently completed clip description', () => {
  const result = applyClipDescription([
    {
      id: 'c1',
      startMarkerId: 'm1',
      endMarkerId: 'm2',
      startTimestampSeconds: 10,
      endTimestampSeconds: 18,
      description: '',
      createdAt: 'b'
    }
  ], 'speaker turns toward camera');

  assert.equal(result[0].description, 'speaker turns toward camera');
});

test('applyMarkerAction erase removes the latest marker and dependent clip', () => {
  const result = applyMarkerAction({
    markers: [
      { id: 'm1', timestampSeconds: 10, createdAt: 'a', kind: 'start' },
      { id: 'm2', timestampSeconds: 18, createdAt: 'b', kind: 'end' }
    ],
    clips: [
      {
        id: 'c1',
        startMarkerId: 'm1',
        endMarkerId: 'm2',
        startTimestampSeconds: 10,
        endTimestampSeconds: 18,
        description: 'clip',
        createdAt: 'b'
      }
    ]
  }, {
    eraseLast: true
  });

  assert.deepEqual(result.markers, [
    { id: 'm1', timestampSeconds: 10, createdAt: 'a', kind: 'start' }
  ]);
  assert.deepEqual(result.clips, []);
});
