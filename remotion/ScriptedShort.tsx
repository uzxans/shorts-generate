import React from 'react';
import {AbsoluteFill, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Audio} from '@remotion/media';
import type {RemotionProps} from './types';
import {TitleScene} from './scenes/TitleScene';
import {CodeScene} from './scenes/CodeScene';
import {LayersScene} from './scenes/LayersScene';
import {GradientScene} from './scenes/GradientScene';
import {TakeawayScene} from './scenes/TakeawayScene';
import {GenericScene} from './scenes/GenericScene';
import {CaptionTrack} from './CaptionTrack';

export const renderScene = (scene: RemotionProps['board']['script_timeline'][number]) => {
  if (scene.scene_type === 'code') return <CodeScene scene={scene}/>;
  if (scene.scene_type === 'bento') return <LayersScene scene={scene}/>;
  if (scene.scene_type === 'gradient') return <GradientScene scene={scene}/>;
  if (scene.scene_type === 'takeaway') return <TakeawayScene scene={scene}/>;
  if (scene.scene_type === 'title') return <TitleScene scene={scene}/>;
  return <GenericScene scene={scene}/>;
};

export const ScriptedShort: React.FC<RemotionProps> = ({board, narrationSrc, soundtrackSrc, includeAudio = true}) => {
  const {fps} = useVideoConfig();
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{backgroundColor: '#07101d'}}>
      {board.script_timeline.map((scene) => <Sequence key={`${scene.start}-${scene.end}`} from={Math.round(scene.start * fps)} durationInFrames={Math.max(1, Math.round((scene.end - scene.start) * fps))}>
        {renderScene(scene)}
      </Sequence>)}
      {includeAudio && narrationSrc && <Audio src={narrationSrc.startsWith('/') ? narrationSrc : staticFile(narrationSrc)} volume={1}/>} 
      {includeAudio && soundtrackSrc && <Audio src={soundtrackSrc.startsWith('/') ? soundtrackSrc : staticFile(soundtrackSrc)} volume={0.13}/>} 
      {board.captions && <CaptionTrack cues={board.captions}/>} 
      {frame >= Math.round(board.outro_start * fps) && <AbsoluteFill style={{backgroundColor: '#07101d', justifyContent: 'center', alignItems: 'center', color: '#c5f86b', fontSize: 44}}>Сохрани идею и попробуй сам</AbsoluteFill>}
    </AbsoluteFill>
  );
};
