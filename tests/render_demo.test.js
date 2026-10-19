const assert = require('assert');
const { buildFfmpegArgs, parseArgs } = require('../render_demo');

const parsed = parseArgs([
  'PGh0bWw+',
  'out.mp4',
  '1080',
  '760',
  '--video',
  '--duration',
  '3',
]);

assert.strictEqual(parsed.fps, 30);
assert.strictEqual(parsed.crf, 16);
assert.strictEqual(parsed.preset, 'medium');

const ffmpegArgs = buildFfmpegArgs('/tmp/frames', 'out.mp4', parsed);

assert.deepStrictEqual(
  ffmpegArgs.slice(0, 7),
  ['-y', '-loglevel', 'error', '-framerate', '30', '-i', '/tmp/frames/%04d.png'],
);
assert.ok(ffmpegArgs.includes('-crf'));
assert.ok(ffmpegArgs.includes('16'));
assert.ok(ffmpegArgs.includes('-preset'));
assert.ok(ffmpegArgs.includes('medium'));
assert.ok(ffmpegArgs.includes('-movflags'));
assert.ok(ffmpegArgs.includes('+faststart'));

console.log('render_demo tests ok');
