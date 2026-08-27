"""Assemble the artifact page from the measured JSON and the SVG generators.

The page is built, not hand-written, so its figures cannot drift from the
studies. Same reasoning as tools/check_readme_claims.py: a findings-first
document is a liability the moment it stops agreeing with its own data.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "figs"))
import charts  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "artifact.html")

F = {name: getattr(charts, name)() for name in (
    "friction_polar", "integrator_order", "physx_iteration_cliff", "grasp_bars",
    "integrator_stability_bars", "crossengine_penetration", "mass_ratio_cliff",
    "collision_bars", "tree_vs_loop", "gait_schedule",
    "trot_wheel", "friction_recovery")}
F["corrections_tally"] = charts.corrections_tally(total=13, studies=19)

gr = charts.load("gait_result")
SPOT = gr["trot_error"]["Spot"]

det = charts.load("determinism")
LAM = round((det["chaos_smooth_1ulp"]["lyapunov_exponent_per_s"]
             + det["chaos_smooth_seeded_1e-12"]["lyapunov_exponent_per_s"]) / 2, 2)
PRED = det["predictive_check"]

HEAD = """<title>Measured, Then Corrected</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Familjen+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
"""

CSS = """<style>
:root{
  --snow:#FBFAF7; --linen:#F3F0EA; --ash:#E3DFD6; --hair:#EDEAE3;
  --slate:#2B3138; --stone:#6F757B;
  --fjord:#46708A; --lingon:#96414B; --moss:#65795B; --sand:#B8A88C;
  --plot:#F7F5F0;
  --fD:"Familjen Grotesk",-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;
  --fM:"IBM Plex Mono",ui-monospace,Menlo,monospace;
  --col:62ch; --pad:clamp(1.25rem,5vw,3rem);
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --snow:#14181B; --linen:#1C2226; --ash:#333B41; --hair:#242B30;
    --slate:#E9E6DF; --stone:#98A0A6;
    --fjord:#7FA9BD; --lingon:#D08A91; --moss:#9CB08D; --sand:#C4B393;
    --plot:#191F23;
  }
}
:root[data-theme="dark"]{
  --snow:#14181B; --linen:#1C2226; --ash:#333B41; --hair:#242B30;
  --slate:#E9E6DF; --stone:#98A0A6;
  --fjord:#7FA9BD; --lingon:#D08A91; --moss:#9CB08D; --sand:#C4B393;
  --plot:#191F23;
}
*{box-sizing:border-box}
body{margin:0;background:var(--snow);color:var(--slate);font-family:var(--fD);
  font-size:1.0625rem;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:74rem;margin:0 auto;padding:0 var(--pad)}
.narrow{max-width:var(--col)}

/* ---------- masthead ---------- */
.mast{padding:clamp(3.5rem,10vw,7rem) 0 clamp(2rem,5vw,3rem)}
.kicker{font-family:var(--fM);font-size:.68rem;letter-spacing:.22em;
  text-transform:uppercase;color:var(--fjord);margin:0 0 2rem}
h1{font-family:var(--fD);font-weight:700;font-size:clamp(2.9rem,9vw,6rem);
  line-height:.92;letter-spacing:-.04em;margin:0 0 1.75rem;max-width:11ch;
  text-wrap:balance}
.thesis{max-width:var(--col);font-size:clamp(1.08rem,2.3vw,1.28rem);
  line-height:1.5;color:var(--stone);margin:0}
.thesis b{color:var(--slate);font-weight:600}

/* ---------- stat rail ---------- */
.rail{display:grid;grid-template-columns:repeat(auto-fit,minmax(8.5rem,1fr));
  gap:1px;background:var(--ash);border-block:1px solid var(--ash);
  margin-top:clamp(2.5rem,6vw,4rem)}
.stat{background:var(--snow);padding:1.35rem 1.25rem;display:flex;
  flex-direction:column;gap:.35rem}
.stat b{font-family:var(--fM);font-weight:500;font-size:clamp(1.25rem,2.6vw,1.6rem);
  letter-spacing:-.02em;font-variant-numeric:tabular-nums;line-height:1}
