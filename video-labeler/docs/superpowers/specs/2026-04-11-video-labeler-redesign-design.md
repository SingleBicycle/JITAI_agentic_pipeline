# Video Labeler Redesign Design

**Date:** 2026-04-11

## Goal

Refine the existing static video labeler so timestamp capture feels immediate, segment clips are stored as structured start/end records with descriptions, video metadata includes a title when available, and the interface is visually upgraded to a cleaner editorial style.

## Product Changes

### Label Interaction

- Replace the top-level `Labels` button with `【label】`
- Clicking `【label】` immediately captures the current playback time and stores a persistent marker
- A marker remains stored even if the user does nothing else with it
- `erase` is the only action that removes stored timing data
- `start` marks the beginning of a clip candidate
- `end` closes the most recent open start marker into a structured clip
- Custom text is used as a clip description for completed start/end clips, not as a generic free-form timestamp tag

### Metadata

- `meta.json` should include `title` when the app can determine a human-readable title
- For YouTube, the title should come from the YouTube player or embed metadata when available
- For direct video URLs, the title may fall back to a filename-like value derived from the URL path
- Include `titleSource` so the origin of the title remains explicit

### Visual Design

- Replace the current warm beige prototype styling with a cleaner editorial “slate” look
- Use a more intentional typography system with a distinct display face and a readable sans-serif body/control face
- Increase hierarchy around the player and main labeling actions
- Make the `【label】` control feel primary and immediate
- Reduce the visual clutter of the current generic rounded controls

## Updated Data Model

### `labels.json`

The file becomes structured around raw markers and derived clips:

```json
{
  "videoIndex": "001",
  "sourceUrl": "https://example.com/video.mp4",
  "markers": [
    {
      "id": "m1",
      "timestampSeconds": 14.22,
      "createdAt": "2026-04-11T12:01:00.000Z",
      "kind": "marker"
    },
    {
      "id": "m2",
      "timestampSeconds": 18.08,
      "createdAt": "2026-04-11T12:01:05.000Z",
      "kind": "start"
    },
    {
      "id": "m3",
      "timestampSeconds": 24.44,
      "createdAt": "2026-04-11T12:01:12.000Z",
      "kind": "end"
    }
  ],
  "clips": [
    {
      "id": "c1",
      "startMarkerId": "m2",
      "endMarkerId": "m3",
      "startTimestampSeconds": 18.08,
      "endTimestampSeconds": 24.44,
      "description": "speaker turns toward camera",
      "createdAt": "2026-04-11T12:01:12.000Z"
    }
  ]
}
```

### `meta.json`

The metadata file expands to include title and clip summary information:

```json
{
  "index": "001",
  "folderName": "001",
  "sourceUrl": "https://example.com/video.mp4",
  "sourceType": "html5-video",
  "title": "video.mp4",
  "titleSource": "filename",
  "createdAt": "2026-04-11T12:00:00.000Z",
  "durationSeconds": 123.45,
  "seekable": true,
  "clipCount": 1,
  "hasOpenStartMarker": false,
  "capabilities": {
    "timing": true,
    "duration": true
  }
}
```

## Interaction Rules

- Clicking `【label】` stores a raw marker with `kind: "marker"`
- Clicking `start` stores a marker with `kind: "start"`
- Clicking `end` stores a marker with `kind: "end"` and, if an open start exists, creates a clip record from that start marker to the end marker
- The description field applies to the most recently completed clip
- If no completed clip is available, custom description submission should be blocked with clear UI feedback
- `erase` removes the most recently stored marker and any derived clip that depends on it
- Manual JSON edits remain possible because raw markers are preserved instead of flattened away

## Title Extraction Rules

- `youtube`: use the embedded player API title if available
- `html5-video`: derive a readable title from the URL path segment when possible
- `unsupported`: store `title` as a best-effort URL-derived fallback

If a strong title cannot be determined, the app should still store a stable fallback string rather than leaving the field ambiguous.

## Visual Direction

### Layout

- Keep the four-area structure: import, session/output, queue, and player/annotation
- Increase emphasis on the player and active annotation controls
- Make the marker and clip history easier to scan
- Separate raw markers from structured clips visually

### Typography

- Use an expressive display face for page title and key headings
- Use a neutral sans-serif for controls, status, queue items, and data views
- Avoid the current generic serif-heavy presentation

### Color

- Move to a cooler editorial palette with paper-like surfaces and darker ink contrast
- Reserve the strongest accent color for active labeling and clip actions
- Make destructive actions like `erase` visually distinct but not overpowering

## Testing Updates

Add or update tests for:

- immediate marker creation from `【label】`
- `start` and `end` marker pairing into clips
- `erase` removing dependent clip records when necessary
- title extraction for standard YouTube and Shorts URLs
- title fallback extraction for direct video URLs

Manual verification should include:

- clicking `【label】` without any follow-up label and confirming the marker persists in `labels.json`
- creating a `start`/`end` clip and applying a description
- confirming `meta.json` includes `title`
- checking the redesigned UI in both desktop and mobile layouts

## Scope

This redesign is a behavior and presentation refinement of the current app, not a platform rewrite. The implementation should reuse the current static architecture and evolve the existing modules instead of replacing the app with a framework or backend.
