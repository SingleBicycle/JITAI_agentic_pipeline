import test from 'node:test';
import assert from 'node:assert/strict';
import {
  startEventClip,
  endEventClip,
  startSegmentTag,
  clearSegmentTag,
  eraseLastAnnotation,
  getOpenEventClip,
  getActiveSegment
} from '../src/lib/annotations.js';

test('startEventClip creates one open event clip at the selected timestamp', () => {
  const result = startEventClip([], {
    id: 'e1',
    timestampSeconds: 10.5,
    createdAt: '2026-04-30T12:00:00.000Z'
  });

  assert.deepEqual(result, [{
    id: 'e1',
    startTimestampSeconds: 10.5,
    endTimestampSeconds: null,
    createdAt: '2026-04-30T12:00:00.000Z',
    endedAt: null,
    segments: []
  }]);
});

test('startSegmentTag closes the previous tag segment and opens the next one', () => {
  let events = startEventClip([], {
    id: 'e1',
    timestampSeconds: 5,
    createdAt: 'clip-start'
  });

  events = startSegmentTag(events, {
    id: 's1',
    tag: 'antecedent',
    timestampSeconds: 7,
    createdAt: 'tag-a'
  });
  events = startSegmentTag(events, {
    id: 's2',
    tag: 'behavior',
    timestampSeconds: 12,
    createdAt: 'tag-b'
  });

  assert.deepEqual(events[0].segments, [
    {
      id: 's1',
      tag: 'antecedent',
      startTimestampSeconds: 7,
      endTimestampSeconds: 12,
      createdAt: 'tag-a',
      endedAt: 'tag-b'
    },
    {
      id: 's2',
      tag: 'behavior',
      startTimestampSeconds: 12,
      endTimestampSeconds: null,
      createdAt: 'tag-b',
      endedAt: null
    }
  ]);
});

test('clearSegmentTag closes the active segment without opening another tag', () => {
  let events = startEventClip([], {
    id: 'e1',
    timestampSeconds: 5,
    createdAt: 'clip-start'
  });
  events = startSegmentTag(events, {
    id: 's1',
    tag: 'consequence',
    timestampSeconds: 6,
    createdAt: 'tag-c'
  });

  events = clearSegmentTag(events, {
    timestampSeconds: 9,
    createdAt: 'clear'
  });

  assert.deepEqual(events[0].segments, [{
    id: 's1',
    tag: 'consequence',
    startTimestampSeconds: 6,
    endTimestampSeconds: 9,
    createdAt: 'tag-c',
    endedAt: 'clear'
  }]);
  assert.equal(getActiveSegment(events), null);
});

test('endEventClip closes an open tag segment at the clip end', () => {
  let events = startEventClip([], {
    id: 'e1',
    timestampSeconds: 20,
    createdAt: 'clip-start'
  });
  events = startSegmentTag(events, {
    id: 's1',
    tag: 'antecedent',
    timestampSeconds: 22,
    createdAt: 'tag-a'
  });

  events = endEventClip(events, {
    timestampSeconds: 31,
    createdAt: 'clip-end'
  });

  assert.equal(events[0].endTimestampSeconds, 31);
  assert.equal(events[0].endedAt, 'clip-end');
  assert.equal(events[0].segments[0].endTimestampSeconds, 31);
  assert.equal(getOpenEventClip(events), null);
});

test('tag actions are ignored when there is no open event clip', () => {
  const events = startSegmentTag([], {
    id: 's1',
    tag: 'behavior',
    timestampSeconds: 1,
    createdAt: 'tag'
  });

  assert.deepEqual(events, []);
});

test('eraseLastAnnotation removes an open segment before removing the open event clip', () => {
  let events = startEventClip([], {
    id: 'e1',
    timestampSeconds: 1,
    createdAt: 'clip-start'
  });
  events = startSegmentTag(events, {
    id: 's1',
    tag: 'antecedent',
    timestampSeconds: 2,
    createdAt: 'tag-a'
  });

  events = eraseLastAnnotation(events);
  assert.deepEqual(events[0].segments, []);

  events = eraseLastAnnotation(events);
  assert.deepEqual(events, []);
});
