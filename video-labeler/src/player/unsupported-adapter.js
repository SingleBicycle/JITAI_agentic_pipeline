export function createUnsupportedAdapter() {
  return {
    async load() {},
    play() {},
    pause() {},
    getCurrentTime() {
      return null;
    },
    getDuration() {
      return null;
    },
    isSeekable() {
      return false;
    },
    getCapabilities() {
      return { timing: false, duration: false };
    }
  };
}
