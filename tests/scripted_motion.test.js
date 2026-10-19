const {test} = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {execFileSync} = require('node:child_process');
const puppeteer = require('puppeteer');

test('scripted scenes move, hand off and rewind deterministically', async () => {
  const log=execFileSync('venv/bin/python',['render.py','--topic','51','--skip-voice','--build-only'],{encoding:'utf8'});
  const project=log.match(/Сценарный проект: (.+)/)[1].trim();
  const browser=await puppeteer.launch({headless:true,executablePath:process.env.PUPPETEER_EXECUTABLE_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
  try{
    const page=await browser.newPage();
    await page.setViewport({width:1080,height:1920});
    await page.goto(pathToFileURL(path.join(project,'index.html')).href);
    await page.evaluate(()=>document.fonts.ready);
    const errors=[];page.on('pageerror',err=>errors.push(err.message));
    const pose=async (time,selector)=>page.evaluate((t,sel)=>{
      window.__timelines.main.totalTime(t,false);
      const el=document.querySelector(sel),s=getComputedStyle(el),r=el.getBoundingClientRect();
      return {transform:Array.from(new DOMMatrix(s.transform==='none'?undefined:s.transform).toFloat64Array()),opacity:Number(s.opacity),x:r.x,y:r.y,width:r.width,height:r.height};
    },time,selector);
    const flat=await pose(.6,'#scene-0 .hero-card');
    const tilted=await pose(2.8,'#scene-0 .hero-card');
    assert.notDeepEqual(flat.transform,tilted.transform,'hover demo must actually rotate');
    assert.deepEqual(await pose(.6,'#scene-0 .hero-card'),flat,'seek backwards must restore pose');
    const incoming=await pose(5.25,'#scene-1');
    const outgoing=await pose(5.25,'#scene-0');
    assert.ok(incoming.x>0&&incoming.x<1080,'incoming travels during transition');
    assert.ok(outgoing.x<0&&outgoing.x>-1080,'outgoing travels simultaneously');
    assert.equal((await pose(6,'#scene-1')).opacity,1);
    assert.equal((await pose(6,'#scene-0')).opacity,0);
    assert.deepEqual(await pose(5.25,'#scene-1'),incoming);
    const compiled=await page.evaluate(()=>JSON.parse(document.querySelector('#script-data').textContent));
    assert.equal(compiled.scenes[3].start,24,'authored code-scene timing must survive compilation');
    assert.equal((await pose(compiled.outro_start+.1,'.chrome')).opacity,0,'no main overlays on frog');
    assert.deepEqual(errors,[]);
  }finally{await browser.close();}
});
