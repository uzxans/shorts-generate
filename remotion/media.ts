import type {Caption} from '@remotion/captions';
import type {CaptionCue} from './types';

export const toRemotionCaptions = (cues: CaptionCue[]): Caption[] => cues.flatMap((cue) => cue.words.map((word) => ({
  text: word.text,
  startMs: Math.round(word.start * 1000),
  endMs: Math.round(word.end * 1000),
  timestampMs: Math.round(word.start * 1000),
  confidence: 1,
})));
