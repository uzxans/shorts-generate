// Usage:
//   node render_demo.js <html_b64> <out_path> <w> <h> [--video --duration 3 --interactive hover]
//
// Modes:
//   default                 → single PNG screenshot
//   --video --duration N    → MP4 of the page over N seconds (30fps)
//   --interactive hover     → during the recording, drive a visible cursor
//                              onto the most-prominent interactive element
//                              and back out, so :hover styles fire
//
// Targets system Chrome (no Chromium download).

const puppeteer = require('puppeteer');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');

const DEFAULT_FPS = 30;
const DEFAULT_CRF = 16;
const DEFAULT_PRESET = 'medium';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

function parseArgs(argv) {
  const args = { positional: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--video') args.video = true;
    else if (a === '--duration') args.duration = parseFloat(argv[++i]);
    else if (a === '--fps') args.fps = parseInt(argv[++i], 10);
    else if (a === '--crf') args.crf = parseInt(argv[++i], 10);
    else if (a === '--preset') args.preset = argv[++i];
    else if (a === '--interactive') args.interactive = argv[++i];
    else args.positional.push(a);
  }
  args.html_b64 = args.positional[0];
  args.out = args.positional[1];
  args.width = parseInt(args.positional[2] || '1080', 10);
  args.height = parseInt(args.positional[3] || '760', 10);
  args.duration = args.duration || 3.0;
  args.fps = args.fps || DEFAULT_FPS;
  args.crf = args.crf || DEFAULT_CRF;
  args.preset = args.preset || DEFAULT_PRESET;
  return args;
}

const CURSOR_SVG_DATA_URI =
  "data:image/svg+xml;utf8," + encodeURIComponent(
    `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='40' height='40'>
       <path d='M3 2 L3 18 L8 14 L11 21 L14 19 L11 13 L18 13 Z'
             fill='white' stroke='black' stroke-width='1.2'
             stroke-linejoin='round'/>
     </svg>`
  );

async function injectCursor(page) {
  await page.evaluate((dataUri) => {
    const c = document.createElement('div');
    c.id = '__cursor__';
    Object.assign(c.style, {
      position: 'fixed',
      top: '0', left: '0',
      width: '40px', height: '40px',
      pointerEvents: 'none',
      zIndex: '2147483647',
      transform: 'translate(-50%, -50%)',
      backgroundImage: `url("${dataUri}")`,
      backgroundRepeat: 'no-repeat',
      backgroundSize: 'contain',
      transition: 'none',
      opacity: '0',
    });
    document.body.appendChild(c);
  }, CURSOR_SVG_DATA_URI);
}

async function findHoverTarget(page) {
  return await page.evaluate(() => {
    const candidates = [
      ...document.querySelectorAll('button, a, .btn, [class*="btn"], input[type="button"], input[type="submit"]'),
    ];
    let best = null, bestArea = 0;
    for (const el of candidates) {
      const r = el.getBoundingClientRect();
      const area = r.width * r.height;
      if (area > bestArea) { best = el; bestArea = area; }
    }
    if (!best) return null;
    const r = best.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  });
}

function easeInOut(t) {
  return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
}

function cursorTrajectory(t, duration, target, viewport) {
  // Phases (proportions of clip duration):
  //   0.00..0.10  off-screen
  //   0.10..0.25  approach (cursor enters from bottom-right toward target)
  //   0.25..0.85  HOVER HELD on target — :hover stays active for ~60% of clip
  //   0.85..0.95  leave (cursor moves back off)
  //   0.95..1.00  hidden
  const p = t / duration;
  const start = { x: viewport.width * 0.88, y: viewport.height * 0.96 };
  if (p < 0.10) return { x: -200, y: -200, opacity: 0 };
  if (p < 0.25) {
    const a = easeInOut((p - 0.10) / 0.15);
    return {
      x: start.x + (target.x - start.x) * a,
      y: start.y + (target.y - start.y) * a,
      opacity: 1,
    };
  }
  if (p < 0.85) {
    return { x: target.x, y: target.y, opacity: 1 };
  }
  if (p < 0.95) {
    const a = easeInOut((p - 0.85) / 0.10);
    return {
      x: target.x + (start.x - target.x) * a,
      y: target.y + (start.y - target.y) * a,
      opacity: 1,
    };
  }
  return { x: -200, y: -200, opacity: 0 };
}

async function captureFrame(page, framePath) {
  await page.screenshot({ path: framePath, omitBackground: false });
}

function buildFfmpegArgs(frameDir, outPath, args) {
  return [
    '-y',
    '-loglevel', 'error',
    '-framerate', String(args.fps),
    '-i', path.join(frameDir, '%04d.png'),
    '-c:v', 'libx264',
    '-preset', args.preset,
    '-crf', String(args.crf),
    '-pix_fmt', 'yuv420p',
    '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
    '-movflags', '+faststart',
    outPath,
  ];
}

async function recordVideo(page, outPath, width, height, duration, interactive, args) {
  const total = Math.max(2, Math.floor(duration * args.fps));
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'demo-frames-'));

  let target = null;
  if (interactive === 'hover') {
    await injectCursor(page);
    target = await findHoverTarget(page);
    if (!target) {
      console.warn('   (no hover target found, recording passive)');
      interactive = null;
    }
  }

  for (let i = 0; i < total; i++) {
    const t = i / args.fps;
    if (interactive === 'hover' && target) {
      const c = cursorTrajectory(t, duration, target, { width, height });
      // Drive real mouse so :hover fires
      await page.mouse.move(c.x, c.y);
      await page.evaluate((cx, cy, op) => {
        const el = document.getElementById('__cursor__');
        if (el) {
          el.style.left = cx + 'px';
          el.style.top = cy + 'px';
          el.style.opacity = String(op);
        }
      }, c.x, c.y, c.opacity);
    }
    const fp = path.join(tmp, String(i).padStart(4, '0') + '.png');
    await captureFrame(page, fp);
  }

  // Encode frames to mp4 with ffmpeg
  await new Promise((resolve, reject) => {
    const ff = spawn('ffmpeg', buildFfmpegArgs(tmp, outPath, args), { stdio: 'inherit' });
    ff.on('exit', (code) => code === 0 ? resolve() : reject(new Error('ffmpeg exit ' + code)));
  });

  fs.rmSync(tmp, { recursive: true, force: true });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const html = Buffer.from(args.html_b64, 'base64').toString('utf8');

  const browser = await puppeteer.launch({
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    executablePath: CHROME,
    headless: 'new',
  });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: args.width, height: args.height, deviceScaleFactor: 2 });
    await page.setContent(html, { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 400));

    if (args.video) {
      await recordVideo(page, args.out, args.width, args.height, args.duration, args.interactive, args);
    } else {
      await captureFrame(page, args.out);
    }
  } finally {
    await browser.close();
  }
}

if (require.main === module) {
  main().catch(err => { console.error(err); process.exit(1); });
}

module.exports = {
  buildFfmpegArgs,
  parseArgs,
};
