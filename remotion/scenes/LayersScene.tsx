import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {SceneShell} from './SceneShell';
import {colors} from '../styles';
import type {ScriptedScene} from '../types';

export const LayersScene: React.FC<{scene: ScriptedScene}> = ({scene}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const labels = (scene.voiceover.match(/сброс|база|компоненты|утилиты/gi) || ['reset', 'base', 'components', 'utilities']);
  return <SceneShell scene={scene}><div style={{position: 'relative', height: 430}}>{labels.map((label, i) => <div key={label} style={{position: 'absolute', left: i * 36, right: (labels.length - i - 1) * 36, top: i * 62, height: 130, borderRadius: 24, padding: 28, background: i === labels.length - 1 ? colors.lime : colors.panelBright, color: i === labels.length - 1 ? colors.ink : colors.text, fontSize: 34, fontWeight: 800, transform: `translateY(${interpolate(frame, [0, fps], [50, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}px)`, opacity: interpolate(frame, [i * 5, fps + i * 5], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>{label}</div>)}</div></SceneShell>;
};
