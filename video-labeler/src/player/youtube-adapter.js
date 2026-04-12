function waitForYouTubeApi() {
  if (window.YT?.Player) {
    return Promise.resolve(window.YT);
  }

  return new Promise((resolve) => {
    const previousReady = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      previousReady?.();
      resolve(window.YT);
    };
  });
}

export function createYouTubeAdapter(iframeHost) {
  let player = null;

  return {
    async load(source) {
      await waitForYouTubeApi();
      iframeHost.innerHTML = '<div id="youtube-player"></div>';
      player = await new Promise((resolve) => {
        const elementId = `youtube-player-${source.embedId}`;
        iframeHost.innerHTML = `<div id="${elementId}"></div>`;
        resolve(new window.YT.Player(elementId, {
          videoId: source.embedId
        }));
      });
    },
    play() {
      player?.playVideo();
    },
    pause() {
      player?.pauseVideo();
    },
    getCurrentTime() {
      return player?.getCurrentTime?.() ?? 0;
    },
    getDuration() {
      return player?.getDuration?.() ?? null;
    },
    isSeekable() {
      return true;
    },
    getCapabilities() {
      return { timing: true, duration: true };
    },
    getTitle() {
      return player?.getVideoData?.().title || null;
    }
  };
}
