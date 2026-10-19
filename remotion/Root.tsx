import React from 'react';
import {Composition} from 'remotion';
import {ScriptedShort} from './ScriptedShort';
import type {RemotionProps} from './types';

const defaultProps: RemotionProps = {
  board: {
    id: 0,
    title: 'Scripted short',
    script_timeline: [],
    outro_start: 1,
    duration: 1,
  },
  includeAudio: false,
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="ScriptedShort"
    component={ScriptedShort}
    fps={30}
    width={1080}
    height={1920}
    durationInFrames={30}
    calculateMetadata={({props}) => ({durationInFrames: Math.max(1, Math.ceil(props.board.duration * 30))})}
    defaultProps={defaultProps}
  />
);
