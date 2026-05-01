import test from 'node:test';
import assert from 'node:assert/strict';
import {
  toIndexCsv,
  toLabelsJson,
  toMetaJson
} from '../src/lib/serializer.js';

test('toIndexCsv serializes local video queue rows', () => {
  assert.equal(toIndexCsv([{
    index: '001',
    fileName: 'video1.mp4',
    sourceType: 'local-video',
    folderName: '001',
    createdAt: '2026-04-30T12:00:00.000Z'
  }]), [
    'index,file_name,source_type,folder_name,created_at',
    '001,video1.mp4,local-video,001,2026-04-30T12:00:00.000Z',
    ''
  ].join('\n'));
});

test('toMetaJson and toLabelsJson write stable pretty JSON', () => {
  assert.equal(toMetaJson({ index: '001', eventCount: 1 }), '{\n  "index": "001",\n  "eventCount": 1\n}\n');
  assert.equal(toLabelsJson({ videoIndex: '001', events: [] }), '{\n  "videoIndex": "001",\n  "events": []\n}\n');
});
