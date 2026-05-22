import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('social interaction cue types include common multimodal cue combinations', async () => {
  const config = JSON.parse(await readFile(new URL('../config/labels.json', import.meta.url), 'utf8'));
  const cueTypes = config.socialInteraction.cueTypes;

  assert.ok(cueTypes.includes('speech_object_action'));
  assert.ok(cueTypes.includes('gesture_object_action'));
  assert.ok(cueTypes.includes('speech_gesture_object_action'));
});
