import test from 'node:test';
import assert from 'node:assert/strict';
import { parseImportedText } from '../src/lib/parser.js';

test('parseImportedText pulls valid URLs from newline and csv-like text in order', () => {
  const input = [
    'https://example.com/a.mp4',
    'not-a-url,https://youtu.be/abc123',
    'https://example.com/b.mp4'
  ].join('\n');

  const result = parseImportedText(input);

  assert.deepEqual(result.urls, [
    'https://example.com/a.mp4',
    'https://youtu.be/abc123',
    'https://example.com/b.mp4'
  ]);
  assert.deepEqual(result.rejected, ['not-a-url']);
});

test('parseImportedText ignores blanks and reports malformed fragments', () => {
  const result = parseImportedText('\n,\nhello world\nhttps://example.com/ok.mp4');

  assert.deepEqual(result.urls, ['https://example.com/ok.mp4']);
  assert.deepEqual(result.rejected, ['hello world']);
});