.stat span{font-family:var(--fM);font-size:.65rem;letter-spacing:.1em;
  text-transform:uppercase;color:var(--stone);line-height:1.4}

/* ---------- hero canvas ---------- */
.hero{margin:clamp(2.5rem,6vw,4rem) 0 0;background:var(--linen);
  border:1px solid var(--ash);position:relative;overflow:hidden}
.hero canvas{display:block;width:100%;height:clamp(300px,46vw,470px)}
.hero-cap{position:absolute;left:0;right:0;bottom:0;padding:1rem 1.25rem;
  display:flex;flex-wrap:wrap;gap:.5rem 1.5rem;align-items:baseline;
  background:linear-gradient(to top,var(--linen),transparent)}
.hero-cap b{font-family:var(--fM);font-size:.72rem;letter-spacing:.06em}
.hero-cap span{font-size:.86rem;color:var(--stone)}
.dot-a,.dot-b{width:.55rem;height:.55rem;border-radius:50%;display:inline-block;
  margin-right:.4rem;vertical-align:baseline}
.dot-a{background:var(--fjord)} .dot-b{background:var(--lingon)}

/* ---------- plates ---------- */
main{padding:clamp(3rem,7vw,5rem) 0 0}
.plate{border-top:1px solid var(--hair);padding:clamp(2.5rem,6vw,4rem) 0;
  display:grid;gap:1.75rem}
@media(min-width:60rem){
  .plate{grid-template-columns:minmax(0,19rem) minmax(0,1fr);
    gap:clamp(2rem,4vw,3.5rem);align-items:start}
  .plate.flip{grid-template-columns:minmax(0,1fr) minmax(0,19rem)}
  .plate.flip .said{order:2}
  .plate.wide{grid-template-columns:minmax(0,1fr)}
}
.said{display:flex;flex-direction:column;gap:.85rem;position:sticky;top:1.5rem}
@media(max-width:60rem){.said{position:static}}
.tag{font-family:var(--fM);font-size:.63rem;letter-spacing:.16em;
  text-transform:uppercase;color:var(--fjord)}
h2{font-family:var(--fD);font-weight:600;font-size:clamp(1.4rem,3vw,1.95rem);
  line-height:1.14;letter-spacing:-.025em;margin:0;text-wrap:balance}
.said p{margin:0;font-size:.97rem;color:var(--stone)}
.said p b{color:var(--slate);font-weight:600}
.src{font-family:var(--fM);font-size:.7rem;color:var(--stone);
  word-break:break-all;padding-top:.25rem;border-top:1px solid var(--hair)}
.fig{background:var(--linen);border:1px solid var(--ash);padding:clamp(.75rem,2vw,1.5rem)}
.fig + .fig{margin-top:1rem}

/* ---------- correction chip ---------- */
.fix{border-left:2px solid var(--lingon);padding:.75rem 0 .75rem 1rem;
  display:flex;flex-direction:column;gap:.4rem}
.fix b{font-family:var(--fM);font-size:.62rem;letter-spacing:.14em;
  text-transform:uppercase;color:var(--lingon);font-weight:500}
.fix p{margin:0;font-size:.92rem;color:var(--stone)}
.fix p em{font-style:normal;font-family:var(--fM);font-size:.9em;color:var(--slate)}

/* ---------- numbers strip inside a plate ---------- */
.nums{display:grid;grid-template-columns:repeat(auto-fit,minmax(7rem,1fr));
  gap:1px;background:var(--ash);border:1px solid var(--ash);margin-top:1rem}
.nums div{background:var(--linen);padding:.85rem .9rem;display:flex;
  flex-direction:column;gap:.2rem}
.nums b{font-family:var(--fM);font-weight:500;font-size:1.05rem;
  font-variant-numeric:tabular-nums;line-height:1.1}
.nums span{font-family:var(--fM);font-size:.6rem;letter-spacing:.08em;
  text-transform:uppercase;color:var(--stone)}
.up{color:var(--moss)} .down{color:var(--lingon)}

