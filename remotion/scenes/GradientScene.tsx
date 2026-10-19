import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {SceneShell} from './SceneShell';
import {colors} from '../styles';
import type {ScriptedScene} from '../types';

export const GradientScene: React.FC<{scene: ScriptedScene}> = ({scene}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const rotate = interpolate(frame, [0, 4 * fps], [0, 360], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <SceneShell scene={scene}><div style={{height: 390, display: 'flex', alignItems: 'center', justifyContent: 'center'}}><div style={{width: 330, height: 330, borderRadius: '50%', background: `conic-gradient(${colors.lime}, ${colors.cyan}, ${colors.orange}, ${colors.lime})`, rotate: `${rotate}deg`, boxShadow: '0 0 100px #64d8ff55'}}><div style={{margin: 30, width: 270, height: 270, borderRadius: '50%', background: colors.ink, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 32, fontWeight: 800, rotate: `${-rotate}deg`}}>PRIORITY</div></div></div></SceneShell>;
};
