import { detectSource, deriveTitleFromUrl } from './detect-source.js';
import { createHtml5VideoAdapter } from './html5-video-adapter.js';
import { createYouTubeAdapter } from './youtube-adapter.js';
import { createUnsupportedAdapter } from './unsupported-adapter.js';

export function createPlayerController(elements) {
  function setVisible({ showVideo, showYouTube }) {
    elements.video.hidden = !showVideo;
    elements.youtubeHost.hidden = !showYouTube;
    if (!showVideo) {
      elements.video.pause();
      elements.video.removeAttribute('src');
      elements.video.load();
    }
    if (!showYouTube) {
      elements.youtubeHost.innerHTML = '';
    }
  }

  return {
    adapter: null,

    async load(item) {
      const detected = detectSource(item.sourceUrl);
      if (detected.sourceType === 'youtube') {
        setVisible({ showVideo: false, showYouTube: true });
        this.adapter = createYouTubeAdapter(elements.youtubeHost);
      } else if (detected.sourceType === 'html5-video') {
        setVisible({ showVideo: true, showYouTube: false });
        this.adapter = createHtml5VideoAdapter(elements.video);
      } else {
        setVisible({ showVideo: false, showYouTube: false });
        this.adapter = createUnsupportedAdapter();
      }

      await this.adapter.load({ ...item, ...detected });
      return detected;
    },

    getCurrentTime() {
      return this.adapter?.getCurrentTime?.() ?? null;
    },

    getCapabilities() {
      return this.adapter?.getCapabilities?.() ?? { timing: false, duration: false };
    },

    getDuration() {
      return this.adapter?.getDuration?.() ?? null;
    },

    isSeekable() {
      return this.adapter?.isSeekable?.() ?? false;
    },

    getTitle(item) {
      return this.adapter?.getTitle?.() || deriveTitleFromUrl(item.sourceUrl).title;
    },

    getTitleInfo(item) {
      const adapterTitle = this.adapter?.getTitle?.();
      if (adapterTitle) {
        return {
          title: adapterTitle,
          titleSource: 'youtube'
        };
      }

      return deriveTitleFromUrl(item.sourceUrl);
    }
  };
}
