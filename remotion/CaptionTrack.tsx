import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {CaptionCue} from './types';

export const CaptionTrack: React.FC<{cues: CaptionCue[]}> = ({cues}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig(); const time = frame / fps;
  const cue = cues.find((candidate) => time >= candidate.start && time <= candidate.end);
  if (!cue) return null;
  return <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 260, pointerEvents: 'none'}}>
    <div style={{background: '#07101ddd', borderRadius: 18, padding: '16px 26px', maxWidth: 900, fontSize: 38, fontWeight: 800, textAlign: 'center'}}>
      {cue.words.map((word) => <span key={`${word.start}-${word.text}`} style={{color: time >= word.start && time <= word.end ? '#c5f86b' : '#f4f7fc'}}>{word.text} </span>)}
    </div>
  </AbsoluteFill>;
};
