# Video Labeler

## Run

1. `npm test`
2. `npm run start`
3. Open `http://localhost:4173`
4. Use Chrome or Edge so folder writes work

## Manual smoke checklist

- Choose an output folder
- Paste a direct `.mp4` URL and confirm `001/meta.json`, `001/labels.json`, and `index.csv` are written
- Click `mark` and confirm a marker is stored immediately in `labels.json`
- Click `start` then `end` and confirm a structured clip appears in `clips`
- Apply description text and confirm it updates the latest completed clip
- Click `erase` and confirm the newest marker, plus any dependent clip, is removed
- Paste a YouTube URL and confirm `meta.json` includes `title`
- Upload a mixed `.txt` or `.csv` file and confirm malformed rows are reported while valid rows still import
- Use previous and next to move through the queue, then confirm new imports append as `002`, `003`, and so on
