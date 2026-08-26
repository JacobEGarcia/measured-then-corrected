# Method 3 — Google Colab (smoke test + reproducibility)

Colab's role is NOT to do real work. It is:

1. The 30-minute smoke test that proves Isaac Sim runs before we spend
   Lightning credits on it.
2. A **"Open in Colab" badge on every published Kaggle notebook.**
   Reproducibility is one of the strongest upvote drivers on Kaggle — a reader
   who can run your thing in one click is far likelier to vote for it.

## The recipe

Use the unofficial but working notebooks at:

    https://github.com/j3soon/isaac-sim-colab

Covers Isaac Sim 6.0.1.0 standalone and Isaac Sim 6.0.1.0 + Isaac Lab 2.1.0,
with one-click Colab launch buttons.

The author is explicit that this is "for demo purposes only, using various
hacks" and not for serious development. Treat it accordingly: proof of life,
not a workbench.

## Known failure modes

- pip install wedges partway -> **delete the runtime and start fresh**.
  Do not try to repair it in place; it is faster to restart.
- Free tier may hand you a CPU-only runtime. Check with `!nvidia-smi` first;
  if there is no GPU, there is no point continuing.
- 12-hour session cap and idle disconnects. Nothing persists.

## Requirements to check first

    !nvidia-smi
    import platform; print(platform.libc_ver())   # need GLIBC >= 2.34
    import shutil; print(shutil.disk_usage('/'))  # need ~25GB+ free