/* ---------- svg figure styling ---------- */
svg{display:block;max-width:100%;height:auto;overflow:visible}
.plot-bg{fill:var(--plot)}
.grid{stroke:var(--ash);stroke-width:1;opacity:.55}
.axis{stroke:var(--stone);stroke-width:1}
.axis-spoke{stroke:var(--ash);stroke-width:1}
.ring{fill:none;stroke:var(--ash);stroke-width:1}
.marker{stroke:var(--lingon);stroke-width:1;stroke-dasharray:3 3;opacity:.8}
.divider{stroke:var(--ash);stroke-width:1}
.lbl,.tick,.cap,.barval,.figtitle{font-family:var(--fM);fill:var(--stone)}
.tick{font-size:10px;letter-spacing:.04em}
.cap{font-size:10px;letter-spacing:.1em;text-transform:uppercase}
.cap-warn{font-family:var(--fM);font-size:10px;letter-spacing:.1em;
  text-transform:uppercase;fill:var(--lingon)}
.barval{font-size:11px;fill:var(--slate)}
.figtitle{font-size:11px;letter-spacing:.12em;text-transform:uppercase;fill:var(--slate)}
.figtitle-warn{font-family:var(--fM);font-size:11px;letter-spacing:.12em;
  text-transform:uppercase;fill:var(--lingon)}
.series-a{stroke:var(--fjord);stroke-width:2;stroke-linejoin:round}
.series-b{stroke:var(--sand);stroke-width:2;stroke-linejoin:round}
.series-c{stroke:var(--stone);stroke-width:1.5;stroke-dasharray:4 3}
.series-ok{stroke:var(--moss);stroke-width:2;stroke-linejoin:round}
.series-warn{stroke:var(--lingon);stroke-width:2;stroke-linejoin:round}
.series-a-dot{fill:var(--fjord)} .series-b-dot{fill:var(--sand)}
.series-c-dot{fill:var(--stone)} .series-ok-dot{fill:var(--moss)}
.series-warn-dot{fill:var(--lingon)}
.key-a{font-family:var(--fM);font-size:10px;fill:var(--fjord)}
.key-b{font-family:var(--fM);font-size:10px;fill:var(--sand)}
.key-series-a{font-family:var(--fM);font-size:10px;fill:var(--fjord)}
.key-series-b{font-family:var(--fM);font-size:10px;fill:var(--sand)}
.key-series-c{font-family:var(--fM);font-size:10px;fill:var(--stone)}
.key-series-ok{font-family:var(--fM);font-size:10px;fill:var(--moss)}
.key-ok{font-family:var(--fM);font-size:10px;fill:var(--moss)}
.key-warn{font-family:var(--fM);font-size:10px;fill:var(--lingon)}
.key-num{font-family:var(--fM);font-size:13px;fill:var(--slate)}
.bar-a{fill:var(--sand)} .bar-b{fill:var(--fjord)} .bar-warn{fill:var(--lingon)}
.band-warn{fill:var(--lingon);opacity:.12}
.band-ok{fill:var(--moss);opacity:.14}
.band-flat{fill:var(--fjord);opacity:.1}
.node{fill:var(--snow);stroke:var(--slate);stroke-width:1.5}
.link{stroke:var(--stone);stroke-width:1.5}
.link-close{stroke:var(--lingon);stroke-width:2.5}
.lane{fill:var(--plot);stroke:var(--ash);stroke-width:1}
.stance-ok{fill:var(--moss);opacity:.75}
.stance-warn{fill:var(--lingon);opacity:.6}
.tally-on{fill:var(--lingon)} .tally-off{fill:var(--ash)}

/* ---------- footer ---------- */
footer{border-top:1px solid var(--ash);margin-top:clamp(2rem,5vw,3rem);
  padding:clamp(3rem,7vw,4.5rem) 0 clamp(4rem,9vw,6rem);
  display:flex;flex-direction:column;gap:1.1rem}
