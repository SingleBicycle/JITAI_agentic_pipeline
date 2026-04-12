export function getDom() {
  return {
    linkInput: document.querySelector('#link-input'),
    fileInput: document.querySelector('#file-input'),
    importTextButton: document.querySelector('#import-text-button'),
    chooseFolderButton: document.querySelector('#choose-folder-button'),
    saveStatus: document.querySelector('#save-status'),
    importReport: document.querySelector('#import-report'),
    queueList: document.querySelector('#queue-list'),
    playerStatus: document.querySelector('#player-status'),
    video: document.querySelector('#video-element'),
    youtubeHost: document.querySelector('#youtube-host'),
    previousButton: document.querySelector('#previous-button'),
    nextButton: document.querySelector('#next-button'),
    captureMarkerButton: document.querySelector('#capture-marker-button'),
    markerActions: document.querySelector('#marker-actions'),
    clipDescriptionInput: document.querySelector('#clip-description-input'),
    applyDescriptionButton: document.querySelector('#apply-description-button'),
    markersList: document.querySelector('#markers-list'),
    clipsList: document.querySelector('#clips-list')
  };
}
