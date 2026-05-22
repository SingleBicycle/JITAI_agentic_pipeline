import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('interaction labeling panel replaces old marker and clip-description controls', async () => {
  const html = await readFile(new URL('../index.html', import.meta.url), 'utf8');

  assert.match(html, /id="episode-description-input"/);
  assert.doesNotMatch(html, /Editorial Slate/);
  assert.doesNotMatch(html, /id="capture-marker-button"/);
  assert.doesNotMatch(html, /id="marker-actions"/);
  assert.doesNotMatch(html, /id="clip-description-input"/);
  assert.doesNotMatch(html, /id="apply-description-button"/);
});