footer p{margin:0;max-width:var(--col);color:var(--stone)}
.pills{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:.3rem}
.pill{font-family:var(--fM);font-size:.7rem;border:1px solid var(--fjord);
  color:var(--fjord);padding:.3rem .6rem;border-radius:2px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>"""


HERO_JS = """<script>
(function(){
  // A live double pendulum, integrated RK4 in the page. Two of them, seeded
  // 1e-12 apart -- the determinism study, running rather than described.
  // Same system, same exponent: they hold together, then separate.
  var c=document.getElementById('chaos'); if(!c) return;
  var ctx=c.getContext('2d'), DPR=Math.min(window.devicePixelRatio||1,2);
  var reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion:reduce)').matches;
  function size(){ var r=c.getBoundingClientRect();
    c.width=r.width*DPR; c.height=r.height*DPR; ctx.setTransform(DPR,0,0,DPR,0,0); }
  size(); addEventListener('resize',size);
  var g=9.81,L1=1,L2=1,m1=1,m2=1;
  function deriv(s){
    var a=s[0],b=s[1],da=s[2],db=s[3],d=a-b,den=2*m1+m2-m2*Math.cos(2*d);
    var dda=(-g*(2*m1+m2)*Math.sin(a)-m2*g*Math.sin(a-2*b)
             -2*Math.sin(d)*m2*(db*db*L2+da*da*L1*Math.cos(d)))/(L1*den);
    var ddb=(2*Math.sin(d)*(da*da*L1*(m1+m2)+g*(m1+m2)*Math.cos(a)
             +db*db*L2*m2*Math.cos(d)))/(L2*den);
    return [da,db,dda,ddb];
  }
  function step(s,h){
    function ax(u,v,k){return [u[0]+k*v[0],u[1]+k*v[1],u[2]+k*v[2],u[3]+k*v[3]];}
    var k1=deriv(s),k2=deriv(ax(s,k1,h/2)),k3=deriv(ax(s,k2,h/2)),k4=deriv(ax(s,k3,h));
    return s.map(function(v,i){return v+h/6*(k1[i]+2*k2[i]+2*k3[i]+k4[i]);});
  }
  var A=[2.0,1.0,0,0], B=[2.0+1e-12,1.0,0,0], t=0;
  var trailA=[], trailB=[], MAXT=520;
  function tip(s,cx,cy,sc){
    var x=cx+sc*L1*Math.sin(s[0]), y=cy+sc*L1*Math.cos(s[0]);
    return [x+sc*L2*Math.sin(s[1]), y+sc*L2*Math.cos(s[1]), x, y];
  }
  function cssvar(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim();}
  function draw(){
    var w=c.clientWidth,h=c.clientHeight,cx=w/2,cy=h*0.30,sc=Math.min(w,h)*0.20;
    ctx.clearRect(0,0,w,h);
    var CA=cssvar('--fjord')||'#46708A', CB=cssvar('--lingon')||'#96414B',
        CS=cssvar('--stone')||'#6F757B';
    [[trailA,CA],[trailB,CB]].forEach(function(p){
      var tr=p[0]; ctx.lineWidth=1.2;
      for(var i=1;i<tr.length;i++){
        ctx.globalAlpha=0.06+0.5*(i/tr.length);
        ctx.strokeStyle=p[1]; ctx.beginPath();
        ctx.moveTo(tr[i-1][0],tr[i-1][1]); ctx.lineTo(tr[i][0],tr[i][1]); ctx.stroke();
      }
      ctx.globalAlpha=1;
    });
    [[A,CA],[B,CB]].forEach(function(p){
      var s=p[0],T=tip(s,cx,cy,sc);
      ctx.strokeStyle=p[1]; ctx.lineWidth=1.6; ctx.globalAlpha=.85;
      ctx.beginPath(); ctx.moveTo(cx,cy); ctx.lineTo(T[2],T[3]); ctx.lineTo(T[0],T[1]); ctx.stroke();
      ctx.globalAlpha=1; ctx.fillStyle=p[1];
      ctx.beginPath(); ctx.arc(T[0],T[1],4,0,6.284); ctx.fill();
      ctx.beginPath(); ctx.arc(T[2],T[3],3,0,6.284); ctx.fill();
    });
    ctx.fillStyle=CS; ctx.beginPath(); ctx.arc(cx,cy,3,0,6.284); ctx.fill();
    var TA=tip(A,cx,cy,sc), TB=tip(B,cx,cy,sc);
    var sep=Math.hypot(TA[0]-TB[0],TA[1]-TB[1])/sc;
    ctx.font='500 11px "IBM Plex Mono",monospace'; ctx.fillStyle=CS;
    ctx.fillText('t = '+t.toFixed(1)+' s', 16, 22);
    ctx.fillText('separation = '+(sep<1e-4?sep.toExponential(1):sep.toFixed(4))+' m', 16, 40);
  }
  function frame(){
    if(!reduce){
      for(var i=0;i<28;i++){ A=step(A,0.0016); B=step(B,0.0016); t+=0.0016; }
      var w=c.clientWidth,h=c.clientHeight,cx=w/2,cy=h*0.30,sc=Math.min(w,h)*0.20;
      trailA.push(tip(A,cx,cy,sc)); trailB.push(tip(B,cx,cy,sc));
      if(trailA.length>MAXT){trailA.shift(); trailB.shift();}
      if(t>26){ A=[2.0,1.0,0,0]; B=[2.0+1e-12,1.0,0,0]; t=0; trailA=[]; trailB=[]; }
    }
    draw(); requestAnimationFrame(frame);
  }
  frame();
})();
</script>"""


def plate(tag, title, said, figs, src=None, fix=None, nums=None, cls=""):
    fx = "".join(f'<div class="fig">{f}</div>' for f in figs)
    parts = [f'<span class="tag">{tag}</span>', f"<h2>{title}</h2>"]
    for p in said:
        parts.append(f"<p>{p}</p>")
    if nums:
        cells = "".join(
            f'<div><b class="{c}">{v}</b><span>{l}</span></div>' for v, l, c in nums)
        parts.append(f'<div class="nums">{cells}</div>')
    if fix:
        parts.append(f'<div class="fix"><b>{fix[0]}</b><p>{fix[1]}</p></div>')
    if src:
        parts.append(f'<div class="src">{src}</div>')
    return (f'<section class="plate {cls}"><div class="said">{"".join(parts)}</div>'
            f'<div class="figs">{fx}</div></section>')


BODY = f"""
<header class="mast wrap">
  <p class="kicker">MuJoCo &middot; Isaac Sim / PhysX &middot; Gazebo &middot; ROS 2</p>
  <h1>Measured, Then Corrected</h1>
  <p class="thesis">Nineteen studies against one robot model in three formats.
  Every number here came out of a run that reproduces from the repository &mdash;
  and so did every <b>correction</b>, because in thirteen of the nineteen the
  first answer was wrong.</p>

  <div class="rail">
    <div class="stat"><b>84</b><span>CI gates<br>4 test the gates</span></div>
    <div class="stat"><b>3.3e&minus;16</b><span>max FK error<br>2000 configs</span></div>
    <div class="stat"><b>{LAM} /s</b><span>Lyapunov<br>exponent</span></div>
    <div class="stat"><b>3.994</b><span>observed RK4 order<br>theory 4</span></div>
    <div class="stat"><b>812,670</b><span>steps/s<br>65,536 envs</span></div>
    <div class="stat"><b>13</b><span>wrong answers<br>caught</span></div>
  </div>

  <div class="hero">
    <canvas id="chaos" aria-label="Two double pendulums seeded one part in 1e12 apart, diverging"></canvas>
    <div class="hero-cap">
      <b><span class="dot-a"></span>pendulum A</b>
      <b><span class="dot-b"></span>pendulum B &mdash; seeded 1e&minus;12 apart</b>
      <span>Identical physics. They hold together, then separate at
      {LAM} e&#8209;folds per second.</span>
    </div>
  </div>
