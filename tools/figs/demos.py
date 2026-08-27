"""Interactive demos for the artifact.

Two kinds, and the difference is stated on the page rather than blurred:

  FRAME PLAYERS are real MuJoCo runs, rendered offscreen from the same XML the
  studies used. Moving the grip-force slider does not recompute anything -- it
  switches to a different pre-rendered run. What you see is what MuJoCo did.

  LIVE DEMOS re-implement a reduced version of the dynamics in JavaScript, so
  they respond continuously. They demonstrate a MECHANISM; they are not the
  measurement, and they say so.
"""
import json


def frames_json(seqs):
    return json.dumps(seqs, separators=(",", ":"))


PLAYER_JS = """
// ---- frame players: real MuJoCo runs, rendered offscreen ----------------
const SEQ = window.__SEQ__;
// dotted keys so a duo can point straight into a slider's set instead of
// shipping a second copy of the same frames
function seqAt(k){ return k.split('.').reduce(function(o,p){ return o && o[p]; }, SEQ); }
function makePlayer(img, get, fps){
  let i = 0, last = 0;
  function tick(t){
    const f = get();
    if (f && f.length){
      if (t - last > 1000/(fps||18)){ last = t; i = (i+1) % f.length; img.src = f[i]; }
    }
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
  return { reset(){ i = 0; } };
}

document.querySelectorAll('[data-seq]').forEach(function(img){
  const key = img.getAttribute('data-seq');
  makePlayer(img, function(){ return seqAt(key); }, +img.dataset.fps || 18);
});

// ---- slider-driven players ---------------------------------------------
document.querySelectorAll('[data-slider]').forEach(function(root){
  const key   = root.dataset.slider;
  const img   = root.querySelector('img');
  const range = root.querySelector('input[type=range]');
  const val   = root.querySelector('[data-val]');
  const verd  = root.querySelector('[data-verdict]');
  const keys  = JSON.parse(root.dataset.keys);
  const marks = JSON.parse(root.dataset.marks || '{}');
  const p = makePlayer(img, function(){ return SEQ[key][keys[range.value]]; },
                       +root.dataset.fps || 16);
  function upd(){
    const k = keys[range.value];
    val.textContent = (root.dataset.unit || '').replace('%s', k);
    if (verd){
      const ok = marks[k] === 1;
      verd.textContent = ok ? (root.dataset.ok || 'HOLDS')
                            : (root.dataset.bad || 'FAILS');
      verd.className = 'verdict ' + (ok ? 'v-ok' : 'v-bad');
    }
    p.reset();
  }
  range.addEventListener('input', upd); upd();
});

// ---- live demo: explicit vs implicit damping ----------------------------
// One rotational DOF with a velocity actuator, which is what a joint PD
// controller's derivative term is. Explicit Euler applies -kv*v using the OLD
// velocity, so the correction overshoots once kv*dt/m > 2 and the overshoot
// compounds. The implicit form solves for the NEW velocity and cannot.
(function(){
  const c = document.getElementById('kvdemo'); if(!c) return;
  const ctx = c.getContext('2d');
  const kvIn = document.getElementById('kv'), kvOut = document.getElementById('kvval');
  const st = document.getElementById('kvstate');
  let A = {q:0.9, v:0}, B = {q:0.9, v:0}, t = 0, DT = 0.02, I = 1.0, blew = false;
  function reset(){ A={q:0.9,v:0}; B={q:0.9,v:0}; t=0; blew=false; }
  kvIn.addEventListener('input', reset);
  function v(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim();}
  function frame(){
    const kv = +kvIn.value;
    kvOut.textContent = 'kv = ' + kv;
    for (let k=0;k<3;k++){
      const g = -9.81*Math.sin(A.q);
      A.v = A.v + DT*(g - kv*A.v/I);      // explicit: old velocity
      A.q = A.q + DT*A.v;
      const gb = -9.81*Math.sin(B.q);
      B.v = (B.v + DT*gb) / (1 + DT*kv/I); // implicit: solved for the new one
      B.q = B.q + DT*B.v;
      t += DT;
      if (!isFinite(A.v) || Math.abs(A.v) > 1e6) blew = true;
    }
    const w=c.width=c.clientWidth, h=c.height=c.clientHeight;
    ctx.clearRect(0,0,w,h);
    const cx=w/2, cy=h*0.28, L=Math.min(w,h)*0.42;
    [[A, v('--red')||'#DE3A3E', -1],[B, v('--blue')||'#0C8FCB', 1]].forEach(function(p){
      const s=p[0]; if(!isFinite(s.q)) return;
      const q = Math.max(-6, Math.min(6, s.q));
      const x = cx + p[2]*w*0.16 + L*Math.sin(q), y = cy + L*Math.cos(q);
      ctx.strokeStyle=p[1]; ctx.lineWidth=3; ctx.beginPath();
      ctx.moveTo(cx+p[2]*w*0.16, cy); ctx.lineTo(x,y); ctx.stroke();
      ctx.fillStyle=p[1]; ctx.fillRect(x-5,y-5,10,10);
      ctx.fillRect(cx+p[2]*w*0.16-3, cy-3, 6, 6);
    });
    st.textContent = blew ? 'EXPLICIT DIVERGED' : 'both stable';
    st.className = 'verdict ' + (blew ? 'v-bad' : 'v-ok');
    requestAnimationFrame(frame);
  }
  frame();
})();

// ---- live demo: friction cone heading ----------------------------------
// Not a simulation: a lookup into the MEASURED sweep, drawn as the direction
// a box actually slid when pushed at that heading.
(function(){
  const c = document.getElementById('conedemo'); if(!c) return;
  const ctx=c.getContext('2d');
  const hIn=document.getElementById('heading'), hOut=document.getElementById('hval');
  const DATA = window.__CONE__;
  function v(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim();}
  function near(arr,h){let b=arr[0];for(const r of arr){if(Math.abs(r[0]-h)<Math.abs(b[0]-h))b=r;}return b;}
  function draw(){
    const h=+hIn.value;
    const p=near(DATA.pyramidal,h), e=near(DATA.elliptic,h);
    hOut.textContent='push heading '+h+'\\u00b0';
    document.getElementById('perr').textContent = p[1].toFixed(2)+'\\u00b0';
    document.getElementById('eerr').textContent = e[1].toFixed(2)+'\\u00b0';
    const w=c.width=c.clientWidth, hh=c.height=c.clientHeight;
    ctx.clearRect(0,0,w,hh);
    const cx=w*0.5, cy=hh*0.82, R=Math.min(w*0.42,hh*0.72);
    const rad=x=>x*Math.PI/180;
    ctx.setLineDash([5,5]); ctx.strokeStyle=v('--ink')||'#000'; ctx.lineWidth=2;
    ctx.beginPath(); ctx.moveTo(cx,cy);
    ctx.lineTo(cx+R*Math.cos(rad(h)), cy-R*Math.sin(rad(h))); ctx.stroke();
    ctx.setLineDash([]);
    [[p[1], v('--red')||'#DE3A3E'],[e[1], v('--green')||'#5FB44A']].forEach(function(d){
      const a=rad(h+d[0]);
      ctx.strokeStyle=d[1]; ctx.lineWidth=4; ctx.beginPath(); ctx.moveTo(cx,cy);
      ctx.lineTo(cx+R*Math.cos(a), cy-R*Math.sin(a)); ctx.stroke();
      ctx.fillStyle=d[1];
      ctx.fillRect(cx+R*Math.cos(a)-5, cy-R*Math.sin(a)-5, 10, 10);
    });
    ctx.fillStyle=v('--ink')||'#000'; ctx.fillRect(cx-5,cy-5,10,10);
  }
  hIn.addEventListener('input',draw); draw(); addEventListener('resize',draw);
})();
"""


