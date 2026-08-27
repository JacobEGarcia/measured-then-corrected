"""Build the artifact in a Susan Kare / classic Macintosh idiom.

Kare drew the original Mac icons on graph paper at 16x16 and designed Chicago,
the system font. Two of her conventions are load-bearing here:

  the bomb  -- what a classic Mac showed when something went wrong. It marks
               every correction on this page, which is most of them.
  Chicago for chrome, Geneva for content -- the Mac used a chunky bitmap face
               for UI and a legible one for text. A pixel font set at reading
               length is a costume, not a design, so the same split applies:
               Silkscreen for titles, labels and numbers; a clean sans for
               prose.

Colour is the Apple six-stripe palette, which is period-correct and doubles as
a categorical scale for the charts.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "figs"))
import charts   # noqa: E402
import pixel    # noqa: E402
import demos    # noqa: E402
import json as _json

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "artifact_kare.html")

F = {n: getattr(charts, n)() for n in (
    "friction_polar", "integrator_order", "physx_iteration_cliff", "grasp_bars",
    "integrator_stability_bars", "crossengine_penetration", "mass_ratio_cliff",
    "collision_bars", "tree_vs_loop", "gait_schedule", "trot_wheel",
    "friction_recovery", "chaos_divergence", "one_spec_three_formats",
    "reflected_inertia", "identifiability", "solver_speed",
    "phase_profile", "scale_bars", "contact_clamp")}
F["corrections_tally"] = charts.corrections_tally(total=13, studies=19)

det = charts.load("determinism")
LAM = round((det["chaos_smooth_1ulp"]["lyapunov_exponent_per_s"]
             + det["chaos_smooth_seeded_1e-12"]["lyapunov_exponent_per_s"]) / 2, 2)
PRED = det["predictive_check"]
SPOT = charts.load("gait_result")["trot_error"]["Spot"]
SEQ = charts.load("render_frames")
_fc = charts.load("friction_cone")
CONE = {c: [[r["heading_deg"], r["direction_error_deg"]]
            for r in _fc["sweeps"][c]] for c in ("pyramidal", "elliptic")}

# which pre-rendered runs held, from the closed form F_min = m*g/(2*mu) = 6.13 N
GRIP_MARK = {"3": 0, "4.5": 0, "6": 0, "6.5": 1, "7.5": 1, "10": 1}
STACK_MARK = {"1": 1, "10": 1, "100": 0, "1000": 0}

I = lambda n, px=4: pixel.icon(n, px=px)          # noqa: E731

HEAD = """<title>Measured, Then Corrected</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Silkscreen:wght@400;700&family=Rubik:wght@400;500;600&display=swap">
"""

CSS = """<style>
:root{
  /* Apple's six stripes: period-correct, and a categorical scale for charts */
  --green:#5FB44A; --yellow:#F2B01E; --orange:#EE7623;
  --red:#DE3A3E;   --purple:#8C3E92; --blue:#0C8FCB;

  --ink:#000000; --paper:#FFFFFF; --desk:#9C9C9C; --deskdot:#8A8A8A;
  --stone:#5A5A5A; --rule:#000000; --shade:#C8C8C8;

  /* charts.py speaks these names; remapping them re-skins every figure */
  --snow:#FFFFFF; --linen:#FFFFFF; --plot:#FFFFFF; --ash:#B4B4B4;
  --slate:#000000; --hair:#000000;
  --fjord:var(--blue); --lingon:var(--red); --moss:var(--green);
  --sand:var(--orange);

  --fC:"Silkscreen","Courier New",monospace;
  --fB:"Rubik",-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;
  --col:60ch; --pad:clamp(1rem,4vw,2.5rem);
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ink:#FFFFFF; --paper:#101010; --desk:#2A2A2A; --deskdot:#333333;
    --stone:#A8A8A8; --rule:#FFFFFF; --shade:#2E2E2E;
    --snow:#101010; --linen:#101010; --plot:#0A0A0A; --ash:#4A4A4A;
    --slate:#FFFFFF; --hair:#FFFFFF;
    --green:#7BD165; --yellow:#F5C542; --orange:#FF9040;
    --red:#FF5F63; --purple:#B061B6; --blue:#3FB5EE;
  }
}
:root[data-theme="dark"]{
  --ink:#FFFFFF; --paper:#101010; --desk:#2A2A2A; --deskdot:#333333;
  --stone:#A8A8A8; --rule:#FFFFFF; --shade:#2E2E2E;
  --snow:#101010; --linen:#101010; --plot:#0A0A0A; --ash:#4A4A4A;
  --slate:#FFFFFF; --hair:#FFFFFF;
  --green:#7BD165; --yellow:#F5C542; --orange:#FF9040;
  --red:#FF5F63; --purple:#B061B6; --blue:#3FB5EE;
}
*{box-sizing:border-box}

/* the desktop: a 50% dither, which is how the Mac made grey out of 1 bit */
body{margin:0;color:var(--ink);font-family:var(--fB);font-size:1rem;
  line-height:1.6;-webkit-font-smoothing:antialiased;
  background-color:var(--desk);
  background-image:linear-gradient(45deg,var(--deskdot) 25%,transparent 25%,
    transparent 75%,var(--deskdot) 75%),
    linear-gradient(45deg,var(--deskdot) 25%,transparent 25%,
    transparent 75%,var(--deskdot) 75%);
  background-size:4px 4px; background-position:0 0,2px 2px;}
.wrap{max-width:72rem;margin:0 auto;padding:0 var(--pad)}

/* ---------- window chrome ---------- */
.win{background:var(--paper);border:2px solid var(--rule);
  box-shadow:5px 5px 0 0 var(--rule);margin:0 0 clamp(1.5rem,4vw,2.5rem)}
.bar{border-bottom:2px solid var(--rule);display:flex;align-items:center;
  gap:.5rem;padding:.3rem .45rem;background:
    repeating-linear-gradient(to bottom,var(--ink) 0 1px,transparent 1px 3px);}