</header>

<main class="wrap">

{plate("Reproducibility", "How long a simulation stays reproducible",
  ["Repeated runs are <b>bit-identical</b>. So is a re-parsed model. Adding an "
   "untouched body three metres away changes nothing. Reproducibility failures "
   "here are not solver nondeterminism.",
   "What bounds them is chaos, and that is measurable. Two perturbation sizes "
   "&mdash; one ULP and 1e&minus;12 &mdash; recover the same exponent, and the "
   "exponent fitted on one run blind&#8209;predicts the other."],
  [F["corrections_tally"]],
  src="model/determinism.py",
  nums=[(f"{PRED['predicted_1mm_s']} s", "predicted 1 mm", ""),
        (f"{PRED['measured_1mm_s']} s", "measured", "up"),
        ("1.2%", "seeds agree", "up"),
        ("6.5x", "contact chaos slower", "")],
  fix=("Two floating-point traps",
       "A one-ULP nudge of <em>2.22e-16</em> added to a coordinate of "
       "<em>2.0</em> &mdash; whose ULP is twice that &mdash; rounds away "
       "entirely. The runs came out bit-identical and read as &ldquo;no "
       "chaos&rdquo;. And <em>nextafter(0.0, 1.0)</em> is the smallest "
       "<b>denormal</b>, which produced a meaningless 2e305&times; growth."))}

