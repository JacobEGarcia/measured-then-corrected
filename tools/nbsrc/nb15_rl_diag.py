TITLE = 'Diagnosing an Unlearnable RL Environment'
SLUG = 'diagnosing-an-unlearnable-rl-environment'
SUBTITLE = ("Four training runs scored identically to random. The fault was not "
            "the algorithm - half the state vector never moved.")
TAGS = ['reinforcement learning', 'robotics', 'gpu']

CELLS = [
("md", """
## When tuning is the wrong response

Four training runs on `Isaac-Cartpole-Direct-v0` - one CEM, three PPO -
produced policies indistinguishable from random. Returns flat, and episode
length **identical** for trained and untrained policies: 41.5 steps versus
41.3.

That last detail is the signal. When a trained policy and a random one fail in
exactly the same way, the problem is upstream of learning, and a fifth set of
hyperparameters will not find it.

So instead of tuning again, I drove the environment with constant actions:
`+1`, `-1`, and `0`.
"""),

("code", r'''
import json
D = json.loads(r"""{"action_space": {"shape": [1],"low": -Infinity,"high": Infinity},"action_scale_cfg": 100.0,"obs_shape": [64,4],"plus1": {"obs_last": [0.12201,0.17561,-0.0,0.0008],"obs_range": [3.02635,9.58222,0.0,0.0008],"traj0": [-0.57303,-0.57701,-0.58329,-0.59189,-0.60283,-0.61615,-0.6319,-0.65013]},"minus1": {"obs_last": [0.10023,0.36224,0.0,-0.0008],"obs_range": [1.45946,4.95923,0.0,0.0008],"traj0": [0.41453,0.4175,0.42216,0.42855,0.43668,0.4466,0.45832,0.47191]},"zero": {"obs_last": [0.81557,2.12405,-0.0,1e-05],"obs_range": [2.37944,7.49133,0.0,9e-05],"traj0": [-0.17689,-0.17818,-0.18022,-0.18301,-0.18657,-0.19091,-0.19604,-0.20199]}}""")
print("action space:", json.dumps(D["action_space"]))
print("action_scale from env cfg:", D["action_scale_cfg"], " -> an action of 1.0 is 100 N")
print()
print("observation RANGE over 60 steps, per dimension:")
for k in ("plus1", "minus1", "zero"):
    print(f"  {k:>7}: {D[k]['obs_range']}")
'''),

("md", """
## Two findings, and the second is the real one

**`action_scale = 100`.** An action of 1.0 is 100 newtons. My PPO used a
`tanh` policy with `logstd = -1`, so the **exploration noise alone** was about
+/-37 N - enough to drive the cart into its position limit on virtually every
episode. That is a genuine bug, and it explains why every policy looked equally
bad.

Fixing it changed nothing. Which is how the second finding surfaced:

```
             cart pos    cart vel    dim 2     dim 3
  plus1  :     3.026       9.582      0.000    0.0008
  minus1 :     1.459       4.959      0.000    0.0008
  zero   :     2.379       7.491      0.000    0.00009
```

**Half the state vector never changes.** Under a 200 N swing in applied force,
the cart travels metres at nearly 10 m/s - and two of the four observation
dimensions stay pinned at zero range.

The pole degree of freedom does not move. A cartpole whose pole cannot move is
not a control problem: there is nothing for a policy to influence, so every
policy is optimal because every policy is irrelevant.

## The mistake inside the diagnostic

Worth recording, because it nearly sent me the wrong way.

The probe's automated verdict compared **final cart position** across the three
regimes, found them similar, and printed `actions_reach_env: false`. That
conclusion is wrong - actions have an enormous effect.

The environment **auto-resets on termination**. With +/-100 N the cart hits its
limit within a few steps and resets, so the final observation is a freshly-reset
state near zero. Zero action drifts slowly without terminating and accumulates
further from the origin. The final positions looked alike for precisely the
opposite reason.

I built the diagnostic to avoid trusting a summary statistic, then wrote its
verdict as a summary statistic. The **trajectories** - logged alongside, almost
as an afterthought - are what actually settled it.

## What this is worth

No policy was trained. What replaced it is more useful:

- `action_scale` is a property of the environment config that silently dictates
  what your policy's output range must be
- identical failure between trained and random policies indicates an
  environment problem, not a learning-rate problem
- **logging per-dimension observation ranges** costs nothing and reveals a
  degenerate task immediately

**Honest limit:** this shows the pole DOF is static on this build under these
actions. Whether that is an environment-configuration issue or a misreading of
the observation layout is unresolved, and both readings fit the data.

If you have run this task successfully on Isaac Lab 3.0.0b2, I would like to
know what differs.
"""),
]
