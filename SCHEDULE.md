# Publishing schedule

Two constraints drive this ordering:

1. **The 90-day rule.** Votes stop counting toward medals once a notebook is
   90 days old. Publishing all five at once means all five windows open and
   close together — one quiet stretch and the whole run is wasted. Staggering
   keeps at least one fresh notebook earning at all times.
2. **Dependency depth.** Notebooks 1 and 5 need only a Kaggle account.
   Notebooks 2 and 3 need generated datasets, which need the Lightning box.
   Publish shallow-first so nothing waits on setup.

## Order and blockers

| Week | Ship | Needs | Blocked by |
|---|---|---|---|
| 1 | Contributor tier + DLI course | Kaggle, NVIDIA accounts | you |
| 1 | **NB1** Isaac Sim on Kaggle | Kaggle GPU | you |
| 2 | **Dataset 3** + **NB5** MuJoCo vs Isaac | Isaac bench run | Kaggle GPU |
| 3 | **NB4** Isaac Lab RL | Isaac Lab install | Lightning (preferred) |
| 5 | **Dataset 1** + **NB2** Synthetic data | generation run | Lightning |
| 6 | **Dataset 2** + **NB3** Domain randomization | second generation run | Lightning |

Notebook 1 is deliberately first. It is the most novel, it needs the least
setup, and it is the series entry point every later notebook links back to.

## Ready to ship right now

- `bench_mujoco.json` — real measured results, already in the dataset
- Both benchmark generator scripts
- All five notebooks, built and validated

## Blocked on your accounts

- Running NB1 on a real Kaggle T4 (it must actually execute before publishing
  — a notebook that errors on run is worse than no notebook)
- `bench_isaac.json`, the other half of the benchmark
- All three synthetic datasets

## The rule I will follow

**Nothing gets published that has not been executed successfully first.**
A notebook with a traceback in its output earns downvotes, not medals, and the
first impression is not recoverable by editing later.

## Discussion medals — start immediately

50 bronze at 1 upvote each. This is the only category that needs no compute
and no setup, so it runs in parallel from day one. Target threads where the
robotics/simulation background is a genuine edge:

- physics engine choice questions
- synthetic data and sim2real
- RL environment design
- "which GPU do I need" questions (the RT-core answer is genuinely useful and
  almost nobody knows it)

Substantive answers only. Low-effort comment farming gets flagged, and votes
from Novice accounts do not count anyway — so the mercenary version of this
strategy does not even work on its own terms.
