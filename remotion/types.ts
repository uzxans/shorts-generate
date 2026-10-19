export type CaptionCue = {
  start: number;
  end: number;
  words: Array<{text: string; start: number; end: number}>;
};

export type ScriptedScene = {
  start: number;
  end: number;
  scene_type: string;
  screen_text: string;
  voiceover: string;
  label?: string;
  note?: string;
  code?: string;
  filename?: string;
  highlights?: number[];
  points?: string[];
  animation?: Record<string, string | number>;
};

export type ScriptedBoard = {
  id: number;
  title: string;
  language?: string;
  script_timeline: ScriptedScene[];
  captions?: CaptionCue[];
  outro_start: number;
  duration: number;
  public_dir?: string;
};

export type RemotionProps = {
  board: ScriptedBoard;
  publicDir?: string;
  narrationSrc?: string;
  soundtrackSrc?: string;
  includeAudio?: boolean;
};
