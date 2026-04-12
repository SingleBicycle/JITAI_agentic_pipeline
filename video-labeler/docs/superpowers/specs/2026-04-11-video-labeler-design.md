# Video Labeler Design

**Date:** 2026-04-11

## Goal

Build a simple single-page static web app that lets a user import public video links, review one video at a time, capture timestamped labels while watching, and persist session output directly to a chosen local folder without a backend.

## Constraints

- No backend service
- No framework or build step for v1
- Must work as a plain HTML/CSS/JS app
- Direct local file writes may rely on the File System Access API, so Chrome or Edge is the supported browser target
- Should support YouTube public links and arbitrary public video URLs where browser playback is possible

## Product Scope

### In Scope

- Paste one or many links into a text area and auto-parse them into a queue
- Upload `.txt` or `.csv` files containing links and auto-parse them into a queue
- Assign stable zero-padded indexes like `001`, `002`, `003` within the active session
- Append new links to the current session queue and `index.csv` instead of rebuilding from scratch
- Let the user choose a local output folder at the start of the session
- Create one subfolder per indexed video
- Write `meta.json` and `labels.json` for each indexed video
- Provide default labels `start`, `end`, and `erase`
- Provide a custom text label input in the UI
- Show one video at a time with queue navigation
- Capture the active playback timestamp when a label is applied
- Remove the most recent label entry for the current video when `erase` is used
- Record useful metadata such as source URL, source type, created date, and duration when available

### Out of Scope for v1

- Authentication
- Multi-user sessions
- Cloud sync
- Server-side downloads or transcoding
- Guaranteed playback support for every video host on the web
- Advanced label taxonomy management beyond defaults plus one-off custom labels

## User Experience

The page is organized into four working areas:

1. Import area for pasted links or uploaded `.txt`/`.csv` files
2. Session/output area for choosing a writable folder and showing save status
3. Queue area showing indexed videos and current selection
4. Player and labeling area for reviewing one video at a time

The user starts by choosing an output folder, then pastes links or uploads a file. The app parses valid URLs, removes exact duplicates already seen in the session, assigns the next indexes, and updates the queue and `index.csv`. The user selects or advances through videos one at a time, watches or scrubs the video, expands the label menu, and clicks a label to record the current timestamp. Each label write updates the current video's `labels.json` immediately.

## Architecture

The app is a single static page with small focused browser-side modules:

- `app`: bootstraps the page, holds session state, and coordinates updates
- `parser`: extracts URLs from pasted text and uploaded files
- `indexer`: assigns sequential zero-padded indexes and handles dedupe rules
- `player`: chooses the correct player adapter for a source
- `labels`: applies label events, handles custom labels, and performs erase
- `storage`: reads and writes `index.csv`, `meta.json`, and `labels.json` via the File System Access API
- `serializer`: converts in-memory state to CSV and JSON payloads

This keeps the no-framework codebase maintainable while avoiding a monolithic script.

## Source Handling

The player layer uses source adapters:

- `youtube` adapter for standard YouTube URLs embedded with the YouTube player
- `html5-video` adapter for direct browser-playable media URLs such as `.mp4`
- `unsupported` adapter for links that cannot be reliably embedded or timed in-browser

Each adapter exposes the same small interface:

- `load(source)`
- `play()`
- `pause()`
- `getCurrentTime()`
- `getDuration()`
- `isSeekable()`
- `getCapabilities()`

If a source cannot provide reliable timing, the app does not fake support. The item stays in the queue, the UI explains the limitation, and `meta.json` records the capability state.

## Data Model

### Session Queue Item

Each queued video is represented in memory as:

```json
{
  "index": "001",
  "sourceUrl": "https://example.com/video.mp4",
  "sourceType": "html5-video",
  "status": "ready",
  "folderName": "001"
}
```

### `index.csv`

The session-level CSV lives in the chosen output folder and contains one row per indexed video. Initial columns:

- `index`
- `source_url`
- `source_type`
- `folder_name`
- `created_at`

New links append rows during the same active session.

### `meta.json`

Stored inside each video folder. Initial shape:

```json
{
  "index": "001",
  "folderName": "001",
  "sourceUrl": "https://example.com/video.mp4",
  "sourceType": "html5-video",
  "createdAt": "2026-04-11T12:00:00.000Z",
  "durationSeconds": 123.45,
  "seekable": true,
  "labelOptions": ["start", "end"],
  "customLabelsUsed": [],
  "capabilities": {
    "timing": true,
    "duration": true
  }
}
```

`labelOptions` lists the currently active non-destructive labels. `erase` is treated as an action, not a stored label.

### `labels.json`

Stored inside each video folder. Initial shape:

```json
{
  "videoIndex": "001",
  "sourceUrl": "https://example.com/video.mp4",
  "labels": [
    {
      "timestampSeconds": 12.34,
      "label": "start",
      "createdAt": "2026-04-11T12:01:00.000Z"
    }
  ]
}
```

Using `erase` removes the most recent item from the `labels` array for the current video and rewrites the file.

## Label Configuration

The app ships with a separate label configuration file at `config/labels.json`, containing the defaults:

```json
{
  "defaults": ["start", "end", "erase"]
}
```

At runtime the UI renders the default actions from this file. The user may also enter a one-off custom label in a text input; that label is applied to the current click only and is also tracked in `meta.json` under `customLabelsUsed` if it has not already been used for that video.

## Storage Layout

For an output folder chosen by the user:

```text
output-folder/
  index.csv
  001/
    meta.json
    labels.json
  002/
    meta.json
    labels.json
```

When the user imports more links later in the same open session, the app appends additional rows to `index.csv` and creates the next numbered folders.

## Import Rules

- Parse URLs from newline-separated text, comma-separated values, or mixed pasted content
- Ignore blank entries
- Ignore malformed URLs and report them in a small import summary
- Deduplicate exact URL repeats within the current session
- Keep indexing monotonic within the current session; imported duplicates do not consume new indexes

## Interaction Rules

- The page loads one video at a time
- Queue items can be selected directly
- Previous and next controls move through the queue
- The label launcher expands into buttons for `start`, `end`, `erase`, and an input-driven custom label action
- Clicking a label records the current playback time from the active player adapter
- Clicking `erase` removes the latest stored label for the current video
- Label writes happen immediately after each action when folder access is available

## Error Handling

- If no writable folder is selected, the app can still parse inputs and build the queue, but saving actions remain blocked behind a clear prompt
- If a file upload contains malformed rows, valid URLs still import and skipped rows are reported
- If a source cannot be embedded or timed, the app shows the limitation and avoids creating misleading timestamps
- If a write fails, the UI shows a non-blocking error and keeps in-memory session state so the user can retry

## Testing Strategy

v1 testing should stay lightweight but cover the highest-risk logic:

- Unit tests for URL parsing from pasted text and uploaded file content
- Unit tests for dedupe and sequential indexing behavior
- Unit tests for label add and erase behavior
- Unit tests for CSV and JSON serialization
- Manual smoke checks for:
  - choosing an output folder
  - importing pasted links
  - importing `.txt` and `.csv`
  - labeling a direct video URL
  - labeling a YouTube URL
  - appending more links in the same session
  - verifying folder/file output structure

## Open Decisions Resolved

- Runtime: plain static HTML/CSS/JS
- Persistence: browser writes directly to a user-selected local folder
- Browser target: Chrome or Edge
- Source scope: YouTube plus arbitrary public video URLs where browser playback is supported
- App shape: single-page experience rather than a multi-step wizard

## Implementation Notes

The project currently has no scaffold, so implementation will also need to create the basic app structure, local test setup, and a minimal way to serve the static files during development. The code should remain dependency-light and organized by responsibility so it can grow later without a rewrite.
