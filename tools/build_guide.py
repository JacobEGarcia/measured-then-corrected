"""Build the beginner's guide, in the same Macintosh idiom as the main site.

The guide teaches from zero toward one specific interview. Every lesson ends
with what the interviewer is actually probing for, because a definition you
can recite is worth much less than knowing why the question gets asked.

Where a claim was measured in this repository, the guide shows the real chart
and says so. Where a demo is a teaching toy, it says that too.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "figs"))
import charts, pixel, anim, edu, demos, edu_demos   # noqa: E402
import json as _json

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "docs", "guide.html")

E = {n: anim.animate_svg(getattr(edu, n)()) for n in (
    "sim_loop", "joint_types", "dof_ladder", "friction_cone_explainer",
    "pd_control", "sim2real", "simulator_picker")}
C = {n: anim.animate_svg(getattr(charts, n)()) for n in (
    "friction_polar", "integrator_order", "integrator_stability_bars",
    "one_spec_three_formats", "reflected_inertia", "identifiability",
    "solver_speed", "phase_profile", "scale_bars", "contact_clamp",
    "crossengine_penetration", "trot_wheel", "grasp_bars", "collision_bars",
    "mass_ratio_cliff", "chaos_divergence")}
SEQ = charts.load("render_frames")


def I(n, px=4):
    if n in pixel.ANIM:
        return anim.animated_icon(pixel.ANIM[n], px=px, title=n, cls=f"ico-{n}")
    return pixel.icon(n, px=px)


# Reuse the Macintosh stylesheet. build_kare.py writes its output at module
# level, so importing it would emit a file as a side effect -- lift the CSS out
# of its source with the ast module instead, which is exact and side-effect
# free.
import ast as _ast


def _const_from(path, name):
    tree = _ast.parse(open(path).read())
    for node in tree.body:
        if isinstance(node, _ast.Assign):
            for t in node.targets:
                if isinstance(t, _ast.Name) and t.id == name:
                    return _ast.literal_eval(node.value)
    raise KeyError(f"{name} not found in {path}")


BASE_CSS = _const_from(os.path.join(HERE, "build_kare.py"), "CSS")

GUIDE_CSS = """<style>
.lesson{counter-increment:lesson}
.lnum{font-family:var(--fC);font-size:.6rem;color:var(--paper);
  background:var(--blue);padding:.15rem .4rem;margin-right:.4rem}
.ask{border:2px solid var(--rule);background:var(--paper);margin-top:.6rem}
.ask .hd{display:flex;align-items:center;gap:.5rem;padding:.4rem .5rem;
  border-bottom:2px solid var(--rule);background:var(--blue)}
