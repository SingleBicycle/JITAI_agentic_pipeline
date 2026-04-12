# Video Labeler Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve the current static video labeler so `【label】` creates persistent markers immediately, `start`/`end` produce structured clip records with descriptions, `meta.json` includes `title`, and the interface adopts the approved Editorial Slate redesign.

**Architecture:** Keep the existing static HTML/CSS/JS app and update its state model, serializers, player metadata extraction, and renderer. Preserve testable logic in pure modules, then wire the redesigned UI behavior in the browser layer.

**Tech Stack:** Plain HTML, CSS, browser ES modules, Node built-in test runner, File System Access API, YouTube IFrame API, Python `http.server`

---

**Repository note:** The current directory is not a git repository, so execution should use verification checkpoints instead of commit steps.

## File Structure

- Modify: `src/lib/labels.js`
- Modify: `src/lib/serializer.js`
- Modify: `src/lib/storage.js`
- Modify: `src/player/detect-source.js`
- Modify: `src/player/youtube-adapter.js`
- Modify: `src/player/create-player-controller.js`
- Modify: `src/state/session.js`
- Modify: `src/ui/render.js`
- Modify: `src/ui/dom.js`
- Modify: `src/main.js`
- Modify: `styles.css`
- Modify: `index.html`
- Modify: `README.md`
- Modify: `tests/labels.test.js`
- Modify: `tests/serializer.test.js`
- Modify: `tests/player.test.js`
- Modify: `tests/session.test.js`

### Task 1: Redesign label logic around markers and clips

**Files:**
- Modify: `tests/labels.test.js`
- Modify: `src/lib/labels.js`

- [ ] **Step 1: Write the failing tests for markers, clips, and erase behavior**

```js
// tests/labels.test.js
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node --test tests/labels.test.js`

Expected: FAIL because the new exports and marker/clip logic do not exist in `src/lib/labels.js`.

- [ ] **Step 3: Write the minimal implementation**

```js
// src/lib/labels.js
export function createMarker(payload) {
  return {
    id: payload.id,
    timestampSeconds: payload.timestampSeconds,
    createdAt: payload.createdAt,
    kind: payload.kind
  };
}

function findLatestOpenStart(markers, clips) {
  const closedStartIds = new Set(clips.map((clip) => clip.startMarkerId));
  return [...markers]
    .reverse()
    .find((marker) => marker.kind === 'start' && !closedStartIds.has(marker.id)) ?? null;
}

export function applyMarkerAction(state, payload) {
  if (payload.eraseLast) {
    const nextMarkers = state.markers.slice(0, -1);
    const removedMarker = state.markers.at(-1);
    const nextClips = removedMarker
      ? state.clips.filter((clip) => clip.startMarkerId !== removedMarker.id && clip.endMarkerId !== removedMarker.id)
      : state.clips;
    return { markers: nextMarkers, clips: nextClips };
  }

  const markers = [...state.markers, payload.marker];
  const clips = [...state.clips];

  if (payload.marker.kind === 'end') {
    const openStart = findLatestOpenStart(state.markers, state.clips);
    if (openStart) {
      clips.push({
        id: payload.clipId,
        startMarkerId: openStart.id,
        endMarkerId: payload.marker.id,
        startTimestampSeconds: openStart.timestampSeconds,
        endTimestampSeconds: payload.marker.timestampSeconds,
        description: '',
        createdAt: payload.marker.createdAt
      });
    }
  }

  return { markers, clips };
}

export function applyClipDescription(clips, description) {
  if (!clips.length) return clips;
  const nextClips = [...clips];
  const lastClip = nextClips.at(-1);
  nextClips[nextClips.length - 1] = {
    ...lastClip,
    description
  };
  return nextClips;
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `node --test tests/labels.test.js`

Expected: PASS with the updated marker and clip tests all green.

- [ ] **Step 5: Checkpoint the new label core**

Run: `node --test tests/labels.test.js tests/session.test.js`

Expected: PASS and the codebase now has a dedicated marker/clip logic layer.

### Task 2: Update serializers and metadata shape for markers, clips, and title

**Files:**
- Modify: `tests/serializer.test.js`
- Modify: `src/lib/serializer.js`

- [ ] **Step 1: Write the failing serializer tests**

```js
// tests/serializer.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import { toMetaJson, toLabelsJson } from '../src/lib/serializer.js';