.box{width:13px;height:13px;border:2px solid var(--rule);background:var(--paper);
  flex:0 0 auto}
.bar h3{font-family:var(--fC);font-size:.72rem;font-weight:700;margin:0;
  padding:.1rem .5rem;background:var(--paper);letter-spacing:.02em;
  text-transform:uppercase;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis}
.bar .grow{flex:1 1 auto}
.body{padding:clamp(.9rem,2.5vw,1.5rem)}

/* ---------- masthead ---------- */
.mast{padding:clamp(2rem,6vw,4rem) 0 0}
h1{font-family:var(--fC);font-weight:700;
  font-size:clamp(1.6rem,5.2vw,3.4rem);line-height:1.25;letter-spacing:.01em;
  margin:0 0 1.25rem;text-transform:uppercase}
.sub{max-width:var(--col);font-size:1.02rem;color:var(--stone);margin:0}
.sub b{color:var(--ink);font-weight:600}
.hi{background:var(--yellow);padding:0 .2em;color:#000}

/* ---------- stat tiles ---------- */
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(8rem,1fr));
  gap:0;border-top:2px solid var(--rule)}
.tile{border-right:2px solid var(--rule);border-bottom:2px solid var(--rule);
  padding:.8rem .7rem;display:flex;flex-direction:column;gap:.25rem}
.tile:last-child{border-right:0}
.tile b{font-family:var(--fC);font-size:clamp(.95rem,2.2vw,1.25rem);
  line-height:1.2;word-break:break-all}
.tile span{font-family:var(--fC);font-size:.55rem;line-height:1.5;
  color:var(--stone);text-transform:uppercase}

/* ---------- pixel icons ---------- */
.px{display:block;image-rendering:pixelated}
.ico-row{display:flex;align-items:center;gap:.6rem;margin-bottom:.5rem}
.ico-row .px{flex:0 0 auto}

/* ---------- layout ---------- */
main{padding:clamp(1.5rem,4vw,2.5rem) 0 0}
.grid2{display:grid;gap:clamp(1rem,3vw,2rem)}
@media(min-width:62rem){.grid2{grid-template-columns:minmax(0,17rem) minmax(0,1fr);
  align-items:start}}
.say{display:flex;flex-direction:column;gap:.7rem}
h2{font-family:var(--fC);font-weight:700;font-size:clamp(.95rem,2.1vw,1.15rem);
  line-height:1.45;margin:0;text-transform:uppercase}
.say p{margin:0;font-size:.94rem;color:var(--stone)}
.say p b{color:var(--ink);font-weight:600}
code{font-family:var(--fC);font-size:.8em;background:var(--shade);
  padding:.05em .3em;color:var(--ink)}

/* ---------- the bomb: a correction ---------- */
.bomb{border:2px solid var(--rule);background:var(--paper);margin-top:.4rem}
.bomb .hd{display:flex;align-items:center;gap:.5rem;padding:.4rem .5rem;
  border-bottom:2px solid var(--rule);background:var(--red)}
.bomb .hd b{font-family:var(--fC);font-size:.6rem;color:#FFF;
  text-transform:uppercase;letter-spacing:.04em}
.bomb p{margin:0;padding:.7rem .6rem;font-size:.89rem;color:var(--stone)}
.bomb p + p{padding-top:0}

/* ---------- number chips ---------- */
.chips{display:flex;flex-wrap:wrap;gap:0;border-top:2px solid var(--rule);
  border-left:2px solid var(--rule);margin-top:.5rem}
.chip{border-right:2px solid var(--rule);border-bottom:2px solid var(--rule);
  padding:.45rem .55rem;display:flex;flex-direction:column;gap:.1rem;flex:1 1 6rem}
.chip b{font-family:var(--fC);font-size:.82rem}
.chip span{font-family:var(--fC);font-size:.5rem;color:var(--stone);
  text-transform:uppercase;line-height:1.5}
.ok b{color:var(--green)} .bad b{color:var(--red)}

/* ---------- figures ---------- */
.figwrap{border:2px solid var(--rule);background:var(--paper);padding:.6rem;
  overflow-x:auto}
.figwrap + .figwrap{margin-top:.75rem}
svg:not(.px){display:block;max-width:100%;height:auto;overflow:visible}
.plot-bg{fill:var(--plot)}
.grid{stroke:var(--ash);stroke-width:1}
.axis,.axis-spoke{stroke:var(--ink);stroke-width:2}
.ring{fill:none;stroke:var(--ash);stroke-width:1}
.marker{stroke:var(--red);stroke-width:2;stroke-dasharray:4 4}
.divider{stroke:var(--ink);stroke-width:2}
.lbl,.tick,.cap,.barval,.figtitle{font-family:var(--fC);fill:var(--stone)}
.tick{font-size:9px} .cap{font-size:8px;text-transform:uppercase}
.cap-warn{font-family:var(--fC);font-size:8px;text-transform:uppercase;fill:var(--red)}
.barval{font-size:9px;fill:var(--ink)}
.figtitle{font-size:9px;text-transform:uppercase;fill:var(--ink)}
.figtitle-warn{font-family:var(--fC);font-size:9px;text-transform:uppercase;fill:var(--red)}
.series-a{stroke:var(--blue);stroke-width:3;stroke-linejoin:miter;stroke-linecap:butt}
.series-b{stroke:var(--orange);stroke-width:3;stroke-linejoin:miter}
.series-c{stroke:var(--purple);stroke-width:2;stroke-dasharray:5 4}
.series-ok{stroke:var(--green);stroke-width:3;stroke-linejoin:miter}
.series-warn{stroke:var(--red);stroke-width:3;stroke-linejoin:miter}
.series-a-dot{fill:var(--blue)} .series-b-dot{fill:var(--orange)}
.series-c-dot{fill:var(--purple)} .series-ok-dot{fill:var(--green)}
.series-warn-dot{fill:var(--red)}
.key-a,.key-series-a{font-family:var(--fC);font-size:9px;fill:var(--blue)}
.key-b,.key-series-b{font-family:var(--fC);font-size:9px;fill:var(--orange)}
.key-series-c{font-family:var(--fC);font-size:9px;fill:var(--purple)}
.key-ok,.key-series-ok{font-family:var(--fC);font-size:9px;fill:var(--green)}
.key-warn{font-family:var(--fC);font-size:9px;fill:var(--red)}
.key-num{font-family:var(--fC);font-size:11px;fill:var(--ink)}
.bar-a{fill:var(--orange)} .bar-b{fill:var(--blue)} .bar-warn{fill:var(--red)}
.band-warn{fill:var(--red);opacity:.16}
.band-ok{fill:var(--green);opacity:.18}
.band-flat{fill:var(--blue);opacity:.14}
.node{fill:var(--paper);stroke:var(--ink);stroke-width:2}
.link{stroke:var(--ink);stroke-width:2}
.link-close{stroke:var(--red);stroke-width:3}
.lane{fill:var(--plot);stroke:var(--ink);stroke-width:1}
.stance-ok{fill:var(--green)} .stance-warn{fill:var(--red)}
.tally-on{fill:var(--red)} .tally-off{fill:var(--shade)}

