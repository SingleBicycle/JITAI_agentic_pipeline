# Video Labeler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a plain HTML/CSS/JS video labeling app that imports public video links, captures timestamped labels, and writes session files into a user-chosen local folder without a backend.

**Architecture:** Use a static single-page app served locally during development, with ES modules split by responsibility. Keep core logic pure and testable with Node's built-in test runner, then wire browser-only pieces such as the File System Access API and video player adapters on top.

**Tech Stack:** Plain HTML, CSS, browser ES modules, Node built-in test runner, File System Access API, YouTube IFrame API, Python `http.server` for local serving

---

**Repository note:** The current directory is not a git repository, so these tasks use verification checkpoints instead of commit steps.

## File Structure

- Create: `package.json`
- Create: `config/labels.json`
- Create: `index.html`
- Create: `styles.css`
- Create: `src/main.js`
- Create: `src/lib/parser.js`
- Create: `src/lib/indexer.js`
- Create: `src/lib/labels.js`
- Create: `src/lib/serializer.js`
- Create: `src/lib/storage.js`
- Create: `src/player/detect-source.js`
- Create: `src/player/html5-video-adapter.js`
- Create: `src/player/youtube-adapter.js`
- Create: `src/player/unsupported-adapter.js`
- Create: `src/player/create-player-controller.js`
- Create: `src/state/session.js`
- Create: `src/ui/render.js`
- Create: `src/ui/dom.js`
- Create: `tests/parser.test.js`
- Create: `tests/indexer.test.js`
- Create: `tests/labels.test.js`
- Create: `tests/serializer.test.js`
- Create: `tests/storage.test.js`
- Create: `tests/player.test.js`
- Create: `tests/session.test.js`
- Create: `README.md`

### Task 1: Bootstrap the project and implement import/indexing core

**Files:**
- Create: `package.json`
- Create: `config/labels.json`
- Create: `tests/parser.test.js`
- Create: `tests/indexer.test.js`
- Create: `src/lib/parser.js`
- Create: `src/lib/indexer.js`

- [ ] **Step 1: Write the failing parser and indexer tests**

```js
// tests/parser.test.js
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
```

```js
// tests/indexer.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import { appendIndexedUrls } from '../src/lib/indexer.js';

test('appendIndexedUrls assigns zero-padded indexes and folder names', () => {
  const result = appendIndexedUrls([], [
    'https://example.com/a.mp4',
    'https://example.com/b.mp4'
  ]);

  assert.deepEqual(result.items.map((item) => item.index), ['001', '002']);
  assert.deepEqual(result.items.map((item) => item.folderName), ['001', '002']);
});

test('appendIndexedUrls skips duplicates already present in the session', () => {
  const existing = [{
    index: '001',
    sourceUrl: 'https://example.com/a.mp4',
    sourceType: 'html5-video',
    folderName: '001',
    status: 'ready'
  }];

  const result = appendIndexedUrls(existing, [
    'https://example.com/a.mp4',
    'https://youtu.be/abc123'
  ]);

  assert.equal(result.items.length, 2);
  assert.deepEqual(result.added.map((item) => item.index), ['002']);
  assert.equal(result.added[0].sourceUrl, 'https://youtu.be/abc123');
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node --test tests/parser.test.js tests/indexer.test.js`

Expected: FAIL with `ERR_MODULE_NOT_FOUND` because `src/lib/parser.js` and `src/lib/indexer.js` do not exist yet.

- [ ] **Step 3: Write the minimal implementation and project config**

```json
// package.json
{
  "name": "video-labeler",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "node --test",
    "start": "python3 -m http.server 4173"
  }
}
```

```json
// config/labels.json
{
  "defaults": ["start", "end", "erase"]
}
```

```js
// src/lib/parser.js
export function parseImportedText(input) {
  const tokens = input
    .split(/[\n,\r]+/)
    .map((value) => value.trim())
    .filter(Boolean);

  const urls = [];
  const rejected = [];

  for (const token of tokens) {
    try {
      urls.push(new URL(token).toString());
    } catch {
      rejected.push(token);
    }
  }

  return { urls, rejected };
}
```

