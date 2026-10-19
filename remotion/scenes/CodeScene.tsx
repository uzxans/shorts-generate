import React from 'react';
import {Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {SceneShell} from './SceneShell';
import {colors} from '../styles';
import type {ScriptedScene} from '../types';

export const CodeScene: React.FC<{scene: ScriptedScene}> = ({scene}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const lines = (scene.code || '').split('\n'); const highlights = new Set(scene.highlights || []);
  return <SceneShell scene={scene}><div style={{background: '#0b1422', border: `2px solid ${colors.panelBright}`, borderRadius: 24, padding: 26, boxShadow: '0 30px 90px #0009'}}>
    <div style={{color: colors.muted, fontSize: 23, marginBottom: 18}}>{scene.filename || 'styles.css'} <span style={{float: 'right'}}>● ● ●</span></div>
    {lines.map((line, i) => <div key={i} style={{display: 'flex', gap: 20, padding: '7px 10px', background: highlights.has(i + 1) ? '#25476b' : 'transparent', opacity: interpolate(frame, [0.4 * fps + i * 4, 0.8 * fps + i * 4], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)}), fontFamily: 'monospace', fontSize: 22, lineHeight: 1.2}}><span style={{color: colors.muted, width: 34, textAlign: 'right'}}>{String(i + 1).padStart(2, '0')}</span><span>{line || ' '}</span></div>)}
  </div></SceneShell>;
};
