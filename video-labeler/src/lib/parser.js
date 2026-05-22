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
