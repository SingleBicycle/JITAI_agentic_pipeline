export function createHtml5VideoAdapter(videoElement) {
  return {
    async load(source) {
      videoElement.src = source.sourceUrl;
      videoElement.load();
    },
    play() {
      return videoElement.play();
    },
    pause() {
      videoElement.pause();
    },
    getCurrentTime() {
      return videoElement.currentTime || 0;
    },
    getDuration() {
      return Number.isFinite(videoElement.duration) ? videoElement.duration : null;
    },
    isSeekable() {
      return (videoElement.seekable?.length ?? 0) > 0;
    },
    getCapabilities() {
      return {
        timing: true,
        duration: Number.isFinite(videoElement.duration)
      };
    }
  };
}
