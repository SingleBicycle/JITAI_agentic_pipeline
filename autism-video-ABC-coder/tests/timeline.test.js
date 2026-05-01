import test from 'node:test';
import assert from 'node:assert/strict';
import { buildTimelineBands } from '../src/lib/timeline.js';

test('buildTimelineBands maps event clips and tag segments onto video-duration percentages', () => {
  const bands = buildTimelineBands({
    durationSeconds: 100,
    events: [{
      id: 'e1',
      startTimestampSeconds: 10,
      endTimestampSeconds: 40,
      segments: [
        {
          id: 's1',
          tag: 'antecedent',
          startTimestampSeconds: 12,
          endTimestampSeconds: 20
        },
        {
          id: 's2',
          tag: 'behavior',
          startTimestampSeconds: 20,
          endTimestampSeconds: 35
        }
      ]
    }]
  });

  assert.deepEqual(bands, [{
    id: 'e1',
    startLabel: '10.00s',
    endLabel: '40.00s',
    leftPercent: 10,
    widthPercent: 30,
    segments: [
      {
        id: 's1',
        tag: 'antecedent',
        leftPercent: 2,
        widthPercent: 8,
        startLabel: '12.00s',
        endLabel: '20.00s'
      },
      {
        id: 's2',
        tag: 'behavior',
        leftPercent: 10,
        widthPercent: 15,
        startLabel: '20.00s',
        endLabel: '35.00s'
      }
    ]
  }]);
});

test('buildTimelineBands uses current playback time for open clips and clips open segments to the event window', () => {
  const bands = buildTimelineBands({
    durationSeconds: 20,
    currentTimeSeconds: 16,
    events: [{
      id: 'e1',
      startTimestampSeconds: 5,
      endTimestampSeconds: null,
      segments: [{
        id: 's1',
        tag: 'consequence',
        startTimestampSeconds: 12,
        endTimestampSeconds: null
      }]
    }]
  });

  assert.equal(bands[0].endLabel, '16.00s');
  assert.equal(bands[0].widthPercent, 55);
  assert.deepEqual(bands[0].segments, [{
    id: 's1',
    tag: 'consequence',
    leftPercent: 35,
    widthPercent: 20,
    startLabel: '12.00s',
    endLabel: '16.00s'
  }]);
});
