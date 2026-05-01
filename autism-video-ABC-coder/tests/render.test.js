import test from 'node:test';
import assert from 'node:assert/strict';
import {
  renderEventHistory,
  renderNoteHistory,
  renderTimeline
} from '../src/ui/render.js';

test('renderTimeline shows event windows and ABC tag spans', () => {
  const dom = { timeline: { innerHTML: '' } };

  renderTimeline(dom, {
    durationSeconds: 20,
    currentTimeSeconds: 12,
    events: [{
      id: 'e1',
      startTimestampSeconds: 4,
      endTimestampSeconds: 10,
      segments: [{
        id: 's1',
        tag: 'behavior',
        startTimestampSeconds: 5,
        endTimestampSeconds: 9
      }]
    }]
  });

  assert.match(dom.timeline.innerHTML, /data-event-id="e1"/);
  assert.match(dom.timeline.innerHTML, /data-tag="behavior"/);
  assert.match(dom.timeline.innerHTML, /4\.00s/);
  assert.match(dom.timeline.innerHTML, /10\.00s/);
});

test('renderEventHistory summarizes completed clips and nested segments', () => {
  const dom = { eventsList: { innerHTML: '' } };

  renderEventHistory(dom, {
    events: [{
      id: 'e1',
      startTimestampSeconds: 1,
      endTimestampSeconds: 6,
      segments: [{
        id: 's1',
        tag: 'antecedent',
        startTimestampSeconds: 2,
        endTimestampSeconds: 3
      }]
    }]
  });

  assert.match(dom.eventsList.innerHTML, /Event e1/);
  assert.match(dom.eventsList.innerHTML, /antecedent/);
  assert.match(dom.eventsList.innerHTML, /2\.00s/);
});

test('renderNoteHistory shows timestamped captions, notes, and comments', () => {
  const dom = { notesList: { innerHTML: '' } };

  renderNoteHistory(dom, {
    notes: [{
      id: 'n1',
      kind: 'caption',
      timestampSeconds: 11,
      text: 'child says hello',
      createdAt: 'created'
    }]
  });

  assert.match(dom.notesList.innerHTML, /caption/);
  assert.match(dom.notesList.innerHTML, /11\.00s/);
  assert.match(dom.notesList.innerHTML, /child says hello/);
});