.ask .hd b{font-family:var(--fC);font-size:.6rem;color:#FFF;text-transform:uppercase}
.ask p{margin:0;padding:.65rem .6rem;font-size:.89rem;color:var(--stone)}
.ask p+p{padding-top:0}
.ask em{font-style:normal;color:var(--ink);font-weight:600}
.plain{border-left:4px solid var(--yellow);padding:.5rem 0 .5rem .8rem;
  margin:.5rem 0;font-size:.95rem}
.plain b{font-family:var(--fC);font-size:.6rem;display:block;margin-bottom:.2rem;
  color:var(--stone);text-transform:uppercase}
.qa{border-top:2px solid var(--rule)}
.qa dt{font-family:var(--fC);font-size:.7rem;padding:.6rem .6rem .2rem;
  color:var(--ink)}
.qa dd{margin:0;padding:0 .6rem .6rem;font-size:.9rem;color:var(--stone)}
.qa dd b{color:var(--ink)}
.toc{display:grid;grid-template-columns:repeat(auto-fit,minmax(11rem,1fr));
  gap:0;border-top:2px solid var(--rule);border-left:2px solid var(--rule)}
.toc a{border-right:2px solid var(--rule);border-bottom:2px solid var(--rule);
  padding:.5rem .6rem;font-family:var(--fC);font-size:.58rem;color:var(--ink);
  text-decoration:none;display:flex;gap:.4rem;align-items:center}
.toc a:hover,.toc a:focus-visible{background:var(--yellow);outline:none}
.toc span{color:var(--blue)}
</style>"""


LESSONS = []


def lesson(num, icon, title, plain, body, figs=(), ask=None, demo=""):
    """plain: the one-sentence version for someone who knows nothing.
       body:  paragraphs.
       ask:   (question the interviewer is really asking, what to say)."""
    anchor = f"L{num}"
    left = [f'<div class="ico-row">{I(icon, 5)}</div>',
            f'<h2><span class="lnum">{num:02d}</span>{title}</h2>']
    if plain:
        left.append(f'<div class="plain"><b>In plain English</b>{plain}</div>')
    for p in body:
        left.append(f"<p>{p}</p>")
    if ask:
        left.append(f'<div class="ask"><div class="hd">{I("question", 3)}'
                    f'<b>What they are really asking</b></div>'
                    f'<p><em>{ask[0]}</em></p><p>{ask[1]}</p></div>')
    right = "".join(f'<div class="figwrap">{f}</div>' for f in figs) + demo
    LESSONS.append((num, title, icon))
    return (f'<section class="win lesson" id="{anchor}">'
            f'<div class="bar"><span class="box"></span>'
            f'<h3>{num:02d} &nbsp; {title}</h3><span class="grow"></span></div>'
            f'<div class="body"><div class="grid2">'
            f'<div class="say">{"".join(left)}</div><div>{right}</div>'
            f'</div></div></section>')


PD_DEMO = '''
<div class="demo" style="margin-top:.75rem">
  <canvas id="pd" style="height:250px" aria-label="a joint driven to a target by a PD controller"></canvas>
  <div class="ctl">
    <label id="kpv">kp = 20</label>
    <input type="range" id="kp" min="0" max="120" step="1" value="20" aria-label="proportional gain">
  </div>
  <div class="ctl" style="border-top:0">
    <label id="kdv">kd = 6</label>
    <input type="range" id="kd" min="0" max="40" step="1" value="6" aria-label="derivative gain">
    <span id="pdverdict" class="verdict v-ok">MOVING</span>
  </div>
  <div class="note">TRY THIS: set kd to 0 and it rings forever. Set kp low and
  it never gets there. The green dashes are the target. This is a real
  second-order system, but it is a teaching toy, not a measurement.</div>
</div>'''

FK_DEMO = '''
<div class="demo" style="margin-top:.75rem">
  <canvas id="fk" style="height:250px" aria-label="a two link arm posed by two joint angles"></canvas>
  <div class="ctl">
    <label>joint 1</label>
    <input type="range" id="j1" min="-180" max="180" step="1" value="35" aria-label="joint one angle">
  </div>
  <div class="ctl" style="border-top:0">
    <label>joint 2</label>
    <input type="range" id="j2" min="-180" max="180" step="1" value="-60" aria-label="joint two angle">
    <span id="fkout" class="verdict v-ok">tip</span>
  </div>
  <div class="note">Two angles in, one tip position out. That is forward
  kinematics. Notice you can reach the same point with more than one pose
  &mdash; that is exactly why the reverse problem is harder.</div>
</div>'''

DT_DEMO = '''
<div class="demo" style="margin-top:.75rem">
  <canvas id="dt" style="height:250px" aria-label="an orbit integrated at the chosen timestep"></canvas>
  <div class="ctl">
    <label id="dtv">dt = 0.010 s</label>
    <input type="range" id="dtr" min="2" max="120" step="1" value="10" aria-label="timestep">
    <span id="dten" class="verdict v-ok">energy drift</span>
  </div>
  <div class="note">A planet orbiting a sun. The physics conserves energy
  exactly; the INTEGRATOR does not. Push the timestep up and watch the orbit
  spiral outward as energy is invented from nothing.</div>
</div>'''


PART1 = "".join([

lesson(1, "mac", "What a simulator actually is",
  "A program that repeatedly asks &ldquo;given where everything is and what "
  "forces act on it, where will everything be 2 milliseconds from now?&rdquo; "
  "&mdash; then does that a thousand times a second.",
  ["It is not a video game and it is not an animation. Nothing moves because "
   "an artist said so; things move because forces were computed and time was "
   "stepped forward.",
   "Every simulator does the same five things in the same order. If you can "
   "draw this loop, most interview questions become <b>&ldquo;which box are "
   "you asking about?&rdquo;</b>",
   "The hard box is number three. Steps 1, 2, 4 and 5 are largely settled "
   "engineering. Making contact forces come out right &mdash; feet not sinking "
   "through floors, fingers not squeezing through objects &mdash; is where the "
   "research, the bugs and the job are."],
  figs=[E["sim_loop"]],
  ask=("Walk me through what happens in one simulation step.",
       "Name the five stages in order and then say which one is hard and why. "
       "Contact is hard because it is a <b>constraint</b>, not a force you can "
       "write down in advance &mdash; you have to solve for the forces that "
       "happen to prevent interpenetration this instant.")),

lesson(2, "gripper", "Rigid body dynamics, minus the maths",
  "Every object is a lump with a mass, a balance point, and a resistance to "
  "being spun. Those three facts decide how it moves.",
  ["<b>Mass</b> resists being pushed. <b>Centre of mass</b> is the balance "
   "point &mdash; push through it and the object slides; push off it and the "
   "object spins. <b>Inertia</b> is mass's rotational cousin: how hard the "
   "object is to spin up, and it is different around each axis. A pencil is "
   "easy to spin like a drill bit and hard to spin end-over-end.",
   "For a jointed robot, everything reduces to one equation you should be able "
   "to say out loud:",
   "<b>M(q)&middot;q&#776; + C(q,q&#775;)&middot;q&#775; + G(q) = &tau;</b>",
   "In English: <em>inertia times acceleration, plus the velocity-dependent "
   "terms, plus gravity, equals the torques you applied.</em> M changes with "
   "pose &mdash; an outstretched arm is harder to swing than a tucked one. C "
   "covers Coriolis and centrifugal effects. G is gravity pulling on every "
   "link. &tau; is what the motors do.",
   "&ldquo;Forward dynamics&rdquo; means solving for q&#776; given &tau;. "
   "That is what a simulator does. &ldquo;Inverse dynamics&rdquo; is solving "
   "for &tau; given a motion you want &mdash; that is what a controller does."],
  ask=("Do you actually understand the dynamics or just the API?",
       "Say the equation, then immediately give the physical meaning of each "
       "term. Add that M is pose-dependent, because that is the part people "
       "who have only read about it tend to miss.")),

lesson(3, "wrench", "Joints and degrees of freedom",
  "A degree of freedom is one number you need to describe the pose. Count "
  "them and you know how big your state vector is.",
  ["Three joint types cover nearly everything: <b>revolute</b> (a hinge), "
   "<b>prismatic</b> (a slider), and <b>ball</b> (three rotations at once). "
   "There is also the <b>free joint</b> or floating base &mdash; six DOF of "
   "nothing-holding-it-up, which is what any robot not bolted to the floor has.",
   "That floating base is the single most important idea in legged robotics. "
   "A quadruped has twelve motors but eighteen degrees of freedom. The six it "
   "cannot directly control are precisely the ones that decide whether it "
   "falls over. You steer them only through contact with the ground.",
   "In a model file, <code>q</code> is the vector of joint positions and "
   "<code>qd</code> or <code>qvel</code> the velocities. For a floating base "
   "they differ in length, because orientation is stored as a 4-number "
   "quaternion but has only 3 rotational velocities. This trips up everyone "
   "once."],
  figs=[E["joint_types"], E["dof_ladder"]],
  demo=FK_DEMO,
  ask=("Have you built a model, or only loaded one?",
       "Mention the quaternion mismatch: <b>qpos is longer than qvel for a "
       "floating base</b>. Nobody who has only read tutorials says that, and "
       "everybody who has debugged a real model has hit it.")),

lesson(4, "floppy", "The three file formats",
  "A robot model is a text file listing links, their shapes and masses, and "
  "the joints connecting them. There are three common dialects and they are "
  "not equivalent.",
  ["<b>URDF</b> is the ROS standard and the most widely supported. It is also "
   "the weakest: it is strictly a <b>tree</b>, one parent per link. That means "
   "it cannot express a closed loop &mdash; no four-bar linkages, no parallel "
   "jaw grippers, no delta arms. Not a tooling gap; the data model forbids it.",
   "<b>MJCF</b> is MuJoCo's format. Richer: closed loops via equality "
   "constraints, tendons, better contact control, sensible defaults.",
   "<b>SDF</b> is Gazebo's. Sits between them, can describe whole worlds "
   "rather than one robot.",
   "The trap that catches everyone: <b>MJCF box <code>size</code> is a HALF "
   "extent; URDF and SDF <code>size</code> is the FULL extent.</b> Convert "
   "without knowing that and every part of your robot comes out twice the "
   "size it should be. I hit this exact bug &mdash; all 147 numeric checks "
   "passed and the arm's tip was still 0.23 m off, because each file was being "
   "compared against itself."],
  figs=[C["one_spec_three_formats"], E["friction_cone_explainer"]][:1],
  ask=("Can you be trusted with a model, or will you silently break it?",
       "Say the half-extent trap and the URDF tree limitation. Then say how "
       "you would catch it: <b>generate the formats from one source and "
       "cross-check them numerically</b>, rather than hand-editing three "
       "files and hoping.")),
])


PART2 = "".join([

lesson(5, "spring", "Contact and friction",
  "Two objects touching is not one thing but two: a normal force stopping "
  "them passing through each other, and a friction force resisting sliding.",
  ["Real contact is a <b>hard constraint</b>: objects simply do not "
   "interpenetrate. That is expensive to enforce, so most engines use "
   "<b>soft contact</b> &mdash; let them overlap a tiny amount and push back "
   "proportionally. The overlap is called penetration, and a fraction of a "
   "millimetre is normal.",
   "Friction is capped by the normal force: <b>friction &le; &mu; &times; "
   "normal</b>. Because that limit is the same in every direction, the "
   "allowed force lives inside a <b>cone</b>. Some solvers approximate the "
   "circular cone with a polygon because linear constraints are easier &mdash; "
   "and the polygon has more grip along its corners than its flats.",
   "I measured that artefact: a box pushed at 20&deg; slid <b>12.76&deg; off "
   "course</b> with the pyramid, versus 0.71&deg; with the exact cone. The "
   "error is exactly zero at 0&deg;, 45&deg; and 90&deg; &mdash; the square's "
   "symmetry axes. And in MuJoCo the exact cone was also <b>2.6&times; "
   "faster</b>, so there was no trade at all."],
  figs=[E["friction_cone_explainer"], C["friction_polar"]],
  ask=("Do you know why contact is the hard part?",
       "Explain hard versus soft contact, then the friction cone and why "
       "polygonal approximations are directionally biased. If you can cite a "
       "number you measured yourself, you are instantly in a different "
       "category of candidate.")),

lesson(6, "stopwatch", "Timesteps and integrators",
  "The simulator moves time forward in small jumps. How it does that jump "
  "decides whether your robot behaves or explodes.",
  ["<b>Explicit Euler</b> is the simplest: assume the current acceleration "
   "holds for the whole step. Cheap, and it slowly invents energy. "
   "<b>RK4</b> samples the acceleration four times per step and is far more "
   "accurate. <b>Implicit</b> methods solve for the end-of-step state and are "
   "extremely stable but blur fast motion.",
   "The proper way to judge one is <b>order of accuracy</b>: a method of order "
   "<em>p</em> has error proportional to dt<sup>p</sup>. Halve the timestep, "
   "and a first-order method halves its error while a fourth-order one cuts it "
   "sixteenfold. That is measurable, and I measured it: Euler came out at "
   "1.002, RK4 at 3.994, against theory of 1 and 4.",
   "Here is the counter-intuitive part worth knowing. <b>Accuracy and "
   "stability are different things.</b> Under a stiff controller, RK4 &mdash; "
   "the accurate one &mdash; blew up at a gain of 5, while plain Euler "
   "survived to 10 and the implicit methods went past 500. High order says "
   "nothing about the size of the stability region."],
  figs=[C["integrator_order"], C["integrator_stability_bars"]],
  demo=DT_DEMO,
  ask=("Will you know what to do when the sim explodes?",
       "Say: check the timestep first, then whether anything stiff was added "
       "&mdash; high controller gains, huge mass ratios, very hard contacts. "
       "Mention that switching to an implicit integrator often fixes it at no "
       "accuracy cost, which is a much better answer than &lsquo;lower the "
       "timestep&rsquo;.")),

lesson(7, "scales", "Solvers, and the mass ratio trap",
  "After deciding which things are touching, the engine has to find contact "
  "forces that satisfy every constraint at once. That is the solver.",
  ["Three families you should be able to name: <b>Newton</b> (second order, "
   "few expensive iterations), <b>CG</b> (conjugate gradient), and <b>PGS</b> "
   "(projected Gauss-Seidel, the classic game-physics choice). On a "
   "well-behaved problem all three give the same answer &mdash; but Newton ran "
   "<b>14&times; faster than PGS</b> at identical accuracy.",
   "The failure mode you must know is <b>mass ratio</b>. Put a very heavy body "
   "on a very light one and solvers fall apart, because the light body has to "
   "transmit a force many times its own weight. At a 1000:1 ratio, MuJoCo "
   "squashed the light block 50&nbsp;mm and PhysX let the heavy one pass "
   "<b>entirely through</b> it.",
   "And crucially: <b>you cannot fix this by turning up solver iterations in "
   "MuJoCo.</b> One iteration and fifty give identical results, because the "
   "squash is the soft-contact model behaving as specified, not a convergence "
   "failure. In PhysX iterations do help, but only past a cliff between 64 and "
   "96, and even 255 cannot save a 10000:1 ratio.",
   "The real fix is in the <b>model</b>: rescale the masses, or replace the "
   "stack with a joint."],
  figs=[C["mass_ratio_cliff"], C["solver_speed"]],
  ask=("Have you debugged a simulation that misbehaved?",
       "&ldquo;My stack is jittering&rdquo; is a mass-ratio question nine "
       "times out of ten. Say you would check the ratio between contacting "
       "bodies <b>before</b> touching solver settings, and that you would "
       "rescale masses rather than crank iterations.")),

lesson(8, "wrench", "Actuators, and the term everyone forgets",
  "A motor is not a magic torque source. It has its own inertia, a gearbox, "
  "limits, and lag &mdash; and ignoring that is a top cause of sim-to-real "
  "failure.",
  ["A gearbox multiplies torque by N and divides speed by N. What people "
   "forget is what it does to <b>inertia</b>: the motor's own spinning rotor "
   "appears at the joint multiplied by <b>N squared</b>.",
   "That sounds academic until you put numbers on it. At a gear ratio of 100, "
   "a rotor with an inertia of 0.00002 kg&middot;m&sup2; &mdash; essentially "
   "nothing &mdash; contributes <b>more inertia at the joint than the entire "
   "link it is driving</b>. Leave it out and your simulated robot is far more "
   "responsive than the real one, every controller you tune in sim is wrong, "
   "and nobody can tell you why.",
   "Also model: <b>torque limits</b> (motors saturate), <b>velocity limits</b> "
   "(back-EMF), and <b>friction</b> in the gearbox."],
  figs=[C["reflected_inertia"]],
  ask=("Do you know why sim-tuned controllers fail on hardware?",
       "Lead with reflected rotor inertia scaling as N&sup2;. It is specific, "
       "it is frequently omitted, and it explains a real class of sim-to-real "
       "failure. Then add torque saturation.")),

lesson(9, "brain", "Control, just enough of it",
  "A controller decides what torques to send. You are not applying for a "
  "controls job, but you must speak the language.",
  ["<b>PD control</b> is nearly all you need: <em>torque = kp &times; (where I "
   "want to be &minus; where I am) &minus; kd &times; (how fast I am "
   "moving)</em>. The kp term pulls toward the target; the kd term resists "
   "speed and damps the wobble. Add an integral term for steady-state error "
   "and you have PID.",
   "Turn kd to zero and the joint oscillates forever. Turn kp too low and it "
   "never arrives. Turn kp very high and, in simulation, the whole thing can "
   "become numerically unstable &mdash; which is where this connects back to "
   "integrators. A joint PD controller's derivative term <em>is</em> a "
   "velocity actuator, and with explicit Euler it diverges once "
   "<code>kd&middot;dt/I &gt; 2</code>.",
   "So when a control engineer says &ldquo;I need higher gains&rdquo;, the "
   "right answer is often not &ldquo;lower your gains&rdquo; but "
   "<b>&ldquo;let me change the integrator&rdquo;</b>."],
  figs=[E["pd_control"]],
  demo=PD_DEMO,
  ask=("Can you work with the controls people?",
       "Show you understand their constraint, not just yours. Saying that a "
       "gain limit can be a <b>solver</b> problem rather than a controls "
       "problem is exactly the cross-boundary thinking a simulation engineer "
       "is hired for.")),
])


PART3 = "".join([

lesson(10, "target", "The sim-to-real gap",
  "Your robot works perfectly in simulation and falls over outside. The gap "
  "between those two facts is the entire point of this job.",
  ["Four causes, in roughly the order they bite. <b>Inertial parameters are "
   "guesses</b> &mdash; nobody weighed each link. <b>Friction is not one "
   "number</b> &mdash; it varies with surface, speed, temperature and wear. "
   "<b>Actuators lag and saturate.</b> <b>Sensors are noisy and delayed.</b>",
   "Three standard fixes. <b>System identification</b>: run the real robot, "
   "record it, and fit the model parameters to match. <b>Domain "
   "randomisation</b>: instead of one perfect model, train across thousands of "
   "randomly perturbed ones so the policy cannot depend on any single value. "
   "<b>Better component models</b>: actuator dynamics, sensor noise.",
   "One honest thing worth saying about system ID: sometimes a parameter is "
   "<b>not identifiable at all</b>. I measured one with a trajectory "
   "sensitivity of exactly <b>0.000</b> &mdash; the experiment carried no "
   "information about it, so no optimiser could recover it. Reporting a fitted "
   "number there would be inventing one."],
  figs=[E["sim2real"], C["identifiability"]],
  ask=("Do you understand the actual problem, or just the tools?",
       "This is the question the whole job description is built around. Name "
       "the causes and the fixes. Then add the identifiability point &mdash; "
       "knowing when your data <b>cannot</b> answer a question is a maturity "
       "signal that separates people fast.")),

lesson(11, "chip", "The three simulators",
  "MuJoCo, Isaac Sim and Gazebo. You need a real opinion about which to use "
  "and why.",
  ["<b>MuJoCo</b> (now Google DeepMind's, free): excellent contact, very fast "
   "on CPU, the research default for locomotion and manipulation. Its GPU "
   "version is <b>MJX</b>. Format: MJCF.",
   "<b>NVIDIA Isaac Sim</b>: built on Omniverse. Photorealistic rendering for "
   "camera-based work, and GPU physics that runs <b>thousands of robots at "
   "once</b> &mdash; I measured 65,536 parallel environments at 812,670 "
   "physics steps per second on a single free-tier T4. Heavy to install. "
   "<b>Isaac Lab</b> is the RL framework on top.",
   "<b>Gazebo</b>: the classic ROS simulator. Deeply integrated with ROS 2, "
   "great plugin ecosystem for sensors, physics slower than the other two. "
   "Format: SDF.",
   "The honest summary: <b>MuJoCo for contact-rich research, Isaac for "
   "large-scale RL and camera sensors, Gazebo when the team lives in ROS.</b>"],
  figs=[E["simulator_picker"], C["scale_bars"]],
  ask=("Which would you pick for our problem?",
       "Never say &ldquo;whichever you use&rdquo;. Pick one, justify it "
       "against <em>their</em> problem, and name the trade-off you are "
       "accepting. Then say you have used the others, because this role lists "
       "all three.")),

lesson(12, "network", "ROS 2, the minimum",
  "ROS is the plumbing that lets separate robot programs talk. The JD says "
  "&ldquo;familiarity&rdquo;, so you need the concepts, not mastery.",
  ["A ROS system is many small programs (<b>nodes</b>) that publish and "
   "subscribe to named channels (<b>topics</b>). A camera node publishes "
   "images; a planner subscribes to them and publishes velocity commands; a "
   "driver subscribes to those and moves the motors.",
   "Simulation slots in by <b>impersonating the hardware</b>. The simulator "
   "publishes the same topics the real robot would &mdash; joint states, "
   "camera frames, IMU &mdash; and subscribes to the same commands. Done "
   "right, the rest of the stack cannot tell the difference. That is the whole "
   "value of a ROS bridge.",
   "Two things that will come up. <b>Sim time</b>: ROS must use the "
   "simulator's clock, not the wall clock, or every timestamp is wrong &mdash; "
   "this surfaces as bizarre transform-lookup failures, never as anything "
   "clock-shaped. And <b>TF</b>, the transform tree, which tracks where every "
   "frame is relative to every other."],
  ask=("Can you plug your simulation into our stack?",
       "Say the simulator should publish and subscribe exactly what the "
       "hardware does, so nothing downstream changes. Mention <code>use_sim_"
       "time</code>. That one detail signals you have actually run it.")),

lesson(13, "camera", "Sensor simulation",
  "A robot only knows what its sensors tell it. Simulating them badly is a "
  "quiet way to build a policy that cannot work outside.",
  ["<b>Cameras</b> need real rendering, which is why Isaac Sim exists. The "
   "thing that matters is not beauty but <b>matching the failure modes</b>: "
   "motion blur, rolling shutter, exposure, lens distortion.",
   "<b>LiDAR</b> is ray casting: shoot rays, return distances. Add dropout on "
   "dark or shiny surfaces or the policy will trust it too much.",
   "<b>IMUs</b> measure acceleration and angular rate, and drift. The noise "
   "model is the whole game &mdash; a noiseless simulated IMU is not an IMU.",
   "<b>Force/torque sensors</b> read contact forces directly, and are only as "
   "good as your contact model.",
   "The rule of thumb: <b>a perfect sensor is a bug.</b> If your policy relies "
   "on measurements cleaner than the hardware can produce, it will fail, and "
   "it will fail in a way that looks like a control problem."],
  ask=("Do you know why perfect sensors are dangerous?",
       "Give the rule directly: a noiseless sensor teaches the policy to trust "
       "information it will not have. Then name a concrete noise model &mdash; "
       "IMU bias drift, LiDAR dropout on glass.")),

lesson(14, "chip", "Making it fast",
  "Simulation for learning means running millions of steps. Knowing where "
  "time goes is a big part of the job.",
  ["First rule: <b>measure before optimising</b>. I profiled with per-phase "
   "timers and found collision detection cost <b>roughly three times the "
   "constraint solver</b> &mdash; which meant tuning solver iterations, the "
   "obvious move, would have been wasted effort.",
   "The biggest single lever is usually <b>collision geometry</b>. Use "
   "primitives &mdash; boxes, spheres, capsules &mdash; not the visual mesh. "
   "Hull cost grows with vertex count, and artists hand you meshes with "
   "thousands.",
   "Then <b>parallelism</b>. GPU simulators run thousands of environments at "
   "once, which is what makes reinforcement learning practical: 65,536 "
   "environments at 812,670 steps/s versus 171,000 for a single CPU "
   "environment.",
   "A trap worth knowing: <b>throughput numbers are wall-clock and they move.</b> "
   "The same per-contact figure shifted 76% on one machine under load. Compare "
   "orderings, not magnitudes."],
  figs=[C["phase_profile"], C["collision_bars"]],
  ask=("Will you optimise the right thing?",
       "Say you profile first, and give the collision-versus-solver example. "
       "Then mention collision primitives, because it is the highest-leverage "
       "fix and shows you have actually made a scene faster.")),
])


PART4 = "".join([

lesson(15, "check", "Testing a simulation",
  "How do you unit-test physics? By asserting things that are true no matter "
  "what the engine does.",
  ["The wrong way is <b>golden files</b>: record the output, assert it never "
   "changes. They rot the moment anyone legitimately regenerates them, and "
   "then people delete the test.",
   "The right way is <b>closed-form physics</b>. A block sliding to rest "
   "travels <code>v&sup2;/(2&micro;g)</code> &mdash; that cannot be "
   "regenerated, it is just true. Drop something and check gravity comes back "
   "out. Grip a block and check the holding force matches "
   "<code>mg/(2&micro;)</code>.",
   "Then the step almost nobody takes: <b>test that your tests can fail</b>. A "
   "suite that passes on a broken model converts &ldquo;unknown&rdquo; into "
   "&ldquo;verified&rdquo;, which is worse than no suite. I wrote four tests "
   "whose only job is to break the model and confirm the gates notice &mdash; "
   "the sharpest swaps real friction for velocity drag and checks the "
   "mass-independence gate rejects it.",
   "And beware of the check that measures the wrong thing. I once had "
   "<code>isfinite()</code> report a diverged simulation as <b>stable</b>, "
   "because MuJoCo silently resets a blown-up state to zero. It hit a velocity "
   "of 345,000, got reset, then sat at exactly zero for 397 steps looking "
   "perfectly healthy."],
  ask=("Are you disciplined, or do you just make things run?",
       "The JD asks for CI experience. Say closed-form assertions over golden "
       "files, then the &lsquo;test your tests&rsquo; idea. That is a senior "
       "instinct and very few candidates mention it.")),

lesson(16, "quadruped", "Legged locomotion",
  "Walking is a contact problem, not a motion problem. The robot is falling "
  "and catching itself, on purpose, forever.",
  ["A <b>gait</b> is defined by its contact schedule &mdash; which feet are on "
   "the ground when. A <b>trot</b> moves diagonal pairs together, half a cycle "
   "apart. A <b>walk</b> moves one foot at a time. Duty factor is the fraction "
   "of the cycle a foot spends on the ground.",
   "Nearly everything hard follows from the <b>floating base</b>: six "
   "unactuated degrees of freedom you can only influence by pushing on the "
   "ground. Balance is not a controller you bolt on, it is the whole problem.",
   "A mistake worth having made: I drove a quadruped with open-loop joint "
   "sinusoids and measured the foot contacts. The duty came out at 0.96 on "
   "every leg &mdash; nothing ever lifting. The robot was <b>falling over</b>, "
   "and my measurement faithfully described the fall. Sinusoids that look like "
   "walking are not a gait; without a balance controller a quadruped topples.",
   "The fix was to change the <b>frame</b>, not the controller: a gait "
   "generator's output is the foot trajectory relative to the <em>trunk</em>. "
   "Measured there, it is well-posed whether the robot balances or not. Spot "
   "then reproduced the commanded trot to within <b>4.8&deg;</b>."],
  figs=[C["trot_wheel"]],
  ask=("Have you worked with legged robots or just read about them?",
       "Talk about the floating base and the contact schedule. The strongest "
       "thing you can say is the mistake: measuring in the wrong frame, and "
       "how you noticed. Interviewers trust a specific failure far more than a "
       "smooth summary.")),

lesson(17, "gripper", "Manipulation",
  "Grasping is friction plus geometry. Whether the object stays in the hand "
  "is a calculation, not a hope.",
  ["For a two-finger pinch on a smooth block, friction at the two contacts "
   "carries the weight: <b>2&micro;F &ge; mg</b>, so the minimum grip force is "
   "<code>F = mg / (2&micro;)</code>. I bisected the grip force in simulation "
   "and found the threshold, and all four cases landed <b>just above</b> the "
   "closed form.",
   "That direction matters. <code>mg/(2&micro;)</code> is the <em>marginal</em> "
   "holding force &mdash; it holds with zero margin &mdash; so real numerical "
   "contact needs slightly more. A measurement <b>below</b> theory would be "
   "alarming: it would mean the contact model is generating friction the "
   "material properties do not license.",
   "Beyond force: <b>form closure</b> (the geometry cages the object, no "
   "friction needed) versus <b>force closure</b> (friction does the work). And "
   "contact for manipulation is far more sensitive than for locomotion, "
   "because fingertips are small and the forces are fine."],
  figs=[C["grasp_bars"]],
  ask=("Can you reason about grasping quantitatively?",
       "Give the formula, then the subtle point: measuring <em>above</em> "
       "theory is correct and measuring below would indicate a bug. Knowing "
       "which direction of error is suspicious is a much stronger signal than "
       "quoting the formula.")),

lesson(18, "book", "Words you must not fumble",
  "Say these wrong and a technical interviewer will notice immediately.",
  ["<b>Kinematics</b> &mdash; motion without forces. <b>Dynamics</b> &mdash; "
   "motion caused by forces. <b>Forward kinematics</b>: joint angles &rarr; "
   "where the hand is. <b>Inverse kinematics</b>: where the hand should be "
   "&rarr; joint angles (harder, often many answers or none).",
   "<b>Configuration space</b> &mdash; the space of all poses; a 6-axis arm's "
   "is 6-dimensional. <b>Jacobian</b> &mdash; the matrix relating joint "
   "velocities to end-effector velocity; it goes singular at a "
   "<b>singularity</b>, where the arm loses a direction it can move.",
   "<b>Stiff</b> &mdash; a system with very fast and very slow dynamics "
   "together; needs small timesteps or implicit integration. <b>Constraint</b> "
   "&mdash; a rule the solver must satisfy, like non-penetration. "
   "<b>Restitution</b> &mdash; bounciness. <b>Damping</b> &mdash; velocity-"
   "proportional resistance. <b>Compliance</b> &mdash; deliberate softness.",
   "<b>Rollout</b> &mdash; one episode of simulation. <b>Headless</b> &mdash; "
   "no rendering. <b>Determinism</b> &mdash; same inputs, same outputs, "
   "bit-for-bit."],
  ask=("Are you fluent, or translating?",
       "The tell is hesitation, not ignorance. Practise saying the Jacobian "
       "and singularity definitions out loud until they are automatic &mdash; "
       "they come up constantly and stumbling on them is expensive.")),
])


QA = [
 ("Walk me through what happens in one simulation timestep.",
  "Forward dynamics, collision detection, constraint solve, integrate, sensors. "
  "Then say <b>the constraint solve is the hard one</b>, because contact forces "
  "are not known in advance &mdash; you solve for whatever forces happen to "
  "prevent interpenetration this instant."),
 ("How would you validate a robot model someone handed you?",
  "Check the closed-form things first: total mass, centre of mass, and whether "
  "forward kinematics matches an independent implementation. Then dynamic "
  "checks &mdash; drop it and see if gravity comes back out, slide it and see "
  "if the stopping distance matches <code>v&sup2;/(2&micro;g)</code>. Mention "
  "unit and convention traps: <b>MJCF half extents versus URDF full extents</b>."),
 ("My simulation is unstable. What do you check?",
  "In order: <b>timestep</b>, then <b>mass ratios</b> between contacting bodies, "
  "then <b>controller gains</b>, then contact stiffness. Say that high gains "
  "with an explicit integrator diverge once <code>kd&middot;dt/I &gt; 2</code>, "
  "and switching to implicit often fixes it at no accuracy cost."),
 ("Why does a policy trained in simulation fail on hardware?",
  "Name the four causes &mdash; inertial parameters, friction, actuator "
  "dynamics, sensor noise &mdash; and the three fixes: system identification, "
  "domain randomisation, better component models. Then give the specific one: "
  "<b>reflected rotor inertia scaling as N&sup2;</b> is commonly omitted and "
  "makes the simulated robot far more responsive than the real one."),
 ("MuJoCo, Isaac Sim or Gazebo?",
  "Pick one for <em>their</em> problem and name the trade-off. Contact-rich "
  "research: MuJoCo. Large-scale RL or camera sensors: Isaac. A team living in "
  "ROS: Gazebo. Never answer &ldquo;whichever you use&rdquo;."),
 ("How do you test a physics simulation?",
  "Closed-form assertions rather than golden files, because golden values rot "
  "and get deleted. Then the part almost nobody says: <b>write tests that "
  "deliberately break the model to confirm the gates actually fire</b>. A suite "
  "that passes on a broken model turns unknown into verified."),
 ("What is the friction cone and why does it matter?",
  "Friction is capped at <code>&micro; &times; normal</code> in every "
  "direction, so allowed forces form a cone. Polygonal approximations are "
  "directionally biased &mdash; more grip along the corners. Quote the "
  "measurement: 12.76&deg; of direction error with a pyramid versus 0.71&deg; "
  "with the exact cone, and the exact one was also faster."),
 ("How would you speed up a slow simulation?",
  "Profile first. Then: collision primitives instead of visual meshes, reduce "
  "contact pairs, check the timestep is not smaller than it needs to be, and "
  "parallelise on GPU if the workload is many independent environments. Give "
  "the example of collision costing 3&times; the solver, which made solver "
  "tuning the wrong lever."),
 ("Tell me about a bug you found that was hard to track down.",
  "Use a real one. The strongest shape is <b>an error message that named the "
  "wrong subsystem</b> &mdash; a numpy &ldquo;zero-size array&rdquo; that was "
  "actually an <code>if</code> block sitting outside a loop, so the simulation "
  "was never stepped. Say that you rewrote the wrong component twice before "
  "reading the code path properly."),
 ("What do you do when you are not sure your result is right?",
  "Design the check that would prove you wrong. Vary something that should not "
  "matter and confirm it does not; recover a known input from an emergent "
  "output. Example: putting <code>&micro;</code> into the engine as a material "
  "property and reading it back out of the slip angle via "
  "<code>tan&theta; = &micro;</code> &mdash; within 2%."),
]

QA_HTML = '<dl class="qa">' + "".join(
    f"<dt>{q}</dt><dd>{a}</dd>" for q, a in QA) + "</dl>"

TOC = '<div class="toc">' + "".join(
    f'<a href="#L{n}"><span>{n:02d}</span>{t}</a>' for n, t, _ in LESSONS
) + "</div>"

BODY = f"""
<div class="wrap mast">
  <section class="win">
    <div class="bar"><span class="box"></span><h3>Robotics Simulation for Dummies</h3>
      <span class="grow"></span></div>
    <div class="body">
      <div class="ico-row">{I("book", 6)}{I("brain", 6)}{I("quadruped", 6)}</div>
      <h1>Robotics<br>Simulation<br>for Dummies</h1>
      <p class="sub">Eighteen lessons from nothing to interview-ready, for one
      specific job: <b>Robotics Simulation Engineer, $180&ndash;200/hr</b>.
      Every lesson ends with <span class="hi">what the interviewer is really
      asking</span>, because a definition you can recite is worth much less
      than knowing why the question gets asked.</p>
    </div>
    <div class="tiles">
      <div class="tile"><b>18</b><span>lessons</span></div>
      <div class="tile"><b>3</b><span>things you<br>can play with</span></div>
      <div class="tile"><b>10</b><span>likely questions<br>with answers</span></div>
      <div class="tile"><b>0</b><span>maths you<br>must memorise</span></div>
    </div>
    {TOC}
  </section>

  <section class="win">
    <div class="bar"><span class="box"></span><h3>Start here</h3>
      <span class="grow"></span></div>
    <div class="body">
      <div class="grid2">
        <div class="say">
          <div class="ico-row">{I("target", 5)}</div>
          <h2>What the job actually is</h2>
          <div class="plain"><b>In plain English</b>You build the fake world
          robots practise in, and you are judged on how well what they learn
          there survives contact with the real one.</div>
          <p>Read the posting again with that lens. &ldquo;High-fidelity robot
          models&rdquo;, &ldquo;tune physics parameters&rdquo;, &ldquo;maximise
          sim-to-real transfer&rdquo; &mdash; it is all one sentence:
          <b>make the simulation lie less</b>.</p>
          <p>Everything in this guide is aimed at that. The physics matters
          because wrong physics teaches robots wrong lessons. The file formats
          matter because a mistyped number is a robot with the wrong mass.
          Performance matters because learning needs millions of attempts.</p>
        </div>
        <div>
          <div class="figwrap">{E["sim2real"]}</div>
          <div class="demo" style="margin-top:.75rem">
            <img src="{SEQ['arm'][0]}" data-seq="arm" data-fps="20"
                 alt="a three link arm swinging under gravity">
            <div class="note">A real simulated arm, rendered from its own model
            file. Three links, three hinges, gravity, nothing else. Everything
            in this guide is about making something like this behave the way
            metal would.</div>
          </div>
        </div>
      </div>
    </div>
  </section>
</div>

<main class="wrap">
{PART1}{PART2}{PART3}{PART4}

<section class="win">
  <div class="bar"><span class="box"></span><h3>Ten questions, and what to say</h3>
    <span class="grow"></span></div>
  <div class="body">
    <div class="ico-row">{I("question", 5)}</div>
    <h2>The interview itself</h2>
    <p style="color:var(--stone);font-size:.94rem;max-width:60ch">Answers are
    written to be said out loud, not recited. Where a number appears, it is one
    that was actually measured &mdash; using your own numbers is the single
    biggest advantage you have.</p>
  </div>
  {QA_HTML}
</section>

<section class="win">
  <div class="bar"><span class="box"></span><h3>How to talk about your own work</h3>
    <span class="grow"></span></div>
  <div class="body">
    <div class="ico-row">{I("bomb", 5)}{I("check", 5)}</div>
    <h2>Lead with the corrections</h2>
    <div class="plain"><b>The move</b>Most candidates present only successes.
    Presenting a wrong answer <em>and the check that caught it</em> is far more
    convincing, because it proves you can find your own mistakes &mdash; which
    is the actual job.</div>
    <p style="color:var(--stone);font-size:.94rem;max-width:60ch">Five worth
    having ready:</p>
    <dl class="qa">
      <dt>isfinite() is not a stability test</dt>
      <dd>A simulation reported <b>stable</b> after diverging, because the
      engine silently resets a blown-up state to zero. Velocity hit 345,000,
      got reset, then read exactly zero for 397 steps. Shows you distrust green
      checks.</dd>
      <dt>The control that named a mechanism</dt>
      <dd>Solver iterations fixed a mass-ratio failure in PhysX; velocity
      iterations did not. That one control turned a correlation into a specific
      cause &mdash; position-level depenetration. Shows experimental design.</dd>
      <dt>Two of my own results contradicted each other</dt>
      <dd>Penetration was mass-independent in one study and scaled 237&times;
      in another. Both were right: the cancellation only holds when the load
      equals the contact's own effective mass. Shows you reconcile rather than
      pick.</dd>
      <dt>The error that named the wrong subsystem</dt>
      <dd>A numpy &ldquo;zero-size array&rdquo; was an <code>if</code> outside
      a loop. I rewrote the wrong component twice chasing it. Shows honest
      debugging.</dd>
      <dt>Eleven attempts, then a reframe</dt>
      <dd>Ten gait attempts measured in the wrong frame. The fix was not a
      better test rig but measuring relative to the trunk. Shows knowing when
      the approach is wrong rather than the implementation.</dd>
    </dl>
  </div>
</section>
</main>

<div class="wrap">
<footer>
  <section class="win">
    <div class="bar"><span class="box"></span><h3>Honest notes</h3>
      <span class="grow"></span></div>
    <div class="body">
      <div class="ico-row">{I("magnifier", 4)}{I("book", 4)}</div>
      <p>Every measured number here comes from runs in the companion
      repository, and every chart is generated from that data rather than drawn
      by hand. The three things you can drag &mdash; the PD tuner, the two-link
      arm, the orbit &mdash; are <b>teaching toys</b>: small honest versions of
      the real dynamics, not measurements, and they say so where they sit.</p>
      <p>This guide will not make you a robotics simulation engineer. It will
      let you hold a technical conversation with one, understand what the job
      is asking for, and talk about real work you have done. The rest is
      reps.</p>
    </div>
  </section>
</footer>
</div>
"""

EARLY_JS = "<script>document.documentElement.classList.add('js');</script>"
DATA_JS = ("<script>window.__SEQ__=" + demos.frames_json({"arm": SEQ["arm"]})
           + ";window.__CONE__={};</script>")
SCRIPTS = ("<script>" + demos.PLAYER_JS + demos.REVEAL_JS
           + edu_demos.EDU_JS + "</script>")

HEAD = """<title>Robotics Simulation for Dummies</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Silkscreen:wght@400;700&family=Rubik:wght@400;500;600&display=swap">
"""

with open(OUT, "w") as f:
    f.write(HEAD + BASE_CSS + GUIDE_CSS + EARLY_JS + BODY + DATA_JS + SCRIPTS)
print(f"wrote {OUT}  ({os.path.getsize(OUT)/1024/1024:.2f} MB, {len(LESSONS)} lessons)")
