import test from 'node:test';
import assert from 'node:assert/strict';
import {
  NOTE_KINDS,
  addHumanNote,
  createHumanNote,
  eraseLastHumanNote
} from '../src/lib/notes.js';

test('NOTE_KINDS exposes caption, note, and comment modes', () => {
  assert.deepEqual(NOTE_KINDS, ['caption', 'note', 'comment']);
});

test('createHumanNote stores trimmed timestamped human text', () => {
  const note = createHumanNote({
    id: 'n1',
    kind: 'caption',
    timestampSeconds: 12.34,
    text: '  child says hello  ',
    createdAt: '2026-05-01T06:00:00.000Z'
  });

  assert.deepEqual(note, {
    id: 'n1',
    kind: 'caption',
    timestampSeconds: 12.34,
    text: 'child says hello',
    createdAt: '2026-05-01T06:00:00.000Z'
  });
});

test('addHumanNote appends valid notes and ignores blank text', () => {
  const notes = addHumanNote([], {
    id: 'n1',
    kind: 'note',
    timestampSeconds: 3,
    text: 'leans toward screen',
    createdAt: 'created'
  });

  assert.equal(notes.length, 1);
  assert.deepEqual(addHumanNote(notes, {
    id: 'n2',
    kind: 'comment',
    timestampSeconds: 4,
    text: '   ',
    createdAt: 'created'
  }), notes);
});

test('addHumanNote rejects unknown note kinds', () => {
  assert.throws(() => addHumanNote([], {
    id: 'n1',
    kind: 'other',
    timestampSeconds: 1,
    text: 'hello',
    createdAt: 'created'
  }), /Unsupported note kind/);
});

test('eraseLastHumanNote removes the latest human note', () => {
  const notes = [
    { id: 'n1', kind: 'caption', timestampSeconds: 1, text: 'one', createdAt: 'a' },
    { id: 'n2', kind: 'comment', timestampSeconds: 2, text: 'two', createdAt: 'b' }
  ];

  assert.deepEqual(eraseLastHumanNote(notes), [
    { id: 'n1', kind: 'caption', timestampSeconds: 1, text: 'one', createdAt: 'a' }
  ]);
});
