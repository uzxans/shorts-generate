import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {SceneShell} from './SceneShell';
import {colors} from '../styles';
import type {ScriptedScene} from '../types';

export const TakeawayScene: React.FC<{scene: ScriptedScene}> = ({scene}) => { const frame = useCurrentFrame(); const points = scene.points || []; return <SceneShell scene={scene}><div>{points.map((point, i) => <div key={point} style={{display: 'flex', alignItems: 'center', gap: 24, marginBottom: 24, fontSize: 34, fontWeight: 700, opacity: interpolate(frame, [i * 12, i * 12 + 18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}), translate: `${interpolate(frame, [i * 12, i * 12 + 18], [50, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}px 0`}}><span style={{color: colors.lime, fontFamily: 'monospace'}}>0{i + 1}</span>{point}</div>)}</div></SceneShell>; };