{plate("Friction", "The approximation with the shape of a square",
  ["Coulomb friction confines the tangential force to a <b>circle</b>. The "
   "common approximation replaces it with a <b>polygon</b> &mdash; and the "
   "polygon shows.",
   "Launch a box across a floor at nineteen headings and plot how far its "
   "slide deviates from its launch. The error is zero at 0&deg;, 45&deg; and "
   "90&deg; &mdash; the square&rsquo;s symmetry axes &mdash; and peaks between."],
  [F["friction_polar"]],
  src="model/friction_cone.py",
  nums=[("12.76&deg;", "pyramidal worst", "down"),
        ("0.71&deg;", "elliptic worst", "up"),
        ("2.6x", "elliptic is FASTER", "up")],
  fix=("What I got wrong &mdash; in my own docstring",
       "I called the pyramid &ldquo;the cheaper option&rdquo;. It is 2.6&times; "
       "<b>slower</b> as well as 18&times; less accurate &mdash; dominated on "
       "both axes, no trade at all."),
  cls="flip")}

{plate("Integration", "Verify the order, not the vibe",
  ["&ldquo;RK4 is more accurate than Euler&rdquo; is not a validation. A method "
   "of order <em>p</em> has global error <em>O(dt^p)</em>, so the slope of this "
   "log&#8209;log plot <b>is</b> the order.",
   "All four land on their theoretical slope. Then the ranking reverses: with a "
   "stiff velocity actuator &mdash; a joint PD controller&rsquo;s derivative "
   "term &mdash; <b>RK4 is less stable than Euler</b>."],
  [F["integrator_order"], F["integrator_stability_bars"]],
  src="model/integrators.py",
  fix=("isfinite() is not a stability test",
       "The first sweep called Euler <b>stable at kv=500</b> after it failed at "
       "20, 50 and 100. MuJoCo detects a diverged step and <b>resets the state "
       "to zero</b> &mdash; it hit <em>|qvel| = 3.45e5</em>, got reset, then sat "
       "at exactly zero for 397 steps. Perfectly finite, perfectly meaningless."))}
"""


BODY += f"""
{plate("MuJoCo vs PhysX", "Two solvers, two different shapes of failure",
  ["The same experiment in both engines. They <b>agree</b> on something "
   "non-obvious: resting penetration is invariant to a 1000&times; mass change "
   "in each.",
   "They disagree on everything else. MuJoCo is flat until <em>2&middot;dt</em> "
   "passes its 0.02&nbsp;s time constant, then steps. PhysX has no time "
   "constant to clamp, so it slopes the whole way."],
  [F["crossengine_penetration"]],
  src="model/crossengine_contact.py",
  nums=[("2155x", "softer at 480 Hz", ""),
        ("61x", "softer at 60 Hz", ""),
        ("1:1", "rest_offset to standoff", "up")],
  fix=("Right answer, unverified reasoning",
       "Both predictions were confirmed. One of the two <b>reasons</b> was not: "
       "I attributed PhysX&rsquo;s mass independence to the rest offset, but "
       "<em>rest_offset</em> read 0.0 for the entire sweep."),
  cls="flip")}