test('toLabelsJson writes markers and clips arrays', () => {
  const json = toLabelsJson({
    videoIndex: '001',
    sourceUrl: 'https://example.com/a.mp4',
    markers: [{ id: 'm1', timestampSeconds: 10, createdAt: 'a', kind: 'marker' }],
    clips: [{ id: 'c1', startMarkerId: 'm1', endMarkerId: 'm2', startTimestampSeconds: 10, endTimestampSeconds: 20, description: '', createdAt: 'b' }]
  });

  assert.match(json, /"markers"/);
  assert.match(json, /"clips"/);
});

test('toMetaJson writes title and clip summary fields', () => {
  const json = toMetaJson({
    index: '001',
    folderName: '001',
    sourceUrl: 'https://example.com/a.mp4',
    sourceType: 'html5-video',
    title: 'a.mp4',
    titleSource: 'filename',
    createdAt: '2026-04-11T12:00:00.000Z',
    durationSeconds: 10,
    seekable: true,
    clipCount: 1,
    hasOpenStartMarker: false,
    capabilities: { timing: true, duration: true }
  });

  assert.match(json, /"title": "a.mp4"/);
  assert.match(json, /"clipCount": 1/);
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node --test tests/serializer.test.js`

Expected: FAIL because the serializer tests no longer match the old flat label structure.

- [ ] **Step 3: Update the serializer implementation**

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

Run: `node --test tests/serializer.test.js`

Expected: PASS with the updated metadata and labels serialization tests green.

- [ ] **Step 5: Checkpoint serialization**

Run: `npm test`

Expected: PASS with no regressions in other test files.

### Task 3: Add title extraction for YouTube and direct video sources

**Files:**
- Modify: `tests/player.test.js`
- Modify: `src/player/detect-source.js`
- Modify: `src/player/youtube-adapter.js`
- Modify: `src/player/create-player-controller.js`

- [ ] **Step 1: Write the failing player metadata tests**

```js
// tests/player.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import { detectSource, deriveTitleFromUrl } from '../src/player/detect-source.js';

test('detectSource still identifies YouTube Shorts URLs', () => {
  assert.deepEqual(detectSource('https://www.youtube.com/shorts/-VZ_F5h6fTk'), {
    sourceType: 'youtube',
    embedId: '-VZ_F5h6fTk'
  });
});

test('deriveTitleFromUrl falls back to the final path segment for direct media', () => {
  assert.deepEqual(deriveTitleFromUrl('https://cdn.example.com/folder/clip-01.mp4'), {
    title: 'clip-01.mp4',
    titleSource: 'filename'
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node --test tests/player.test.js`

Expected: FAIL because `deriveTitleFromUrl` does not exist yet.

- [ ] **Step 3: Implement the minimal title extraction**

```js
// src/player/detect-source.js
function getYouTubeId(url) {
  const parsed = new URL(url);
  if (parsed.hostname.includes('youtu.be')) {
    return parsed.pathname.slice(1) || null;
  }
  if (parsed.hostname.includes('youtube.com')) {
    const pathMatch = parsed.pathname.match(/^\/(?:shorts|embed)\/([^/]+)/);
    if (pathMatch) return pathMatch[1];
    return parsed.searchParams.get('v');
  }
  return null;
}

export function detectSource(url) {
  const youtubeId = getYouTubeId(url);
  if (youtubeId) return { sourceType: 'youtube', embedId: youtubeId };
  if (/\.(mp4|webm|ogg)(\?|#|$)/i.test(url)) return { sourceType: 'html5-video', embedId: null };
  return { sourceType: 'unsupported', embedId: null };
}

export function deriveTitleFromUrl(url) {
  const parsed = new URL(url);
  const lastSegment = parsed.pathname.split('/').filter(Boolean).at(-1);
  return {
    title: lastSegment || parsed.hostname,
    titleSource: lastSegment ? 'filename' : 'url'
  };
}
```

```js
// src/player/youtube-adapter.js
export function createYouTubeAdapter(iframeHost) {
  let player = null;

  async function waitForYouTubeApi() {
    if (window.YT?.Player) return window.YT;
    return new Promise((resolve) => {
      const previousReady = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        previousReady?.();
        resolve(window.YT);
      };
    });
  }

  return {
    async load(source) {
      await waitForYouTubeApi();
      const elementId = `youtube-player-${source.embedId}`;
      iframeHost.innerHTML = `<div id="${elementId}"></div>`;
      player = new window.YT.Player(elementId, { videoId: source.embedId });
    },
    play() { player?.playVideo(); },
    pause() { player?.pauseVideo(); },
    getCurrentTime() { return player?.getCurrentTime?.() ?? 0; },
    getDuration() { return player?.getDuration?.() ?? null; },
    isSeekable() { return true; },
    getCapabilities() { return { timing: true, duration: true }; },
    getTitle() { return player?.getVideoData?.().title || null; }
  };
}
```

```js
// src/player/create-player-controller.js
import { detectSource, deriveTitleFromUrl } from './detect-source.js';
// keep the rest of the file structure the same, but add:
getTitle(item) {
  return this.adapter?.getTitle?.() || deriveTitleFromUrl(item.sourceUrl).title;
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `node --test tests/player.test.js`

Expected: PASS with the updated title extraction tests green.

- [ ] **Step 5: Checkpoint player metadata**

Run: `npm test`

Expected: PASS and source detection remains stable.

### Task 4: Update session state and persistence for markers, clips, descriptions, and metadata

**Files:**
- Modify: `tests/session.test.js`
- Modify: `src/state/session.js`
- Modify: `src/main.js`

- [ ] **Step 1: Write the failing session tests**

```js
// tests/session.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createSessionState,
  appendImportedUrls,
  addMarkerForCurrentItem,
  describeLastClipForCurrentItem
} from '../src/state/session.js';

test('addMarkerForCurrentItem stores a persistent raw marker', () => {
  const state = createSessionState();
  appendImportedUrls(state, [{
    index: '001',
    sourceUrl: 'https://example.com/a.mp4',
    sourceType: 'html5-video',
    folderName: '001',
    createdAt: '2026-04-11T12:00:00.000Z',
    markers: [],
    clips: []
  }]);

  addMarkerForCurrentItem(state, {
    id: 'm1',
    timestampSeconds: 1.25,
    createdAt: '2026-04-11T12:01:00.000Z',
    kind: 'marker'
  });

  assert.equal(state.items[0].markers.length, 1);
  assert.equal(state.items[0].markers[0].kind, 'marker');
});

test('describeLastClipForCurrentItem updates the latest completed clip', () => {
  const state = createSessionState();
  appendImportedUrls(state, [{
    index: '001',
    sourceUrl: 'https://example.com/a.mp4',
    sourceType: 'html5-video',
    folderName: '001',
    createdAt: '2026-04-11T12:00:00.000Z',
    markers: [],
    clips: [{
      id: 'c1',
      startMarkerId: 'm1',
      endMarkerId: 'm2',
      startTimestampSeconds: 1,
      endTimestampSeconds: 2,
      description: '',
      createdAt: 'b'
    }]
  }]);

  describeLastClipForCurrentItem(state, 'opening reaction');

  assert.equal(state.items[0].clips[0].description, 'opening reaction');
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node --test tests/session.test.js`

Expected: FAIL because the new marker and clip state helpers do not exist yet.

- [ ] **Step 3: Implement the session and persistence changes**

```js
// src/state/session.js
import { createMarker, applyMarkerAction, applyClipDescription } from '../lib/labels.js';

export function createSessionState() {
  return {
    outputDirectoryHandle: null,
    items: [],
    currentIndex: null,
    importErrors: [],
    importSummary: null,
    lastSaveError: null,
    nextMarkerNumber: 1,
    nextClipNumber: 1
  };
}

export function getCurrentItem(state) {
  return state.items.find((item) => item.index === state.currentIndex) ?? null;
}

export function appendImportedUrls(state, items) {
  state.items.push(...items.map((item) => ({
    ...item,
    markers: item.markers ?? [],
    clips: item.clips ?? [],
    title: item.title ?? '',
    titleSource: item.titleSource ?? 'unknown'
  })));
  if (!state.currentIndex && state.items.length > 0) {
    state.currentIndex = state.items[0].index;
  }
}

export function addMarkerForCurrentItem(state, payload) {
  const item = getCurrentItem(state);
  if (!item) return;
  const result = applyMarkerAction(
    { markers: item.markers, clips: item.clips },
    {
      marker: createMarker(payload),
      clipId: `c${state.nextClipNumber++}`
    }
  );
  item.markers = result.markers;
  item.clips = result.clips;
}

export function eraseLastForCurrentItem(state) {
  const item = getCurrentItem(state);
  if (!item) return;
  const result = applyMarkerAction(
    { markers: item.markers, clips: item.clips },
    { eraseLast: true }
  );
  item.markers = result.markers;
  item.clips = result.clips;
}

export function describeLastClipForCurrentItem(state, description) {
  const item = getCurrentItem(state);
  if (!item) return;
  item.clips = applyClipDescription(item.clips, description);
}
```

```js
// src/main.js
// keep the current structure, but update it so:
// - the top-level button text becomes 【label】
// - imported items initialize with markers: [] and clips: []
// - persistState writes labels as { videoIndex, sourceUrl, markers, clips }
// - buildMeta includes title, titleSource, clipCount, hasOpenStartMarker
// - click handlers call addMarkerForCurrentItem for marker/start/end kinds
// - the description input applies to the last completed clip instead of writing a generic label
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `node --test tests/session.test.js`

Expected: PASS with marker and clip state transitions green.

- [ ] **Step 5: Checkpoint the session model**

Run: `npm test`

Expected: PASS across the full suite.

### Task 5: Redesign the UI to Editorial Slate and wire the smoother annotation flow

**Files:**
- Modify: `index.html`
- Modify: `src/ui/dom.js`
- Modify: `src/ui/render.js`
- Modify: `styles.css`
- Modify: `README.md`

- [ ] **Step 1: Write the failing UI-focused assertions in the session tests**

```js
// tests/session.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import { createSessionState, appendImportedUrls } from '../src/state/session.js';

test('imported items initialize with marker and clip collections', () => {
  const state = createSessionState();
  appendImportedUrls(state, [{
    index: '001',
    sourceUrl: 'https://example.com/a.mp4',
    sourceType: 'html5-video',
    folderName: '001',
    createdAt: '2026-04-11T12:00:00.000Z',
    markers: [],
    clips: []
  }]);

  assert.deepEqual(state.items[0].markers, []);
  assert.deepEqual(state.items[0].clips, []);
});
```

- [ ] **Step 2: Run the tests to verify they fail or expose missing wiring**

Run: `node --test tests/session.test.js`

Expected: FAIL or expose stale UI wiring assumptions if the state shape is not fully updated yet.

- [ ] **Step 3: Implement the new UI shell and renderer details**

```html
<!-- index.html -->
<!-- Keep the existing shell but update the player controls to include: -->
<div class="label-toolbar">
  <button id="capture-marker-button">【label】</button>
  <button data-marker-kind="start">start</button>
  <button data-marker-kind="end">end</button>
  <button data-marker-kind="erase">erase</button>
</div>
<div class="clip-description-row">
  <input id="clip-description-input" placeholder="Describe the latest completed clip">
  <button id="apply-description-button">Apply Description</button>
</div>
<section class="history-panel">
  <h2>Markers</h2>
  <ul id="markers-list"></ul>
  <h2>Clips</h2>
  <ul id="clips-list"></ul>
</section>
```

```js
// src/ui/dom.js
// extend the DOM map with:
captureMarkerButton,
clipDescriptionInput,
applyDescriptionButton,
markersList,
clipsList
```

```js
// src/ui/render.js
// add:
export function renderMarkerHistory(dom, item) {
  dom.markersList.innerHTML = (item?.markers ?? []).map((marker) => `
    <li>${marker.kind} @ ${marker.timestampSeconds.toFixed(2)}s</li>
  `).join('') || '<li>No markers yet.</li>';
}

export function renderClipHistory(dom, item) {
  dom.clipsList.innerHTML = (item?.clips ?? []).map((clip) => `
    <li>${clip.startTimestampSeconds.toFixed(2)}s → ${clip.endTimestampSeconds.toFixed(2)}s ${clip.description ? `· ${clip.description}` : ''}</li>
  `).join('') || '<li>No clips yet.</li>';
}
```

```css
/* styles.css */
/* Replace the current look with an editorial slate direction:
   - cooler paper background
   - stronger contrast
   - display font for h1/h2
   - sans-serif UI text
   - clear primary styling for #capture-marker-button
   - cleaner card and toolbar spacing
*/
```

```md
<!-- README.md -->
Update the usage notes so they explain:
- `【label】` saves a marker immediately
- `start` and `end` build structured clips
- description text applies to the latest completed clip
- `erase` removes the most recently saved marker
```

- [ ] **Step 4: Run the tests to verify the updated state assumptions pass**

Run: `npm test`

Expected: PASS with the updated marker/clip tests and no regressions.

- [ ] **Step 5: Run the manual redesign verification**

Run: `npm run start`

Expected: `Serving HTTP on ... port 4173`, then verify in Chrome or Edge that:

- the main control reads `【label】`
- clicking `【label】` immediately adds a marker entry
- `start` then `end` creates a clip entry
- applying description text updates the newest clip
- `erase` removes the latest marker and dependent clip when relevant
- `meta.json` includes `title`
- the new visual theme and typography match the approved Editorial Slate direction on desktop and mobile
