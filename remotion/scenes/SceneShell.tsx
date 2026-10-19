import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {colors, font} from '../styles';
import type {ScriptedScene} from '../types';

export const SceneShell: React.FC<{scene: ScriptedScene; children: React.ReactNode}> = ({scene, children}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = interpolate(frame, [0, 0.7 * fps], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)});
  return <AbsoluteFill style={{fontFamily: font, backgroundColor: colors.ink, color: colors.text, padding: 80, opacity: enter}}>
    <div style={{fontSize: 26, letterSpacing: 5, color: colors.lime, fontWeight: 700}}>{scene.label || 'CODE / MOTION'}</div>
    <div style={{position: 'absolute', top: 145, left: 80, right: 80, fontSize: 72, lineHeight: 1.02, fontWeight: 800, whiteSpace: 'pre-line'}}>{scene.screen_text}</div>
    <div style={{position: 'absolute', top: 560, left: 80, right: 80}}>{children}</div>
    <div style={{position: 'absolute', bottom: 120, left: 80, right: 80, color: colors.muted, fontSize: 27, lineHeight: 1.25}}>{scene.note || scene.voiceover}</div>
  </AbsoluteFill>;
};
