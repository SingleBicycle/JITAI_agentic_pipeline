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