/* ---------- hero ---------- */
#chaos{display:block;width:100%;height:clamp(260px,40vw,400px);
  image-rendering:pixelated;background:var(--paper)}
.legend{display:flex;flex-wrap:wrap;gap:.4rem 1.25rem;padding:.55rem .6rem;
  border-top:2px solid var(--rule);font-family:var(--fC);font-size:.6rem;
  align-items:center}
.sw{width:10px;height:10px;display:inline-block;margin-right:.35rem;
  vertical-align:-1px}

/* ---------- demos ---------- */
.demo{border:2px solid var(--rule);background:var(--paper)}
.demo img,.demo canvas{display:block;width:100%;background:var(--paper);
  image-rendering:auto}
.demo canvas{height:230px}
.ctl{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem .9rem;
  padding:.55rem .6rem;border-top:2px solid var(--rule);font-family:var(--fC);
  font-size:.6rem}
.ctl input[type=range]{flex:1 1 8rem;min-width:7rem;accent-color:var(--blue);
  height:1.1rem}
.ctl label{white-space:nowrap}
.verdict{font-family:var(--fC);font-size:.62rem;padding:.15rem .4rem;
  border:2px solid var(--rule);white-space:nowrap}
.v-ok{background:var(--green);color:#000}
.v-bad{background:var(--red);color:#FFF}
.duo{display:grid;grid-template-columns:1fr 1fr;gap:0}
.duo>div{border-right:2px solid var(--rule)}
.duo>div:last-child{border-right:0}
.duo .cap2{font-family:var(--fC);font-size:.58rem;padding:.35rem .45rem;
  border-top:2px solid var(--rule);text-align:center}
.note{font-family:var(--fC);font-size:.52rem;color:var(--stone);
  padding:.4rem .6rem;border-top:2px solid var(--rule);line-height:1.6}
footer{padding:0 0 clamp(3rem,8vw,5rem)}
footer p{margin:0 0 .8rem;max-width:var(--col);color:var(--stone);font-size:.94rem}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
</style>"""


HERO_JS = """<script>
(function(){
  // The determinism study, running. Two double pendulums seeded 1e-12 apart,
  // integrated RK4. Drawn on a coarse pixel grid rather than as smooth lines,
  // because a 1-bit machine could not have drawn it any other way -- and the
  // quantisation makes the moment they separate easier to see, not harder.
  var c=document.getElementById('chaos'); if(!c) return;
  var ctx=c.getContext('2d'), P=4;
  var reduce=matchMedia&&matchMedia('(prefers-reduced-motion:reduce)').matches;
  function size(){var r=c.getBoundingClientRect();
    c.width=Math.max(1,Math.floor(r.width/P)); c.height=Math.max(1,Math.floor(r.height/P));}
  size(); addEventListener('resize',size);
  var g=9.81,L1=1,L2=1,m1=1,m2=1;
  function deriv(s){var a=s[0],b=s[1],da=s[2],db=s[3],d=a-b,
    den=2*m1+m2-m2*Math.cos(2*d);
    return [da,db,
      (-g*(2*m1+m2)*Math.sin(a)-m2*g*Math.sin(a-2*b)
       -2*Math.sin(d)*m2*(db*db*L2+da*da*L1*Math.cos(d)))/(L1*den),
      (2*Math.sin(d)*(da*da*L1*(m1+m2)+g*(m1+m2)*Math.cos(a)
       +db*db*L2*m2*Math.cos(d)))/(L2*den)];}
  function step(s,h){function ax(u,v,k){return [u[0]+k*v[0],u[1]+k*v[1],u[2]+k*v[2],u[3]+k*v[3]];}
    var k1=deriv(s),k2=deriv(ax(s,k1,h/2)),k3=deriv(ax(s,k2,h/2)),k4=deriv(ax(s,k3,h));
    return s.map(function(v,i){return v+h/6*(k1[i]+2*k2[i]+2*k3[i]+k4[i]);});}
  var A=[2.0,1.0,0,0],B=[2.0+1e-12,1.0,0,0],t=0,trA=[],trB=[],MAX=260;
  function tip(s,cx,cy,sc){var x=cx+sc*Math.sin(s[0]),y=cy+sc*Math.cos(s[0]);
    return [x+sc*Math.sin(s[1]),y+sc*Math.cos(s[1]),x,y];}
  function v(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim();}
  function line(x0,y0,x1,y1,col){ // Bresenham, one pixel at a time
    x0=Math.round(x0);y0=Math.round(y0);x1=Math.round(x1);y1=Math.round(y1);
    var dx=Math.abs(x1-x0),dy=Math.abs(y1-y0),sx=x0<x1?1:-1,sy=y0<y1?1:-1,e=dx-dy;
    ctx.fillStyle=col;
    for(;;){ctx.fillRect(x0,y0,1,1);
      if(x0===x1&&y0===y1)break; var e2=2*e;
      if(e2>-dy){e-=dy;x0+=sx;} if(e2<dx){e+=dx;y0+=sy;}}}
  function draw(){
    var w=c.width,h=c.height,cx=w/2,cy=h*0.30,sc=Math.min(w,h)*0.20;
    ctx.fillStyle=v('--paper')||'#fff'; ctx.fillRect(0,0,w,h);
    var CA=v('--blue')||'#0C8FCB', CB=v('--red')||'#DE3A3E', CI=v('--ink')||'#000';
    [[trA,CA],[trB,CB]].forEach(function(p){var tr=p[0];
      for(var i=1;i<tr.length;i++) line(tr[i-1][0],tr[i-1][1],tr[i][0],tr[i][1],p[1]);});
    [[A,CA],[B,CB]].forEach(function(p){var T=tip(p[0],cx,cy,sc);
      line(cx,cy,T[2],T[3],CI); line(T[2],T[3],T[0],T[1],CI);
      ctx.fillStyle=p[1]; ctx.fillRect(Math.round(T[0])-1,Math.round(T[1])-1,3,3);
      ctx.fillRect(Math.round(T[2])-1,Math.round(T[3])-1,2,2);});
    ctx.fillStyle=CI; ctx.fillRect(Math.round(cx)-1,Math.round(cy)-1,3,3);
  }
  function frame(){
    if(!reduce){
      for(var i=0;i<26;i++){A=step(A,0.0016);B=step(B,0.0016);t+=0.0016;}
      var w=c.width,h=c.height,cx=w/2,cy=h*0.30,sc=Math.min(w,h)*0.20;
      trA.push(tip(A,cx,cy,sc)); trB.push(tip(B,cx,cy,sc));
      if(trA.length>MAX){trA.shift();trB.shift();}
      var el=document.getElementById('sep');
      if(el){var TA=tip(A,cx,cy,sc),TB=tip(B,cx,cy,sc);
        var s=Math.hypot(TA[0]-TB[0],TA[1]-TB[1])/sc;
        el.textContent='t='+t.toFixed(1)+'s  sep='+(s<1e-3?s.toExponential(1):s.toFixed(3));}
      if(t>26){A=[2.0,1.0,0,0];B=[2.0+1e-12,1.0,0,0];t=0;trA=[];trB=[];}
    }
    draw(); requestAnimationFrame(frame);
  }
  frame();
})();
</script>"""


def win(title, icon_name, inner, extra=""):
    return (f'<section class="win {extra}"><div class="bar"><span class="box"></span>'
            f'<h3>{title}</h3><span class="grow"></span></div>'
            f'<div class="body">{inner}</div></section>')


def study(title, icon_name, said, figs, chips=None, bomb=None, src=""):
    left = [f'<div class="ico-row">{I(icon_name, 5)}</div>', f"<h2>{title}</h2>"]
    for p in said:
        left.append(f"<p>{p}</p>")
    if chips:
        cells = "".join(f'<div class="chip {c}"><b>{v}</b><span>{l}</span></div>'
                        for v, l, c in chips)
        left.append(f'<div class="chips">{cells}</div>')
    if bomb:
        ps = "".join(f"<p>{x}</p>" for x in bomb[1])
        left.append(f'<div class="bomb"><div class="hd">{I("bomb", 3)}'
                    f'<b>{bomb[0]}</b></div>{ps}</div>')
    if src:
        left.append(f'<p><code>{src}</code></p>')
    right = "".join(f'<div class="figwrap">{f}</div>' for f in figs)
    return win(title, icon_name,
               f'<div class="grid2"><div class="say">{"".join(left)}</div>'
               f'<div>{right}</div></div>')


GRIP_DEMO = """
      <div class="demo" data-slider="grasp_slider"
           data-keys='["3","4.5","6","6.5","7.5","10"]'
           data-marks='{"3":0,"4.5":0,"6":0,"6.5":1,"7.5":1,"10":1}'
           data-unit="grip force %s N" data-ok="HELD" data-bad="DROPPED" data-fps="16">
        <img alt="grasp at the selected grip force">
        <div class="ctl">
          <label data-val>grip force 3 N</label>
          <input type="range" min="0" max="5" step="1" value="0" aria-label="grip force">
          <span data-verdict class="verdict">DROPPED</span>
        </div>
        <div class="note">Each position is a separate MuJoCo run, rendered
        offscreen. Nothing is recomputed when you drag &mdash; you are switching
        between real runs. The threshold falls between 6 and 6.5 N; closed form
        says 6.13, bisection measured 6.44.</div>
      </div>"""
STACK_DEMO = """
      <div class="demo" data-slider="stack_slider"
           data-keys='["1","10","100","1000"]'
           data-marks='{"1":1,"10":1,"100":0,"1000":0}'
           data-unit="mass ratio %s to 1" data-ok="STACK HOLDS" data-bad="CRUSHED" data-fps="14">
        <img alt="stack at the selected mass ratio">
        <div class="ctl">
          <label data-val>mass ratio 1 to 1</label>
          <input type="range" min="0" max="3" step="1" value="0" aria-label="mass ratio">
          <span data-verdict class="verdict">STACK HOLDS</span>
        </div>
        <div class="note">Four real runs. The light block is 1 kg throughout;
        only the block on top changes. PhysX fails between 10 and 100, MuJoCo
        degrades gradually &mdash; the charts above measure both.</div>
      </div>"""
KV_DEMO = """
      <div class="demo">
        <canvas id="kvdemo" aria-label="explicit versus implicit damping at the selected gain"></canvas>
        <div class="ctl">
          <label id="kvval">kv = 5</label>
          <input type="range" id="kv" min="1" max="120" step="1" value="5" aria-label="derivative gain">
          <span id="kvstate" class="verdict v-ok">both stable</span>
        </div>
        <div class="note">LIVE, and a reduced model: one rotational DOF, not the
        measured system. Explicit Euler (red) applies the damping force using the
        OLD velocity, so past kv&middot;dt/I = 2 the correction overshoots and
        compounds. The implicit form (blue) solves for the new velocity and
        cannot. Push the gain past about 100.</div>
      </div>"""
CONE_DEMO = """
      <div class="demo">
        <canvas id="conedemo" aria-label="direction a box slid versus the direction it was pushed"></canvas>
        <div class="ctl">
          <label id="hval">push heading 20&deg;</label>
          <input type="range" id="heading" min="0" max="90" step="5" value="20" aria-label="push heading">
          <span class="verdict v-bad">PYR <span id="perr">0</span></span>
          <span class="verdict v-ok">ELL <span id="eerr">0</span></span>
        </div>
        <div class="note">Dashed line is where the box was pushed; solid lines
        are where it actually went. Values are looked up from the MEASURED
        sweep, not simulated here. Try 0, 45 and 90 &mdash; the square&rsquo;s
        symmetry axes, where the error vanishes.</div>
      </div>"""

BODY = f"""
<div class="wrap mast">
  <section class="win">
    <div class="bar"><span class="box"></span><h3>Measured, Then Corrected</h3>
      <span class="grow"></span></div>
    <div class="body">
      <div class="ico-row">{I("mac", 6)}</div>
      <h1>Measured,<br>Then Corrected</h1>
      <p class="sub">Nineteen studies against one robot model in three formats.
      Every number came out of a run that reproduces from the repository &mdash;
      and so did every <b>correction</b>, because in
      <span class="hi">thirteen of the nineteen</span> the first answer was wrong.</p>
    </div>
    <div class="tiles">
      <div class="tile"><b>90</b><span>CI gates<br>4 test the gates</span></div>
      <div class="tile"><b>3.3e-16</b><span>max FK error<br>2000 configs</span></div>
      <div class="tile"><b>{LAM}/s</b><span>Lyapunov<br>exponent</span></div>
      <div class="tile"><b>3.994</b><span>RK4 order<br>theory 4</span></div>
      <div class="tile"><b>812670</b><span>steps/sec<br>65536 envs</span></div>
      <div class="tile"><b>13</b><span>wrong answers<br>caught</span></div>
    </div>
  </section>

  <section class="win">
    <div class="bar"><span class="box"></span><h3>Chaos.sim</h3>
      <span class="grow"></span></div>
    <canvas id="chaos" aria-label="Two double pendulums seeded 1e-12 apart, diverging"></canvas>
    <div class="legend">
      <span><span class="sw" style="background:var(--blue)"></span>PENDULUM A</span>
      <span><span class="sw" style="background:var(--red)"></span>PENDULUM B &mdash; SEEDED 1e-12 APART</span>
      <span id="sep">t=0.0s</span>
      <span>IDENTICAL PHYSICS. THEY SEPARATE AT {LAM} E-FOLDS/SEC.</span>
    </div>
  </section>
</div>

<div class="wrap">
  <section class="win">
    <div class="bar"><span class="box"></span><h3>Footage.mov &mdash; rendered from the models</h3>
      <span class="grow"></span></div>
    <div class="body">
      <p class="sub" style="margin-bottom:.9rem">No photographs of any of this
      exist: the runs were headless, on a GPU whose RTX renderer never
      initialised. What follows is the <b>actual models</b>, rasterised
      offscreen from the same XML the physics ran on.</p>
      <div class="demo">
        <div class="duo">
          <div><img src="{SEQ['grasp_slips'][0]}" data-seq="grasp_slips" data-fps="16" alt="grip force below the Coulomb threshold, block falls">
            <div class="cap2">4 N &mdash; BELOW THRESHOLD</div></div>
          <div><img src="{SEQ['grasp_holds'][0]}" data-seq="grasp_holds" data-fps="16" alt="grip force above the threshold, block held">
            <div class="cap2">9 N &mdash; ABOVE THRESHOLD</div></div>
        </div>
        <div class="note">Same grasp, same block, same friction. The closed form
        says it needs 6.13 N; measured 6.44 N. Below it, the block leaves.</div>
      </div>
      <div class="demo" style="margin-top:1rem">
        <img src="{SEQ['arm'][0]}" data-seq="arm" data-fps="20"
             alt="the three-DOF arm swinging under gravity">
        <div class="note">The 3-DOF arm this whole repository is built around,
        released from a raised pose and swinging under gravity. Same
        <code>model/arm3.xml</code> the 151 property checks and the
        forward-kinematics cross-check run against.</div>
      </div>
      <div class="demo" style="margin-top:1rem">
        <div class="duo">
          <div><img src="{SEQ['stack_slider']['1'][0]}" data-seq="stack_slider.1" data-fps="14" alt="equal mass stack, stable">
            <div class="cap2">MASS RATIO 1</div></div>
          <div><img src="{SEQ['stack_slider']['1000'][0]}" data-seq="stack_slider.1000" data-fps="14" alt="1000 to 1 mass ratio, light box crushed">
            <div class="cap2">MASS RATIO 1000</div></div>
        </div>
        <div class="note">The heavy block drives the light one into the floor.
        This is the 50 mm of squash the stability study measured, happening.</div>
      </div>
    </div>
  </section>
</div>

<main class="wrap">

{study("One spec, three formats", "floppy",
  ["A single Python spec emits MJCF, URDF and SDF. Link geometry, mass, inertia "
   "and joint limits are computed once, never typed twice.",
   "Validated two ways: 151 property comparisons across the three files, then "
   "an independent NumPy forward-kinematics implementation checked against "
   "MuJoCo's own over 2000 random configurations."],
  [F["one_spec_three_formats"]],
  chips=[("151/151", "properties agree", "ok"),
         ("3.3e-16", "max FK error m", "ok"),
         ("2000", "configs checked", "")],
  bomb=("The files agreed with themselves",
        ["The first emitter passed all 147 numeric checks and still had a "
         "<b>0.23 m</b> forward-kinematics error. MJCF <code>size</code> is a "
         "<b>half</b> extent; URDF and SDF <code>box size</code> is the "
         "<b>full</b> extent. Every property matched because each format was "
         "being compared against itself."]),
  src="model/robot_spec.py &middot; model/emit.py &middot; model/validate.py")}

{study("Reproducibility", "stopwatch",
  ["Repeated runs are <b>bit-identical</b>. So is a re-parsed model. Adding an "
   "untouched body three metres away changes nothing.",
   "What bounds reproducibility is chaos. Two perturbation sizes recover the "
   "same exponent, and the exponent fitted on one run blind-predicts the other."],
  [F["chaos_divergence"]],
  chips=[(f"{PRED['predicted_1mm_s']}s", "predicted 1mm", ""),
         (f"{PRED['measured_1mm_s']}s", "measured", "ok"),
         ("1.2%", "seeds agree", "ok"),
         ("6.5x", "contact slower", "")],
  bomb=("Two floating-point traps",
        ["A one-ULP nudge of <code>2.22e-16</code> added to a coordinate of "
         "<code>2.0</code> &mdash; whose ULP is twice that &mdash; rounds away "
         "entirely. The runs came out bit-identical and read as no chaos.",
         "And <code>nextafter(0,1)</code> is the smallest <b>denormal</b>, "
         "which produced a meaningless 2e305x growth figure."]),
  src="model/determinism.py")}

{study("Friction has the shape of a square", "cube",
  ["Coulomb friction confines the tangential force to a <b>circle</b>. The "
   "common approximation uses a <b>polygon</b> &mdash; and the polygon shows.",
   "Error is zero at 0, 45 and 90 degrees &mdash; the square's symmetry axes "
   "&mdash; and peaks between them. Eight lobes around the circle."],
  [F["friction_polar"], CONE_DEMO],
  chips=[("12.76d", "pyramidal worst", "bad"),
         ("0.71d", "elliptic worst", "ok"),
         ("2.6x", "elliptic faster", "ok")],
  bomb=("What I got wrong, in my own docstring",
        ["I called the pyramid the cheaper option. It is 2.6x <b>slower</b> as "
         "well as 18x less accurate &mdash; dominated on both axes."]),
  src="model/friction_cone.py")}

{study("Verify the order, not the vibe", "magnifier",
  ["A method of order <em>p</em> has global error <code>O(dt^p)</code>, so the "
   "slope of a log-log plot <b>is</b> the order. All four land on theirs.",
   "Then the ranking reverses. With a stiff velocity actuator &mdash; a joint "
   "PD controller's derivative term &mdash; <b>RK4 is less stable than Euler</b>."],
  [F["integrator_order"], F["integrator_stability_bars"], KV_DEMO],
  bomb=("isfinite() is not a stability test",
        ["The first sweep called Euler <b>stable at kv=500</b> after it failed "
         "at 20, 50 and 100. MuJoCo detects a diverged step and <b>resets the "
         "state to zero</b> &mdash; it hit <code>|qvel|=3.45e5</code>, got "
         "reset, then sat at exactly zero for 397 steps. Perfectly finite, "
         "perfectly meaningless."]),
  src="model/integrators.py")}

{study("Two engines, two shapes of failure", "scales",
  ["The same experiment in MuJoCo and PhysX. They <b>agree</b> on something "
   "non-obvious: penetration is invariant to a 1000x mass change in each.",
   "They disagree on everything else. MuJoCo is flat until <code>2*dt</code> "
   "passes its 0.02s time constant. PhysX has no constant to clamp."],
  [F["crossengine_penetration"], F["mass_ratio_cliff"]],
  chips=[("2155x", "softer at 480Hz", ""),
         ("61x", "softer at 60Hz", ""),
         ("37x", "PhysX jump", "bad")],
  bomb=("Right answer, unverified reasoning",
        ["Both predictions were confirmed. One of the two <b>reasons</b> was "
         "not: I attributed PhysX's mass independence to the rest offset, but "
         "<code>rest_offset</code> read 0.0 for the entire sweep."]),
  src="model/crossengine_contact.py")}

{study("A cliff, not a curve", "wrench",
  ["In MuJoCo, solver iterations never help a bad mass ratio &mdash; 1 and 50 "
   "give identical results.",
   "In PhysX they help, but as a <b>step function</b>: 1, 32 and 64 are "
   "indistinguishable failures and 96 is a working stack."],
  [F["physx_iteration_cliff"], STACK_DEMO],
  chips=[("64>96", "where it flips", "bad"),
         ("0", "velocity iters help", "bad"),
         ("255", "still fails at 1e4", "bad")],
  bomb=("The control that named the mechanism",
        ["Velocity iterations at 1, 32, 128 and 255 all leave it at ~100mm. So "
         "the cliff is not about total solver effort &mdash; it is "
         "specifically <b>position-level depenetration work</b>. That turns a "
         "correlation into a mechanism."]),
  src="model/crossengine_stack.py")}
"""


BODY += f"""
{study("A grip force nobody supplied", "gripper",
  ["A parallel-jaw grasp holds when <code>2*mu*F >= m*g</code>. Friction and "
   "mass go in; the holding threshold comes out of the dynamics.",
   "<b>All four land above the closed form</b>, and the sign is the point. A "
   "measurement <b>below</b> theory would mean the contact model invents "
   "friction the materials do not license."],
  [F["grasp_bars"], GRIP_DEMO],
  chips=[("+7.5%", "mean excess", ""),
         ("0.37N", "additive offset", "ok"),
         ("4x", "tighter than rel.", "ok")],
  bomb=("Testing the explanation, not asserting it",
        ["The excess could be proportional or additive. Absolute excess "
         "clusters at 0.313 / 0.451 / 0.331 / 0.368 N with a coefficient of "
         "variation of <b>0.144</b>, against 0.598 for the relative reading. "
         "Additive wins by 4x."]),
  src="model/grasp.py")}

{study("Eleven attempts, then a trot", "quadruped",
  ["A trot has one signature: diagonal pairs move <b>together</b>, and the two "
   "pairs are half a cycle apart.",
   "Ten attempts measured in the world frame and kept describing a robot "
   "falling over. The eleventh changed the <b>frame</b>: a gait generator's "
   "output is the foot trajectory relative to the trunk."],
  [F["trot_wheel"], F["gait_schedule"]],
  chips=[(f"{SPOT['diag_FL_HR_deg']}d", "FL+HR apart", "ok"),
         (f"{SPOT['diag_FR_HL_deg']}d", "FR+HL apart", "ok"),
         (f"{SPOT['between_pairs_deg']}d", "between pairs", "ok"),
         (f"{SPOT['worst_deviation_deg']}d", "worst dev.", "ok")],
  bomb=("One robot of three, and the others are diagnosed",
        ["ANYmal: two of four legs resolved to a <b>shank</b> rather than a "
         "foot, so the tracked points sit partway up the chain. A1: the legs "
         "never moved at all &mdash; 1e-5 m of excursion.",
         "The error that cost the most named the wrong subsystem. An "
         "<code>if</code> sat outside the stepping loop, so the sim was never "
         "stepped and the arrays stayed empty &mdash; surfacing as "
         "<code>zero-size array to reduction</code>. I read that as foot "
         "detection failing and rewrote foot detection twice."]),
  src="model/gait_result.py")}

{study("Reading friction back out", "check",
  ["<code>mu</code> goes into PhysX as a material property. The angle at which "
   "a block slides comes out of the dynamics. <code>tan(theta) = mu</code> "
   "closes the loop.",
   "Three coefficients recovered to better than 2% &mdash; without ever asking "
   "the engine what friction it was using."],
  [F["friction_recovery"]],
  chips=[("+1.9%", "mu 0.3", ""), ("+1.9%", "mu 0.5", ""),
         ("+1.2%", "mu 0.8", ""), ("0.435d", "max overshoot", "ok")],
  bomb=("My prediction was wrong in DIRECTION",
        ["I predicted a low bias, reasoning that pre-slip creep would trip the "
         "detector early. But the sweep steps in 2-degree increments, so the "
         "first angle flagged can only ever be the first grid line <b>at or "
         "above</b> the threshold. The bias had to be positive.",
         "Creep is there in the data &mdash; 0.4 to 0.8 mm one step before "
         "release &mdash; it just never reaches the detection threshold."]),
  src="model/friction_recovery.py")}

{study("What URDF cannot say", "tree",
  ["URDF is a <b>tree</b>: one parent per link. Four-bar linkages, parallel "
   "jaws and differential drives are outside the format's data model.",
   "Drop the closure and the mechanism still simulates, still looks plausible, "
   "and is <b>half dead</b> &mdash; the rocker travels 0.0000 rad."],
  [F["tree_vs_loop"]],
  chips=[("0.0000", "open rocker rad", "bad"),
         ("0.7191", "closed rocker rad", "ok"),
         ("109x", "tuning the closure", "")],
  bomb=("Wrong diagnosis, then the correction",
        ["A 57mm worst-case gap looked like a soft constraint. Stiffening "
         "moved the mean 109x and the max barely at all &mdash; because the "
         "max is at <b>step 0</b>. The model was spawned 60.7mm off the "
         "constraint manifold."]),
  src="model/closed_chain.py")}

{study("The metric measured the wrong thing", "floppy",
  ["Raw throughput says a 282-vertex hull is 11.8x slower than the sphere it "
   "approximates. But the scenes do not generate the same number of contacts.",
   "Per contact, <b>the box is cheaper than the sphere</b> &mdash; it only "
   "looked slow because it makes four times the contacts."],
  [F["collision_bars"]],
  chips=[("~5x", "cost per 23.5x hull", ""),
         ("sub-lin", "hull scaling", "ok")],
  bomb=("A gate that guards its own confound",
        ["A CI test asserts the box stays cheaper per contact, so the "
         "&ldquo;raw steps/s is the wrong metric&rdquo; argument fails loudly "
         "if its own example ever inverts."]),
  src="model/collision_cost.py")}


{study("The stiffness you asked for is not the one you got", "wrench",
  ["MuJoCo parameterises contact softness in <b>time</b>, not stiffness &mdash; "
   "and silently clamps the requested time constant to twice the timestep.",
   "Ask for a contact stiffer than your timestep supports and you quietly get "
   "the softer one. No warning is emitted. This finding turned up again, "
   "independently, in two later studies."],
  [F["contact_clamp"]],
  chips=[("0.1078", "mm, tc=0.0001", "bad"),
         ("0.1078", "mm, tc=0.02", "bad"),
         ("flat", "across 1000x mass", "ok")],
  bomb=("I predicted penetration would scale with load",
        ["It does not. The solver normalises by the contact's effective mass, "
         "so the load cancels exactly &mdash; 0.1078 mm at 0.1 kg and at 100 kg. "
         "The prediction is kept in the source next to the measurement that "
         "refuted it, because the reason it fails is the interesting part."]),
  src="model/contact_tuning.py")}

{study("Rotor inertia reflects as N squared", "wrench",
  ["The gearbox term everyone drops. A rotor's inertia appears at the joint "
   "multiplied by the square of the gear ratio.",
   "At N=100, a <b>2e-5</b> kg&middot;m&sup2; rotor contributes more inertia "
   "than the entire link it drives. Four actuator models validated against "
   "closed-form torque, all to 0.00% error."],
  [F["reflected_inertia"]],
  chips=[("0.00%", "torque error", "ok"),
         ("2.3x", "rotor vs link at N=100", "bad")],
  bomb=("A 196% discrepancy that was mine",
        ["I reported a large simulator disagreement that turned out to be a "
         "sign error in my own torque expression, plus a thin-rod inertia used "
         "for a capsule &mdash; 4.3% off. The gate now asks MuJoCo for the body "
         "inertia rather than assuming it."]),
  src="model/actuators.py")}

{study("The parameter you cannot identify", "magnifier",
  ["System identification over the same model. Three parameters recover; one "
   "has a trajectory sensitivity of <b>exactly zero</b>.",
   "That is the honest answer, not a failure: the experiment carries no "
   "information about it, so no optimiser can recover it. Reporting a fitted "
   "value would be inventing one."],
  [F["identifiability"]],
  chips=[("0.000", "damping_j1 sens.", "bad"),
         ("3", "of 4 identifiable", ""),
         ("35x", "better with true seed", "")],
  bomb=("Two hypotheses refuted in a row",
        ["I predicted richer excitation would improve the fit. It did not "
         "&mdash; 168.8% to 168.3%. I then concluded the parameters were "
         "unidentifiable, which was <b>also wrong</b>: seeding the optimiser "
         "with the true values fit 35x better, so the problem was a trapped "
         "optimiser, not missing information."]),
  src="model/sysid.py")}

{study("Newton, CG, PGS", "wrench",
  ["On a well-conditioned problem all three agree on the answer to 0.01 mm, "
   "which makes the speed difference free to take.",
   "<b>Newton is 14x faster than PGS</b> &mdash; the classic game-physics "
   "choice &mdash; at identical accuracy."],
  [F["solver_speed"]],
  chips=[("14x", "Newton over PGS", "ok"),
         ("0.01mm", "they all agree to", "ok")],
  bomb=("No solver rescues a bad mass ratio",
        ["On the 1000:1 stack they only change WHICH body fails. Newton drives "
         "the light block 49 mm into the floor; CG and PGS let the heavy one "
         "pass entirely through it. Two different wrong answers, neither "
         "better. With the iteration sweep, that closes it: a bad mass ratio "
         "is not a solver-tuning problem at all."]),
  src="model/solvers.py")}

{study("Where the time actually goes", "stopwatch",
  ["A C++ harness against the same model, with MuJoCo's per-phase timers "
   "enabled. Collision detection costs roughly <b>three times</b> the "
   "constraint solver.",
   "Which is why solver-iteration tuning was the wrong lever &mdash; something "
   "the stability study independently confirmed from the other direction."],
  [F["phase_profile"], F["scale_bars"]],
  chips=[("284x", "realtime, C++", "ok"),
         ("26.9%", "collision", ""),
         ("10.0%", "solve", "")],
  bomb=("MuJoCo's profiler is opt-in",
        ["Without installing <code>mjcb_time</code> the entire timer array "
         "reads zero &mdash; which looks exactly like every phase being free."]),
  src="cpp/sim_bench.cpp")}

</main>

<div class="wrap">
<footer>
  <section class="win">
    <div class="bar"><span class="box"></span><h3>About this page</h3>
      <span class="grow"></span></div>
    <div class="body">
      <div class="figwrap" style="margin-bottom:1rem">{F["corrections_tally"]}</div>
      <div class="ico-row">{I("floppy", 4)}{I("bomb", 4)}{I("check", 4)}</div>
      <p>Every figure is generated from the measured JSON by
      <code>tools/build_kare.py</code>, so the charts cannot drift from the
      studies. A separate CI gate checks the repository README's prose against
      the same data &mdash; it has caught three hand-typed roundings so far.</p>
      <p>Type is set the way the Macintosh set it: a chunky bitmap face for
      chrome and labels, a legible one for prose. Icons are 16x16, drawn a
      pixel at a time. The bomb is what a classic Mac showed when something
      went wrong, which is why it marks the corrections.</p>
      <p><b>Sixteen of the nineteen studies have a window here.</b> The other
      three are folded in rather than dropped: the ten failed gait attempts sit
      inside the trot window, and the stability-frontier sweep supplies the
      mass-ratio and iteration charts in two windows above. All nineteen are in
      the repository.</p>
      <p>One honest gap in the results themselves: the trot validates on Spot
      and not on ANYmal or A1, and both failures are diagnosed rather than
      smoothed over.</p>
      <div class="chips">
        <div class="chip"><b>19</b><span>studies</span></div>
        <div class="chip"><b>90</b><span>CI gates</span></div>
        <div class="chip"><b>22</b><span>commits</span></div>
        <div class="chip bad"><b>13</b><span>corrections</span></div>
      </div>
    </div>
  </section>
</footer>
</div>
"""

for _k, _first in (("grasp_slider", "3"), ("stack_slider", "1")):
    BODY = BODY.replace(f'<img alt="{"grasp" if _k.startswith("grasp") else "stack"}',
                        f'<img src="{SEQ[_k][_first][0]}" alt="'
                        + ("grasp" if _k.startswith("grasp") else "stack"), 1)

DATA_JS = ("<script>window.__SEQ__=" + demos.frames_json(SEQ)
           + ";window.__CONE__=" + _json.dumps(CONE, separators=(",", ":"))
           + ";</script>")
DEMO_JS = "<script>" + demos.PLAYER_JS + "</script>"

with open(OUT, "w") as f:
    f.write(HEAD + CSS + BODY + DATA_JS + HERO_JS + DEMO_JS)
print(f"wrote {OUT}  ({os.path.getsize(OUT)/1024/1024:.2f} MB)")
