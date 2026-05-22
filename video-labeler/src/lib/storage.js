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
