export function getDom() {
  return {
    chooseFolderButton: document.querySelector('#choose-folder-button'),
    folderStatus: document.querySelector('#folder-status'),
    saveStatus: document.querySelector('#save-status'),
    queueList: document.querySelector('#queue-list'),
    playerStatus: document.querySelector('#player-status'),
    video: document.querySelector('#video-element'),
    previousButton: document.querySelector('#previous-button'),
    nextButton: document.querySelector('#next-button'),
    startClipButton: document.querySelector('#start-clip-button'),
    endClipButton: document.querySelector('#end-clip-button'),
    clearTagButton: document.querySelector('#clear-tag-button'),
    undoButton: document.querySelector('#undo-button'),
    tagActions: document.querySelector('#tag-actions'),
    tagButtons: [],
    noteKindSelect: document.querySelector('#note-kind-select'),
    noteTextInput: document.querySelector('#note-text-input'),
    addNoteButton: document.querySelector('#add-note-button'),
    eraseNoteButton: document.querySelector('#erase-note-button'),
    timeline: document.querySelector('#timeline'),
    eventsList: document.querySelector('#events-list'),
    notesList: document.querySelector('#notes-list')
  };
}