```js
// src/lib/indexer.js
function padIndex(value) {
  return String(value).padStart(3, '0');
}

function detectInitialSourceType(url) {
  return /youtu\.be|youtube\.com/.test(url) ? 'youtube' : 'html5-video';
}

export function appendIndexedUrls(existingItems, incomingUrls) {
  const seen = new Set(existingItems.map((item) => item.sourceUrl));
  const items = [...existingItems];
  const added = [];
  let nextNumber = items.length + 1;

  for (const sourceUrl of incomingUrls) {
    if (seen.has(sourceUrl)) continue;
    seen.add(sourceUrl);

    const index = padIndex(nextNumber++);
    const item = {
      index,
      sourceUrl,
      sourceType: detectInitialSourceType(sourceUrl),
      folderName: index,
      status: 'ready'
    };

    items.push(item);
    added.push(item);
  }

  return { items, added };
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `node --test tests/parser.test.js tests/indexer.test.js`

Expected: PASS with 4 passing tests.

- [ ] **Step 5: Checkpoint the bootstrap files**

Run: `node --test tests/parser.test.js tests/indexer.test.js`

Expected: PASS and the repo now contains `package.json`, `config/labels.json`, and the two core import modules.

### Task 2: Add label reduction and JSON/CSV serialization

**Files:**
- Create: `tests/labels.test.js`
- Create: `tests/serializer.test.js`
- Create: `src/lib/labels.js`
- Create: `src/lib/serializer.js`

- [ ] **Step 1: Write the failing label and serializer tests**

```js
// tests/labels.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import { applyLabelAction } from '../src/lib/labels.js';

test('applyLabelAction appends a timestamped label entry', () => {
  const result = applyLabelAction([], {
    action: 'start',
    timestampSeconds: 12.34,
    createdAt: '2026-04-11T12:00:00.000Z'
  });

  assert.deepEqual(result, [{
    label: 'start',
    timestampSeconds: 12.34,
    createdAt: '2026-04-11T12:00:00.000Z'
  }]);
});

test('applyLabelAction removes the most recent label when action is erase', () => {
  const result = applyLabelAction([
    { label: 'start', timestampSeconds: 1, createdAt: 'a' },
    { label: 'end', timestampSeconds: 2, createdAt: 'b' }
  ], {
    action: 'erase'
  });

  assert.deepEqual(result, [
    { label: 'start', timestampSeconds: 1, createdAt: 'a' }
  ]);
});
```

```js
// tests/serializer.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import { toIndexCsv, toMetaJson, toLabelsJson } from '../src/lib/serializer.js';

test('toIndexCsv writes the expected header and rows', () => {
  const csv = toIndexCsv([{
    index: '001',
    sourceUrl: 'https://example.com/a.mp4',
    sourceType: 'html5-video',
    folderName: '001',
    createdAt: '2026-04-11T12:00:00.000Z'
  }]);

  assert.equal(
    csv,
    'index,source_url,source_type,folder_name,created_at\\n001,https://example.com/a.mp4,html5-video,001,2026-04-11T12:00:00.000Z\\n'
  );
});

