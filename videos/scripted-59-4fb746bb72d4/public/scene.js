/* One deterministic timeline: render and preview use the same poses. */
const data = JSON.parse(document.getElementById('script-data').textContent);
const tl = gsap.timeline({paused:true});
data.scenes.forEach((s,i) => {
  const root = `#scene-${i}`, q = x => `${root} ${x}`;
  const T=s.start, D=s.end-s.start, a=s.animation, preset=a.preset;
  if(i){
    const old=`#scene-${i-1}`, tr=data.scenes[i-1].transition_out, d=tr.duration;
    tl.set(root,{opacity:1},T);
    if(tr.type==='slide'){
      tl.to(old,{x:-1080,duration:d,ease:'power3.inOut'},T);
      tl.fromTo(root,{x:1080},{x:0,duration:d,ease:'power3.inOut',immediateRender:false},T);
    }else if(tr.type==='zoom'){
      tl.to(old,{scale:1.1,opacity:0,duration:d,ease:'power2.inOut'},T);
      tl.fromTo(root,{scale:.9,opacity:0},{scale:1,opacity:1,duration:d,immediateRender:false},T);
    }else if(tr.type==='crossfade'){
      tl.to(old,{opacity:0,duration:d},T);
      tl.fromTo(root,{opacity:0},{opacity:1,duration:d,immediateRender:false},T);
    }
    tl.set(old,{opacity:0},T+d);
  }
  tl.fromTo(q('h1'),{y:35,opacity:i===0?.35:0},{y:0,opacity:1,duration:.65,ease:'power3.out',immediateRender:false},T+.05);
  tl.fromTo(q('.eyebrow'),{x:-25,opacity:0},{x:0,opacity:1,duration:.5,immediateRender:false},T+.15);
  tl.fromTo(q('.note'),{y:15,opacity:0},{y:0,opacity:1,duration:.5,immediateRender:false},T+.6);
  const hasCard=['title','tilt_card','perspective'].includes(s.scene_type);
  if(hasCard){
    const c=q('.hero-card');
    tl.set(q('.demo-plane'),{perspective:a.perspective||1100},T);
    if(preset==='depth'){
      tl.set(q('.cursor'),{opacity:0},T);
      tl.set(q('.state-a'),{textContent:'perspective → ГЛУБИНА'},T);
      tl.fromTo(c,{rotationY:0},{rotationY:-32,duration:2,ease:'power2.inOut',immediateRender:false},T+1.2);
      tl.to(c,{z:95,rotationY:-22,duration:2,ease:'power2.inOut'},T+D*.5);
      tl.fromTo(q('.plane-grid'),{rotationY:0},{rotationY:-22,duration:2,immediateRender:false},T+1.2);
    }else if(preset==='axes'){
      tl.set(q('.cursor'),{opacity:0},T);
      tl.to(q('.axis-x'),{opacity:.8,duration:.4},T+.8);
      tl.set(q('.state-a'),{textContent:'rotateX → ВВЕРХ / ВНИЗ'},T);
      tl.to(c,{rotationX:a.rotate_x||22,duration:1.2,ease:'power2.inOut'},T+1);
      tl.to(c,{rotationX:0,duration:.7},T+D*.42);
      tl.to(q('.axis-x'),{opacity:0,duration:.3},T+D*.47);
      tl.to(q('.axis-y'),{opacity:.8,duration:.3},T+D*.5);
      tl.set(q('.state-a'),{textContent:'rotateY → ВЛЕВО / ВПРАВО'},T+D*.5);
      tl.to(c,{rotationY:a.rotate_y||-25,duration:1.2,ease:'power2.inOut'},T+D*.55);
      tl.to(c,{rotationY:0,duration:.8},T+D*.85);
    }else{
      const enter=T+Math.min(1,D*.15), leave=T+D*.7;
      tl.fromTo(q('.cursor'),{x:30,y:0},{x:-215,y:-240,duration:.8,ease:'power2.inOut',immediateRender:false},enter);
      tl.to(c,{rotationX:a.rotate_x??10,rotationY:a.rotate_y??-15,duration:.8,ease:'power2.out'},enter+.55);
      tl.set(q('.state-a'),{opacity:0},enter+.55);tl.set(q('.state-b'),{opacity:1},enter+.55);
      tl.to(q('.cursor'),{x:30,y:0,duration:.8,ease:'power2.inOut'},leave);
      tl.to(c,{rotationX:0,rotationY:0,duration:.8,ease:'power2.out'},leave+.2);
      tl.set(q('.state-b'),{opacity:0},leave+.2);tl.set(q('.state-c'),{opacity:1},leave+.2);
    }
  }
  if(s.scene_type==='code'){
    const lines=document.querySelectorAll(q('.code-line'));
    lines.forEach((line,j)=>{
      tl.fromTo(line,{opacity:0,x:22},{opacity:1,x:0,duration:.35,immediateRender:false},T+.5+j*Math.min(.24,(D*.3)/lines.length));
    });
    (s.highlights||[]).forEach((h,j)=>{
      const line=lines[h-1];if(!line)return;
      const t=T+D*(.36+j*.15);
      tl.to(line,{backgroundColor:'#25476b',duration:.3},t);
      tl.to(line,{backgroundColor:'#101b2b',duration:.4},Math.min(T+D-.6,t+1.5));
    });
  }
  if(s.scene_type==='gradient') tl.to(q('.gradient-ring'),{rotation:360*(a.cycles||2),duration:D-.8,ease:'none'},T+.4);
  if(s.scene_type==='bento'){
    tl.fromTo(q('.cursor'),{x:0,y:0},{x:-430,y:-270,duration:1,ease:'power2.inOut',immediateRender:false},T+.7);
    const dur=preset==='jump'?.03:1.1;
    tl.to(q('.active-tile'),{scaleX:2.06,scaleY:2.08,duration:dur,ease:'power3.inOut'},T+2);
    tl.to(q('.expanded-copy'),{opacity:1,duration:.4},T+3.2);
    tl.to(q('.active-tile'),{scaleX:1,scaleY:1,duration:dur,ease:'power3.inOut'},T+D*.77);
    tl.to(q('.expanded-copy'),{opacity:0,duration:.2},T+D*.75);
  }
  if(s.scene_type==='spotlight'){
    if(preset==='float'){
      tl.set(q('.cursor,.spot-glow'),{opacity:0},T);
      tl.to(q('.spot-card'),{y:-24,duration:D/3,yoyo:true,repeat:1,ease:'sine.inOut'},T+.5);
    }else{
      tl.fromTo(q('.cursor'),{x:-470,y:-290},{x:-50,y:-90,duration:D*.42,ease:'sine.inOut',immediateRender:false},T+.8);
      tl.fromTo(q('.spot-glow'),{x:50,y:20},{x:470,y:220,duration:D*.42,ease:'sine.inOut',immediateRender:false},T+.8);
      tl.to(q('.cursor'),{x:-340,y:-200,duration:D*.35,ease:'sine.inOut'},T+D*.53);
      tl.to(q('.spot-glow'),{x:180,y:110,duration:D*.35,ease:'sine.inOut'},T+D*.53);
    }
  }
  if(s.scene_type==='skeleton'){
    tl.fromTo(q('.skeleton-line'),{opacity:.4},{opacity:1,duration:.65,repeat:3,yoyo:true,immediateRender:false},T+.3);
    const t=T+D*.48,d=preset==='jump'?.01:1.2;
    tl.to(q('.placeholder'),{opacity:0,y:preset==='jump'?0:-12,duration:d},t);
    tl.fromTo(q('.loaded'),{opacity:0,y:12},{opacity:1,y:0,duration:d,immediateRender:false},t);
    tl.set(q('.state-a'),{opacity:0},t);tl.set(q('.state-b'),{opacity:1},t);
  }
  if(s.scene_type==='takeaway') tl.fromTo(q('.point'),{opacity:0,x:50},{opacity:1,x:0,duration:.6,stagger:.65,ease:'power3.out',immediateRender:false},T+.5);
});
data.captions.forEach((cue,i)=>{
  tl.set(`#caption-${i}`,{opacity:1},cue.start);
  tl.set(`#caption-${i}`,{opacity:0},cue.end);
  cue.words.forEach((w,j)=>{
    tl.set(`#cw-${i}-${j}`,{color:'#c5f86b'},w.start);
    tl.set(`#cw-${i}-${j}`,{color:'#f4f7fc'},w.end);
  });
});
tl.fromTo('.progress',{scaleX:0},{scaleX:1,duration:data.outro_start,ease:'none'},0);
tl.set('.scene,.chrome,.progress-track,.captions',{opacity:0},data.outro_start);
window.__timelines = window.__timelines || {};
window.__timelines['main']=tl;