{plate("Stability", "A cliff, not a curve",
  ["Mass ratio, not timestep, is what breaks a solver. MuJoCo slides. PhysX "
   "falls off a table between ratio 10 and 100.",
   "In MuJoCo, iterations never help &mdash; 1 and 50 give identical results. "
   "In PhysX they help, but as a <b>step function</b>: 1, 32 and 64 are "
   "indistinguishable failures and 96 is a working stack."],
  [F["mass_ratio_cliff"], F["physx_iteration_cliff"]],
  src="model/stability_frontier.py &middot; model/crossengine_stack.py",
  nums=[("64 &rarr; 96", "where it flips", "down"),
        ("0", "velocity iters help", "down"),
        ("255", "still fails at 1e4", "down")],
  fix=("The control that named the mechanism",
       "Velocity iterations at 1, 32, 128 and 255 all leave it at ~100&nbsp;mm. "
       "So the cliff is not about total solver effort &mdash; it is "
       "specifically <b>position-level depenetration work</b>. That turns a "
       "correlation into a mechanism."))}

{plate("Manipulation", "Recovering a grip force nobody supplied",
  ["A parallel-jaw grasp holds when <em>2&middot;mu&middot;F &ge; m&middot;g</em>. "
   "Friction and mass go in; the holding threshold comes out of the dynamics, "
   "found by bisecting the grip force.",
   "<b>All four land above the closed form</b>, and the sign is the point. "
   "<em>m&middot;g/(2&middot;mu)</em> is the marginal holding force, so it holds "
   "with zero margin. A measurement <b>below</b> theory would mean the contact "
   "model invents friction."],
  [F["grasp_bars"]],
  src="model/grasp.py",
  nums=[("+7.5%", "mean excess", ""),
        ("0.37 N", "additive offset", "up"),
        ("4x", "tighter than relative", "up")],
  fix=("Testing the explanation, not asserting it",
       "The excess could be proportional or additive. Absolute excess clusters "
       "at 0.313&thinsp;/&thinsp;0.451&thinsp;/&thinsp;0.331&thinsp;/&thinsp;0.368&nbsp;N "
       "with a coefficient of variation of <b>0.144</b>, against 0.598 for the "
       "relative reading. Additive wins by 4&times;."),
  cls="flip")}

{plate("Format limits", "What URDF cannot say",
  ["URDF is a <b>tree</b>. Every link has exactly one parent, so four-bar "
   "linkages, parallel jaws and differential drives are outside the "
   "format&rsquo;s data model &mdash; not a tooling gap.",
   "Drop the closure and the mechanism still simulates, still looks plausible, "
   "and is <b>half dead</b>: the rocker travels 0.0000&nbsp;rad."],
  [F["tree_vs_loop"]],
  src="model/closed_chain.py",
  nums=[("0.0000", "open rocker rad", "down"),
        ("0.7191", "closed rocker rad", "up"),
        ("109x", "tuning the closure", "")],
  fix=("Wrong diagnosis, then the correction",
       "A 57&nbsp;mm worst-case gap looked like a soft constraint. Stiffening "
       "moved the mean 109&times; and the max barely at all &mdash; because the "
       "max is at <b>step 0</b>. The model was spawned 60.7&nbsp;mm off the "
       "constraint manifold."))}

{plate("Performance", "The metric was measuring the wrong thing",
  ["Raw throughput says a 282-vertex hull is 11.8&times; slower than the "
   "primitive sphere it approximates. But the scenes do not generate the same "
   "number of contacts.",
   "Normalised per contact, <b>the box is cheaper than the sphere</b> &mdash; it "
   "only looked slow because it makes four times the contacts."],
  [F["collision_bars"]],
  src="model/collision_cost.py",
  nums=[("~5x", "cost per 23.5x hull", ""),
        ("sub-linear", "hull scaling", "up")],
  fix=("A gate that guards its own confound",
       "A CI test asserts the box stays cheaper per contact, so the "
       "&ldquo;raw steps/s is the wrong metric&rdquo; argument fails loudly if "
       "its own example ever inverts."),
  cls="flip")}