test('toLabelsJson and toMetaJson return stable JSON payloads', () => {
  const meta = toMetaJson({
    index: '001',
    folderName: '001',
    sourceUrl: 'https://example.com/a.mp4',
    sourceType: 'html5-video',
    createdAt: '2026-04-11T12:00:00.000Z',
    durationSeconds: 10,
    seekable: true,
    labelOptions: ['start', 'end'],
    customLabelsUsed: [],
    capabilities: { timing: true, duration: true }
  });

  const labels = toLabelsJson({
    videoIndex: '001',
    sourceUrl: 'https://example.com/a.mp4',
    labels: [{ label: 'start', timestampSeconds: 1.23, createdAt: 't' }]
  });

  assert.match(meta, /"durationSeconds": 10/);
  assert.match(labels, /"label": "start"/);
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node --test tests/labels.test.js tests/serializer.test.js`

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `src/lib/labels.js` and `src/lib/serializer.js`.

- [ ] **Step 3: Write the minimal implementation**

```js
// src/lib/labels.js
export function applyLabelAction(existingLabels, payload) {
  if (payload.action === 'erase') {
    return existingLabels.slice(0, -1);
  }

  return [...existingLabels, {
    label: payload.action,
    timestampSeconds: payload.timestampSeconds,
    createdAt: payload.createdAt
  }];
}
```

```js
// src/lib/serializer.js
function stableJson(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}

export function toIndexCsv(items) {
  const header = 'index,source_url,source_type,folder_name,created_at\n';
  const rows = items.map((item) => [
    item.index,
    item.sourceUrl,
    item.sourceType,
    item.folderName,
    item.createdAt
  ].join(','));

  return `${header}${rows.join('\n')}${rows.length ? '\n' : ''}`;
}

export function toMetaJson(item) {
  return stableJson(item);
}

export function toLabelsJson(payload) {
  return stableJson(payload);
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `node --test tests/labels.test.js tests/serializer.test.js`

Expected: PASS with 4 passing tests.

- [ ] **Step 5: Checkpoint the serialization layer**

Run: `node --test tests/parser.test.js tests/indexer.test.js tests/labels.test.js tests/serializer.test.js`

Expected: PASS with 8 passing tests.

### Task 3: Implement local folder storage with File System Access API wrappers

**Files:**
- Create: `tests/storage.test.js`
- Create: `src/lib/storage.js`

- [ ] **Step 1: Write the failing storage tests**

```js
// tests/storage.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import { createStorageClient } from '../src/lib/storage.js';

function createFakeDirectoryHandle() {
  const files = new Map();
  const dirs = new Map();

  return {
    files,
    dirs,
    async getFileHandle(name, options = {}) {
      if (!files.has(name) && options.create) {
        files.set(name, { name, content: '' });
      }
      return {
        async createWritable() {
          return {
            async write(content) {
              files.get(name).content = content;
            },
            async close() {}
          };
        }
      };
    },
    async getDirectoryHandle(name, options = {}) {
      if (!dirs.has(name) && options.create) {
        dirs.set(name, createFakeDirectoryHandle());
      }
      return dirs.get(name);
    }
  };
}

test('createStorageClient writes index.csv in the root folder', async () => {
  const root = createFakeDirectoryHandle();
  const client = createStorageClient(root);

  await client.writeIndex([{
    index: '001',
    sourceUrl: 'https://example.com/a.mp4',
    sourceType: 'html5-video',
    folderName: '001',
    createdAt: '2026-04-11T12:00:00.000Z'
  }]);

  assert.match(root.files.get('index.csv').content, /^index,/);
});

test('createStorageClient writes meta.json and labels.json in a video folder', async () => {
  const root = createFakeDirectoryHandle();
  const client = createStorageClient(root);

  await client.writeVideoFiles({
    item: {
      index: '001',
      folderName: '001',
      sourceUrl: 'https://example.com/a.mp4',
      sourceType: 'html5-video',
      createdAt: '2026-04-11T12:00:00.000Z'
    },
    meta: { index: '001' },
    labels: { videoIndex: '001', labels: [] }
  });

  const videoDir = root.dirs.get('001');
  assert.ok(videoDir.files.get('meta.json'));
  assert.ok(videoDir.files.get('labels.json'));
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node --test tests/storage.test.js`

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `src/lib/storage.js`.

- [ ] **Step 3: Write the minimal implementation**

```js
// src/lib/storage.js
import { toIndexCsv, toMetaJson, toLabelsJson } from './serializer.js';

async function writeTextFile(directoryHandle, name, content) {
  const fileHandle = await directoryHandle.getFileHandle(name, { create: true });
  const writable = await fileHandle.createWritable();
  await writable.write(content);
  await writable.close();
}

export function createStorageClient(rootDirectoryHandle) {
  return {
    async writeIndex(items) {
      await writeTextFile(rootDirectoryHandle, 'index.csv', toIndexCsv(items));
    },

    async writeVideoFiles({ item, meta, labels }) {
      const videoDir = await rootDirectoryHandle.getDirectoryHandle(item.folderName, { create: true });
      await writeTextFile(videoDir, 'meta.json', toMetaJson(meta));
      await writeTextFile(videoDir, 'labels.json', toLabelsJson(labels));
    }
  };
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `node --test tests/storage.test.js`

Expected: PASS with 2 passing tests.

- [ ] **Step 5: Checkpoint full core logic**

Run: `npm test`

Expected: PASS with parser, indexer, labels, serializer, and storage tests all green.

### Task 4: Implement source detection and player adapters

**Files:**
- Create: `tests/player.test.js`
- Create: `src/player/detect-source.js`
- Create: `src/player/html5-video-adapter.js`
- Create: `src/player/youtube-adapter.js`
- Create: `src/player/unsupported-adapter.js`
- Create: `src/player/create-player-controller.js`

- [ ] **Step 1: Write the failing player tests**

```js
// tests/player.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import { detectSource } from '../src/player/detect-source.js';

test('detectSource identifies YouTube URLs', () => {
  assert.deepEqual(detectSource('https://www.youtube.com/watch?v=abc123'), {
    sourceType: 'youtube',
    embedId: 'abc123'
  });
});

test('detectSource identifies direct video URLs', () => {
  assert.deepEqual(detectSource('https://cdn.example.com/video.mp4'), {
    sourceType: 'html5-video',
    embedId: null
  });
});

test('detectSource marks unsupported URLs clearly', () => {
  assert.deepEqual(detectSource('https://example.com/page'), {
    sourceType: 'unsupported',
    embedId: null
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node --test tests/player.test.js`

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `src/player/detect-source.js`.

- [ ] **Step 3: Write the minimal implementation**

```js
// src/player/detect-source.js
function getYouTubeId(url) {
  const parsed = new URL(url);
  if (parsed.hostname.includes('youtu.be')) {
    return parsed.pathname.slice(1) || null;
  }
  if (parsed.hostname.includes('youtube.com')) {
    return parsed.searchParams.get('v');
  }
  return null;
}

export function detectSource(url) {
  const youtubeId = getYouTubeId(url);
  if (youtubeId) {
    return { sourceType: 'youtube', embedId: youtubeId };
  }

  if (/\.(mp4|webm|ogg)(\?|#|$)/i.test(url)) {
    return { sourceType: 'html5-video', embedId: null };
  }

  return { sourceType: 'unsupported', embedId: null };
}
```

```js
// src/player/html5-video-adapter.js
export function createHtml5VideoAdapter(videoElement) {
  return {
    async load(source) {
      videoElement.src = source.sourceUrl;
      videoElement.load();
    },
    play() { return videoElement.play(); },
    pause() { videoElement.pause(); },
    getCurrentTime() { return videoElement.currentTime || 0; },
    getDuration() { return Number.isFinite(videoElement.duration) ? videoElement.duration : null; },
    isSeekable() { return (videoElement.seekable?.length ?? 0) > 0; },
    getCapabilities() {
      return {
        timing: true,
        duration: Number.isFinite(videoElement.duration)
      };
    }
  };
}
```

```js
// src/player/youtube-adapter.js
export function createYouTubeAdapter(iframeHost) {
  let player = null;

  return {
    async load(source) {
      iframeHost.innerHTML = `<div id="youtube-player"></div>`;
      player = new window.YT.Player('youtube-player', {
        videoId: source.embedId
      });
    },
    play() { player?.playVideo(); },
    pause() { player?.pauseVideo(); },
    getCurrentTime() { return player?.getCurrentTime?.() ?? 0; },
    getDuration() { return player?.getDuration?.() ?? null; },
    isSeekable() { return true; },
    getCapabilities() { return { timing: true, duration: true }; }
  };
}
```

```js
// src/player/unsupported-adapter.js
export function createUnsupportedAdapter() {
  return {
    async load() {},
    play() {},
    pause() {},
    getCurrentTime() { return null; },
    getDuration() { return null; },
    isSeekable() { return false; },
    getCapabilities() { return { timing: false, duration: false }; }
  };
}
```

```js
// src/player/create-player-controller.js
import { detectSource } from './detect-source.js';
import { createHtml5VideoAdapter } from './html5-video-adapter.js';
import { createYouTubeAdapter } from './youtube-adapter.js';
import { createUnsupportedAdapter } from './unsupported-adapter.js';

export function createPlayerController(elements) {
  return {
    async load(item) {
      const detected = detectSource(item.sourceUrl);
      if (detected.sourceType === 'youtube') {
        this.adapter = createYouTubeAdapter(elements.youtubeHost);
      } else if (detected.sourceType === 'html5-video') {
        this.adapter = createHtml5VideoAdapter(elements.video);
      } else {
        this.adapter = createUnsupportedAdapter();
      }

      await this.adapter.load({ ...item, ...detected });
      return detected;
    },
    getCurrentTime() {
      return this.adapter?.getCurrentTime?.() ?? null;
    },
    getCapabilities() {
      return this.adapter?.getCapabilities?.() ?? { timing: false, duration: false };
    }
  };
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `node --test tests/player.test.js`

Expected: PASS with 3 passing tests.

- [ ] **Step 5: Checkpoint the player layer**

Run: `npm test`

Expected: PASS and the source-detection behavior is now fixed under test.

### Task 5: Implement session state and the single-page UI shell

**Files:**
- Create: `tests/session.test.js`
- Create: `index.html`
- Create: `styles.css`
- Create: `src/state/session.js`
- Create: `src/ui/dom.js`
- Create: `src/ui/render.js`
- Create: `src/main.js`

- [ ] **Step 1: Write the failing session-state test**

```js
// tests/session.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import { createSessionState, appendImportedUrls, selectVideo } from '../src/state/session.js';

test('appendImportedUrls adds new queue items and auto-selects the first item', () => {
  const state = createSessionState();
  appendImportedUrls(state, [
    {
      index: '001',
      sourceUrl: 'https://example.com/a.mp4',
      sourceType: 'html5-video',
      folderName: '001',
      status: 'ready',
      createdAt: '2026-04-11T12:00:00.000Z',
      labels: []
    }
  ]);

  assert.equal(state.items.length, 1);
  assert.equal(state.currentIndex, '001');
});

test('selectVideo switches the active item by index', () => {
  const state = createSessionState();
  state.items = [
    { index: '001', labels: [] },
    { index: '002', labels: [] }
  ];

  selectVideo(state, '002');

  assert.equal(state.currentIndex, '002');
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node --test tests/session.test.js`

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `src/state/session.js`.

- [ ] **Step 3: Write the minimal implementation and UI shell**

```js
// src/state/session.js
export function createSessionState() {
  return {
    outputDirectoryHandle: null,
    items: [],
    currentIndex: null,
    importErrors: [],
    importSummary: null,
    lastSaveError: null
  };
}

export function appendImportedUrls(state, items) {
  state.items.push(...items);
  if (!state.currentIndex && state.items.length > 0) {
    state.currentIndex = state.items[0].index;
  }
}

export function selectVideo(state, index) {
  state.currentIndex = index;
}
```

```html
<!-- index.html -->
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Labeler</title>
    <link rel="stylesheet" href="./styles.css">
  </head>
  <body>
    <main class="app-shell">
      <section class="panel import-panel">
        <h1>Video Labeler</h1>
        <textarea id="link-input" placeholder="Paste one or many links"></textarea>
        <div class="row">
          <button id="import-text-button">Import Links</button>
          <input id="file-input" type="file" accept=".txt,.csv">
        </div>
        <p id="import-report"></p>
      </section>

      <section class="panel session-panel">
        <button id="choose-folder-button">Choose Output Folder</button>
        <p id="save-status">No folder selected</p>
      </section>

      <section class="panel queue-panel">
        <ul id="queue-list"></ul>
      </section>

      <section class="panel player-panel">
        <div id="player-status">No video selected</div>
        <video id="video-element" controls></video>
        <div id="youtube-host"></div>
        <div class="row">
          <button id="previous-button">Previous</button>
          <button id="next-button">Next</button>
          <button id="toggle-labels-button">Labels</button>
        </div>
        <div id="label-menu" hidden></div>
        <ul id="labels-list"></ul>
      </section>
    </main>

    <script type="module" src="./src/main.js"></script>
    <script src="https://www.youtube.com/iframe_api"></script>
  </body>
</html>
```

```css
/* styles.css */
:root {
  --bg: #f6f2e8;
  --panel: rgba(255, 252, 247, 0.92);
  --line: #d4c5a8;
  --ink: #2e2419;
  --accent: #8d4f2c;
}

body {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  color: var(--ink);
  background:
    radial-gradient(circle at top left, rgba(194, 141, 85, 0.18), transparent 28%),
    linear-gradient(180deg, #f8f3ea 0%, #efe3d0 100%);
}

.app-shell {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
  padding: 16px;
}

.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 16px;
}
```

```js
// src/ui/dom.js
export function getDom() {
  return {
    linkInput: document.querySelector('#link-input'),
    fileInput: document.querySelector('#file-input'),
    importTextButton: document.querySelector('#import-text-button'),
    chooseFolderButton: document.querySelector('#choose-folder-button'),
    saveStatus: document.querySelector('#save-status'),
    importReport: document.querySelector('#import-report'),
    queueList: document.querySelector('#queue-list'),
    playerStatus: document.querySelector('#player-status'),
    video: document.querySelector('#video-element'),
    youtubeHost: document.querySelector('#youtube-host'),
    previousButton: document.querySelector('#previous-button'),
    nextButton: document.querySelector('#next-button'),
    toggleLabelsButton: document.querySelector('#toggle-labels-button'),
    labelMenu: document.querySelector('#label-menu'),
    labelsList: document.querySelector('#labels-list')
  };
}
```

```js
// src/ui/render.js
export function renderQueue(dom, state) {
  dom.queueList.innerHTML = state.items.map((item) => `
    <li data-index="${item.index}">
      <button type="button" data-select-index="${item.index}">
        ${item.index} · ${item.sourceUrl}
      </button>
    </li>
  `).join('');
}

export function renderSaveStatus(dom, state) {
  dom.saveStatus.textContent = state.outputDirectoryHandle ? 'Output folder ready' : 'No folder selected';
}

export function renderImportReport(dom, state) {
  if (!state.importSummary) {
    dom.importReport.textContent = '';
    return;
  }

  const { addedCount, duplicateCount, rejectedCount } = state.importSummary;
  dom.importReport.textContent = `Added ${addedCount}, skipped ${duplicateCount} duplicates, rejected ${rejectedCount} malformed entries.`;
}

export function renderLabels(dom, item) {
  dom.labelsList.innerHTML = (item?.labels ?? []).map((label) => `
    <li>${label.label} @ ${label.timestampSeconds.toFixed(2)}s</li>
  `).join('');
}
```

```js
// src/main.js
import { getDom } from './ui/dom.js';
import { renderQueue, renderSaveStatus, renderLabels, renderImportReport } from './ui/render.js';
import { createSessionState } from './state/session.js';

const state = createSessionState();
const dom = getDom();

renderQueue(dom, state);
renderSaveStatus(dom, state);
renderLabels(dom, null);
renderImportReport(dom, state);
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `node --test tests/session.test.js`

Expected: PASS with 2 passing tests.

- [ ] **Step 5: Checkpoint the UI shell**

Run: `npm test`

Expected: PASS, and opening `http://localhost:4173` after `npm run start` shows the four-panel layout with empty-state controls.

### Task 6: Wire imports, labeling, local writes, and manual verification

**Files:**
- Modify: `src/main.js`
- Modify: `src/ui/render.js`
- Modify: `src/state/session.js`
- Modify: `src/lib/indexer.js`
- Modify: `src/player/create-player-controller.js`
- Modify: `README.md`

- [ ] **Step 1: Write the failing integration-oriented session test**

```js
// tests/session.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createSessionState,
  appendImportedUrls,
  recordLabelForCurrentItem,
  eraseLabelForCurrentItem
} from '../src/state/session.js';

test('recordLabelForCurrentItem appends to the active video labels', () => {
  const state = createSessionState();
  appendImportedUrls(state, [{
    index: '001',
    sourceUrl: 'https://example.com/a.mp4',
    sourceType: 'html5-video',
    folderName: '001',
    status: 'ready',
    createdAt: '2026-04-11T12:00:00.000Z',
    labels: []
  }]);

  recordLabelForCurrentItem(state, {
    action: 'start',
    timestampSeconds: 1.25,
    createdAt: '2026-04-11T12:01:00.000Z'
  });

  assert.equal(state.items[0].labels.length, 1);
  assert.equal(state.items[0].labels[0].label, 'start');
});

test('eraseLabelForCurrentItem removes the latest label on the active video', () => {
  const state = createSessionState();
  appendImportedUrls(state, [{
    index: '001',
    sourceUrl: 'https://example.com/a.mp4',
    sourceType: 'html5-video',
    folderName: '001',
    status: 'ready',
    createdAt: '2026-04-11T12:00:00.000Z',
    labels: [{ label: 'start', timestampSeconds: 1.25, createdAt: 't' }]
  }]);

  eraseLabelForCurrentItem(state);

  assert.deepEqual(state.items[0].labels, []);
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node --test tests/session.test.js`

Expected: FAIL because `recordLabelForCurrentItem` and `eraseLabelForCurrentItem` are not defined yet.

- [ ] **Step 3: Implement the final wiring**

```js
// src/state/session.js
import { applyLabelAction } from '../lib/labels.js';

export function getCurrentItem(state) {
  return state.items.find((item) => item.index === state.currentIndex) ?? null;
}

export function recordLabelForCurrentItem(state, payload) {
  const item = getCurrentItem(state);
  if (!item) return;
  item.labels = applyLabelAction(item.labels, payload);
}

export function eraseLabelForCurrentItem(state) {
  const item = getCurrentItem(state);
  if (!item) return;
  item.labels = applyLabelAction(item.labels, { action: 'erase' });
}

export function selectRelativeVideo(state, offset) {
  const currentPosition = state.items.findIndex((item) => item.index === state.currentIndex);
  if (currentPosition === -1) return;
  const nextPosition = currentPosition + offset;
  if (nextPosition < 0 || nextPosition >= state.items.length) return;
  state.currentIndex = state.items[nextPosition].index;
}
```

```js
// src/main.js
import { getDom } from './ui/dom.js';
import { renderQueue, renderSaveStatus, renderLabels, renderImportReport } from './ui/render.js';
import {
  createSessionState,
  appendImportedUrls,
  selectVideo,
  getCurrentItem,
  selectRelativeVideo,
  recordLabelForCurrentItem,
  eraseLabelForCurrentItem
} from './state/session.js';
import { parseImportedText } from './lib/parser.js';
import { appendIndexedUrls } from './lib/indexer.js';
import { createStorageClient } from './lib/storage.js';
import { createPlayerController } from './player/create-player-controller.js';

const state = createSessionState();
const dom = getDom();
const player = createPlayerController(dom);
let storage = null;
const labelsConfig = await fetch('../config/labels.json').then((response) => response.json());

function nowIso() {
  return new Date().toISOString();
}

async function persistState() {
  if (!storage) return;
  await storage.writeIndex(state.items.map((item) => ({
    index: item.index,
    sourceUrl: item.sourceUrl,
    sourceType: item.sourceType,
    folderName: item.folderName,
    createdAt: item.createdAt
  })));

  for (const item of state.items) {
    await storage.writeVideoFiles({
      item,
      meta: {
        index: item.index,
        folderName: item.folderName,
        sourceUrl: item.sourceUrl,
        sourceType: item.sourceType,
        createdAt: item.createdAt,
        durationSeconds: item.durationSeconds ?? null,
        seekable: item.seekable ?? false,
        labelOptions: labelsConfig.defaults.filter((label) => label !== 'erase'),
        customLabelsUsed: item.customLabelsUsed ?? [],
        capabilities: item.capabilities ?? { timing: false, duration: false }
      },
      labels: {
        videoIndex: item.index,
        sourceUrl: item.sourceUrl,
        labels: item.labels
      }
    });
  }
}

async function loadCurrentItem() {
  const item = getCurrentItem(state);
  if (!item) return;
  const detected = await player.load(item);
  item.sourceType = detected.sourceType;
  item.capabilities = player.getCapabilities();
  item.durationSeconds = player.adapter?.getDuration?.() ?? null;
  item.seekable = player.adapter?.isSeekable?.() ?? false;
  dom.playerStatus.textContent = item.capabilities.timing
    ? `Loaded ${item.index} (${item.sourceType})`
    : `Loaded ${item.index}, but timestamp capture is unavailable for this source`;
  renderLabels(dom, item);
  await persistState();
}

async function importUrlsFromText(rawText) {
  const parsed = parseImportedText(rawText);
  const indexed = appendIndexedUrls(state.items, parsed.urls);

  state.importErrors = parsed.rejected;
  state.importSummary = {
    addedCount: indexed.added.length,
    duplicateCount: parsed.urls.length - indexed.added.length,
    rejectedCount: parsed.rejected.length
  };

  appendImportedUrls(state, indexed.added.map((item) => ({
    ...item,
    createdAt: nowIso(),
    labels: [],
    customLabelsUsed: []
  })));

  renderQueue(dom, state);
  renderImportReport(dom, state);
  await persistState();
  await loadCurrentItem();
}

dom.importTextButton.addEventListener('click', async () => {
  await importUrlsFromText(dom.linkInput.value);
});

dom.fileInput.addEventListener('change', async () => {
  const file = dom.fileInput.files?.[0];
  if (!file) return;
  await importUrlsFromText(await file.text());
});

dom.chooseFolderButton.addEventListener('click', async () => {
  state.outputDirectoryHandle = await window.showDirectoryPicker();
  storage = createStorageClient(state.outputDirectoryHandle);
  renderSaveStatus(dom, state);
  await persistState();
});

dom.queueList.addEventListener('click', async (event) => {
  const button = event.target.closest('[data-select-index]');
  if (!button) return;
  selectVideo(state, button.dataset.selectIndex);
  await loadCurrentItem();
});

dom.previousButton.addEventListener('click', async () => {
  selectRelativeVideo(state, -1);
  await loadCurrentItem();
});

dom.nextButton.addEventListener('click', async () => {
  selectRelativeVideo(state, 1);
  await loadCurrentItem();
});

dom.toggleLabelsButton.addEventListener('click', () => {
  dom.labelMenu.hidden = !dom.labelMenu.hidden;
});

dom.labelMenu.innerHTML = [
  ...labelsConfig.defaults.map((label) => `<button type="button" data-label-action="${label}">${label}</button>`),
  '<input id="custom-label-input" placeholder="Custom label">',
  '<button type="button" data-label-action="custom">Apply Custom</button>'
].join('');

dom.labelMenu.addEventListener('click', async (event) => {
  const button = event.target.closest('[data-label-action]');
  if (!button) return;

  const currentTime = player.getCurrentTime();
  if (currentTime == null) return;

  if (button.dataset.labelAction === 'erase') {
    eraseLabelForCurrentItem(state);
  } else {
    const action = button.dataset.labelAction === 'custom'
      ? document.querySelector('#custom-label-input').value.trim()
      : button.dataset.labelAction;
    if (!action) return;

    recordLabelForCurrentItem(state, {
      action,
      timestampSeconds: currentTime,
      createdAt: nowIso()
    });

    const item = getCurrentItem(state);
    const builtInLabels = new Set(labelsConfig.defaults);
    if (item && !builtInLabels.has(action) && !item.customLabelsUsed.includes(action)) {
      item.customLabelsUsed.push(action);
    }
  }

  renderLabels(dom, getCurrentItem(state));
  await persistState();
});

renderQueue(dom, state);
renderSaveStatus(dom, state);
renderImportReport(dom, state);
```

```md
<!-- README.md -->
# Video Labeler

## Run

1. `npm test`
2. `npm run start`
3. Open `http://localhost:4173`
4. Use Chrome or Edge so folder writes work

## Manual smoke checklist

- Choose an output folder
- Paste a direct `.mp4` URL and confirm `001/meta.json`, `001/labels.json`, and `index.csv` are written
- Paste a YouTube URL and confirm timestamps save while the embedded player is active
- Upload a mixed `.txt` or `.csv` file and confirm malformed rows are reported while valid rows still import
- Click `erase` and confirm the last label disappears from the UI and `labels.json`
- Use previous and next to move through the queue, then confirm new imports append as `002`, `003`, and so on
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test`

Expected: PASS with all test files green, including the updated session tests.

- [ ] **Step 5: Run the manual verification flow**

Run: `npm run start`

Expected: `Serving HTTP on ... port 4173` from Python. Then open `http://localhost:4173` in Chrome or Edge and complete the README smoke checklist, confirming that:

- imported links create indexed queue entries
- selecting an output folder enables file writes
- direct video labels and YouTube labels write `meta.json` and `labels.json`
- malformed upload rows are reported without blocking valid imports
- `erase` removes the latest label entry
- importing more links appends to `index.csv` and creates the next numbered folders
