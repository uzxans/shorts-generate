import React from 'react';
import {SceneShell} from './SceneShell';
import type {ScriptedScene} from '../types';

export const GenericScene: React.FC<{scene: ScriptedScene}> = ({scene}) => <SceneShell scene={scene}><div style={{fontSize: 42, fontWeight: 700, lineHeight: 1.15, whiteSpace: 'pre-line'}}>{scene.voiceover}</div></SceneShell>;