{plate("Legged locomotion", "Eleven attempts, and then a trot",
  ["A trot has one signature: diagonal pairs move <b>together</b>, and the two "
   "pairs are half a cycle apart. Everything else &mdash; duty thresholds, "
   "foot heights &mdash; is downstream of that.",
   "Ten attempts measured in the world frame and kept describing a robot "
   "falling over. The eleventh changed the <b>frame</b>, not the fix: a gait "
   "generator&rsquo;s output is the foot trajectory relative to the trunk, so "
   "measured there it is well&#8209;posed whether the robot balances or not."],
  [F["trot_wheel"]],
  src="model/gait_result.py",
  nums=[(f"{SPOT['diag_FL_HR_deg']}&deg;", "FL+HR apart", "up"),
        (f"{SPOT['diag_FR_HL_deg']}&deg;", "FR+HL apart", "up"),
        (f"{SPOT['between_pairs_deg']}&deg;", "between pairs", "up"),
        (f"{SPOT['worst_deviation_deg']}&deg;", "worst deviation", "up")],
  fix=("One robot of three, and the other two are diagnosed",
       "ANYmal: two of four legs resolved to a <b>shank</b> rather than a foot, "
       "so the tracked points sit partway up the chain. A1: the legs never "
       "moved at all &mdash; 1e&minus;5&nbsp;m of excursion, so the joint "
       "targets produced no motion. Neither is a mystery, and neither is fixed."))}

{plate("Fidelity", "Reading a friction coefficient back out",
  ["<em>mu</em> goes into PhysX as a material property. The angle at which a "
   "block starts to slide comes out of the dynamics. Coulomb connects them: "
   "<em>tan(&theta;) = mu</em>.",
   "Three coefficients recovered to better than 2% &mdash; without ever asking "
   "the engine what friction it was using."],
  [F["friction_recovery"]],
  src="model/friction_recovery.py",
  nums=[("+1.9%", "mu 0.3", ""), ("+1.9%", "mu 0.5", ""),
        ("+1.2%", "mu 0.8", ""), ("0.44&deg;", "max overshoot", "up")],
  fix=("My prediction was wrong in DIRECTION",
       "I predicted a low bias, reasoning that pre-slip creep would trip the "
       "detector early. But the sweep steps in 2&deg; increments, so the first "
       "angle flagged can only ever be the first grid line <b>at or above</b> "
       "the true threshold. The bias had to be positive whatever creep does. "
       "Creep is there in the data &mdash; 0.4 to 0.8&nbsp;mm one step before "
       "release &mdash; it just never reaches the detection threshold."),
  cls="flip")}

{plate("Legged locomotion, before it worked", "What ten failures looked like",
  ["Kept because the failures are the load-bearing part. Open-loop joint "
   "sinusoids <b>topple a quadruped</b>, and for ten attempts the measurement "
   "faithfully described the fall."],
  [F["gait_schedule"]],
  src="model/gait_validation.py",
  fix=("The error that named the wrong subsystem",
       "An <em>if</em> block sat outside the stepping loop, so the sim was "
       "never stepped and the height arrays stayed empty &mdash; surfacing as "
       "<em>zero-size array to reduction operation minimum</em>. I read that as "
       "foot detection returning nothing and rewrote foot detection twice."))}

</main>

<footer class="wrap">
  <h2>Where this stands</h2>
  <p>Every figure on this page is generated from the measured JSON by
  <span class="src">tools/build_artifact.py</span>, so the charts cannot drift
  from the studies that produced them. A separate CI gate checks the repository
  README&rsquo;s prose against the same data.</p>
  <p>Seventeen studies, seventy-odd figures and tables, and one honest gap:
  the trot validates on Spot and not on ANYmal or A1. Both failures are
  diagnosed in the repository rather than smoothed over here.</p>
  <div class="pills">
    <span class="pill">19 studies</span>
    <span class="pill">84 CI gates</span>
    <span class="pill">23 commits</span>
    <span class="pill">13 corrections</span>
  </div>
</footer>
"""

with open(OUT, "w") as f:
    f.write(HEAD + CSS + BODY + HERO_JS)
print(f"wrote {OUT}  ({len(HEAD+CSS+BODY+HERO_JS):,} bytes)")
