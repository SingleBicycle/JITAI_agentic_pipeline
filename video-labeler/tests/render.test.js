import test from 'node:test';
import assert from 'node:assert/strict';
import { renderInteractionEpisodeHistory } from '../src/ui/render.js';

test('renderInteractionEpisodeHistory shows cue actor recipient response and latency', () => {
  const dom = { interactionEpisodesList: { innerHTML: '' } };

  renderInteractionEpisodeHistory(dom, {
    interactionEpisodes: [{
      id: 'ie1',
      cueEvent: {
        startSeconds: 13.2,
        endSeconds: 14.8,
        actor: 'P1',
        candidateRecipient: 'P2',
        cueType: 'speech_gesture'
      },
      recipientAccess: {
        recipient: 'P2',
        accessLabel: 'visible_and_audible'
      },
      responseEvent: {
        label: 'possible_response',
        startSeconds: 15.1,
        endSeconds: 17,
        responseType: 'object_action_response'
      },
      cueResponseLink: {
        label: 'linked',
        latencySeconds: 0.3
      },
      evidenceSpans: [[13.2, 14.8], [15.1, 17]],
      ambiguityLabel: 'low',
      description: 'Adult presents materials; child visually orients toward the table.'
    }]
  });

  assert.match(dom.interactionEpisodesList.innerHTML, /P1 -> P2/);
  assert.match(dom.interactionEpisodesList.innerHTML, /possible_response/);
  assert.match(dom.interactionEpisodesList.innerHTML, /0\.30s latency/);
  assert.match(dom.interactionEpisodesList.innerHTML, /13\.20-14\.80/);
  assert.match(dom.interactionEpisodesList.innerHTML, /Adult presents materials/);
});
