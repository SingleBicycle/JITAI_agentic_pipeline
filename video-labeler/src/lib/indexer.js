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
