import React from 'react';
import {Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {SceneShell} from './SceneShell';
import {colors} from '../styles';
import type {ScriptedScene} from '../types';

export const TitleScene: React.FC<{scene: ScriptedScene}> = ({scene}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const scale = interpolate(frame, [0, 1.5 * fps], [0.78, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)});
  return <SceneShell scene={scene}><div style={{display: 'flex', gap: 18, alignItems: 'flex-end', scale}}>
    {[0, 1, 2, 3].map((i) => <div key={i} style={{width: 140, height: 120 + i * 55, borderRadius: 22, background: `linear-gradient(145deg, ${i % 2 ? colors.cyan : colors.lime}, ${colors.panelBright})`, transform: `translateY(${Math.sin((frame + i * 8) / 12) * 12}px)`, boxShadow: '0 20px 60px #0008'}}><div style={{padding: 20, fontSize: 24, fontWeight: 800}}>L{i + 1}</div></div>)}
  </div></SceneShell>;
};