REVEAL_JS = """
// Everything below only hides things it will later reveal, so the CSS that
// starts elements invisible is gated on this class. If this script never
// runs, the page renders complete rather than blank.
document.documentElement.classList.add('js');

// ---- reveal on first sight ---------------------------------------------
// Charts draw themselves when they scroll into view rather than being already
// finished when the reader arrives. Fires once per element, then unobserves.
(function(){
  const reduce = matchMedia && matchMedia('(prefers-reduced-motion:reduce)').matches;
  const targets = document.querySelectorAll('.figwrap, .win');
  if (reduce || !('IntersectionObserver' in window)){
    targets.forEach(function(el){ el.classList.add('in'); });
    return;
  }
  const io = new IntersectionObserver(function(entries){
    entries.forEach(function(e){
      if (e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); }
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
  targets.forEach(function(el){ io.observe(el); });
})();

// ---- headline numbers count up -----------------------------------------
// Only the tiles that are plainly numeric; anything with a unit or exponent is
// left alone rather than mangled into a wrong intermediate value.
(function(){
  const reduce = matchMedia && matchMedia('(prefers-reduced-motion:reduce)').matches;
  const tiles = document.querySelectorAll('.tile b, .chip b');
  const numeric = [];
  tiles.forEach(function(el){
    const raw = el.textContent.trim();
    if (!/^[0-9][0-9,]*$/.test(raw)) return;          // integers only
    numeric.push([el, parseInt(raw.replace(/,/g,''),10), raw]);
    if (!reduce) el.textContent = '0';
  });
  if (reduce || !('IntersectionObserver' in window)){
    numeric.forEach(function(n){ n[0].textContent = n[2]; });
    return;
  }
  const io = new IntersectionObserver(function(entries){
    entries.forEach(function(e){
      if (!e.isIntersecting) return;
      const rec = numeric.find(function(n){ return n[0] === e.target; });
      if (!rec) return;
      io.unobserve(e.target);
      const [el, target, raw] = rec;
      const dur = 620, t0 = performance.now();
      (function tick(t){
        const p = Math.min(1, (t - t0)/dur);
        const eased = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(target*eased).toLocaleString();
        if (p < 1) requestAnimationFrame(tick); else el.textContent = raw;
      })(t0);
    });
  }, { threshold: 0.6 });
  numeric.forEach(function(n){ io.observe(n[0]); });
})();
"""
