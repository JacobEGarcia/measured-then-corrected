TITLE = 'Free Labeled Training Data with Isaac Sim'
SLUG = 'free-labeled-training-data-with-isaac-sim'
SUBTITLE = ("Perfect bounding boxes, segmentation masks and depth, generated "
            "at thousands of frames per hour, for zero labeling cost. And the "
            "catch nobody mentions.")
TAGS = ['computer vision', 'robotics', 'deep learning', 'image']

CELLS = [
("md", """
## The pitch

Labeling is the tax on every computer vision project. A bounding-box dataset
of 10,000 images costs real money and weeks of calendar time, and the labels
still come back with errors.

A renderer knows where every object is. It placed them. So it can emit
**pixel-perfect** bounding boxes, instance segmentation, semantic
segmentation, depth, surface normals and object poses — for free, at whatever
scale you are willing to wait for.

NVIDIA **Isaac Sim** ships this as *Replicator*, and Isaac Sim is Apache 2.0.
The GPU it needs can be free too (notebook 1 in this series covers that).

So: free tool, free labels, free compute. This notebook shows the pipeline
end to end, and then spends the second half on the part that gets glossed
over — **synthetic labels are perfect, but synthetic images are not real**,
and that gap decides whether any of this works.
"""),

("code", r'''
import json, os, glob
import numpy as np
import matplotlib.pyplot as plt

DATA = "/kaggle/input/isaac-sim-synthetic-robot-vision"

if os.path.exists(os.path.join(DATA, "dataset_meta.json")):
    meta = json.load(open(os.path.join(DATA, "dataset_meta.json")))
    print(json.dumps(meta, indent=2))
else:
    print("Attach the dataset 'isaac-sim-synthetic-robot-vision' "
          "in the right-hand panel to run this notebook.")
    meta = None
'''),

("md", """
## What Replicator actually generates

The generator script is ~80 lines. The important part is that *randomization
is declarative* — you describe distributions, not loops:

```python
with rep.trigger.on_frame():
    with prop:
        rep.modify.pose(
            position=rep.distribution.uniform((-0.7,-0.7,0.06), (0.7,0.7,0.06)),
            rotation=rep.distribution.uniform((0,-180,0), (0,180,0)),
        )
    rep.create.light(
        intensity=rep.distribution.uniform(2000, 30000),
        temperature=rep.distribution.uniform(2000, 10000),
    )
```

Then attach a writer and say how many frames you want:

```python
writer.initialize(output_dir=out, rgb=True,
                  bounding_box_2d_tight=True,
                  semantic_segmentation=True)
rep.orchestrator.run_until_complete(num_frames=2000)
```

That is the whole API surface for a basic detection dataset. Full source is in
the linked dataset as `gen_synthetic.py`.
"""),

("code", r'''
from PIL import Image

def show_samples(root, n=6):
    imgs = sorted(glob.glob(os.path.join(root, "**", "rgb_*.png"), recursive=True))
    if not imgs:
        print("no images found — is the dataset attached?"); return
    print(f"{len(imgs)} images available")
    idx = np.linspace(0, len(imgs)-1, n).astype(int)
    fig, axes = plt.subplots(2, n//2, figsize=(14, 6))
    for ax, i in zip(axes.ravel(), idx):
        ax.imshow(Image.open(imgs[i])); ax.axis("off")
        ax.set_title(os.path.basename(imgs[i]), fontsize=8)
    plt.suptitle("Isaac Sim rendered frames", y=1.0)
    plt.tight_layout(); plt.show()

if meta: show_samples(DATA)
'''),

("md", """
## The labels are exact

This is the part worth internalizing. A human labeler drawing a box around a
partially occluded cone produces an estimate. The renderer produces the
answer — it knows the geometry, so the "tight" 2D box is exact to the pixel.

Below, boxes are drawn from the generated annotations with no smoothing or
correction of any kind.
"""),

("code", r'''
import matplotlib.patches as patches

def show_boxes(root, n=4):
    imgs = sorted(glob.glob(os.path.join(root, "**", "rgb_*.png"), recursive=True))
    if not imgs: return
    fig, axes = plt.subplots(1, n, figsize=(16, 4.2))
    for ax, p in zip(axes, imgs[:n]):
        ax.imshow(Image.open(p)); ax.axis("off")
        # Replicator's BasicWriter emits a parallel .npy of tight 2D boxes
        bb = p.replace("rgb_", "bounding_box_2d_tight_").replace(".png", ".npy")
        if os.path.exists(bb):
            boxes = np.load(bb, allow_pickle=True)
            for b in boxes:
                x0, y0, x1, y1 = (int(b["x_min"]), int(b["y_min"]),
                                  int(b["x_max"]), int(b["y_max"]))
                ax.add_patch(patches.Rectangle(
                    (x0, y0), x1-x0, y1-y0, fill=False, lw=2, edgecolor="lime"))
    plt.suptitle("Ground truth boxes — generated, not drawn", y=1.02)
    plt.tight_layout(); plt.show()

if meta: show_boxes(DATA)
'''),

("md", """
## Now the catch

Here is what the "free infinite labeled data" pitch leaves out.

**Your labels are perfect. Your images are not.** A model trained on renders
learns the renderer's world: its lighting model, its material shaders, its
noise characteristics (or lack of them), its exact object geometry. Real
cameras have sensor noise, motion blur, chromatic aberration, dust, and
lighting that no one designed.

The result is a model with excellent validation accuracy on held-out synthetic
data and disappointing accuracy on photographs. **Held-out synthetic accuracy
is close to meaningless as a metric** — it mostly measures how well the model
memorized the renderer.

Three things actually close the gap:

1. **Domain randomization** — randomize appearance so hard that reality
   becomes one more sample from the training distribution. Notebook 3 in this
   series measures whether this works, with matched control and treatment
   arms.
2. **Fine-tuning on a small real set** — usually the highest return per hour
   spent. A few hundred real images on top of 10k synthetic often beats either
   alone by a wide margin.
3. **Better rendering** — path tracing, real HDRI environment maps, scanned
   materials. Expensive, and hits diminishing returns fastest.

**Always evaluate on real images.** If your paper, blog post, or internal
report evaluates synthetic-trained models on synthetic test data, it is not
measuring anything anyone cares about.
"""),

("code", r'''
# Quick demonstration of the point above: train briefly, then compare
# accuracy on held-out SYNTHETIC vs on REAL photographs.
import torch, torch.nn as nn
from torch.utils.data import DataLoader, random_split
from torchvision import transforms, models, datasets

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
tf = transforms.Compose([transforms.Resize((128,128)), transforms.ToTensor()])

SYN  = os.path.join(DATA, "images")
REAL = "/kaggle/input/real-objects-testset"

if os.path.isdir(SYN) and os.path.isdir(REAL):
    full = datasets.ImageFolder(SYN, transform=tf)
    n_val = max(1, len(full)//10)
    tr, va = random_split(full, [len(full)-n_val, n_val],
                          generator=torch.Generator().manual_seed(0))
    real = datasets.ImageFolder(REAL, transform=tf)

    model = models.resnet18(weights=None, num_classes=len(full.classes)).to(DEVICE)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
    lossf = nn.CrossEntropyLoss()

    model.train()
    for ep in range(6):
        for x, y in DataLoader(tr, batch_size=64, shuffle=True, num_workers=2):
            x, y = x.to(DEVICE), y.to(DEVICE)
            opt.zero_grad(); loss = lossf(model(x), y); loss.backward(); opt.step()
        print(f"epoch {ep+1} done")

    @torch.no_grad()
    def acc(ds):
        model.eval(); c = t = 0
        for x, y in DataLoader(ds, batch_size=64, num_workers=2):
            x, y = x.to(DEVICE), y.to(DEVICE)
            c += (model(x).argmax(1) == y).sum().item(); t += y.size(0)
        return c / t

    a_syn, a_real = acc(va), acc(real)
    print(f"\nheld-out SYNTHETIC accuracy : {a_syn:.3f}   <- looks great")
    print(f"REAL photograph accuracy    : {a_real:.3f}   <- the number that matters")
    print(f"the sim2real gap            : {a_syn - a_real:+.3f}")
else:
    print("Attach both datasets to run this cell.")
'''),

("md", """
## When synthetic data is genuinely the right call

Not always. Being specific about this is more useful than cheerleading.

**Strong fit:**
- Objects that are **rare or dangerous** to photograph — failure states,
  safety incidents, defective parts
- Labels that are **impossible or impractical** for humans to produce: depth,
  surface normals, amodal (through-occlusion) masks, 6-DoF pose
- **Heavy class imbalance** — generate exactly as many of the rare class as
  you want
- **Before the hardware exists.** You can train perception for a robot that is
  still a CAD file.

**Weak fit:**
- Common objects with big public datasets already available. If COCO covers
  it, use COCO.
- Fine-grained appearance tasks — species, materials, surface defects — where
  the discriminative signal is exactly the part renderers approximate worst
- Anything where you already have plenty of cheap real labeled data

The honest summary: synthetic data is a tool for the cases where real data is
*impossible*, not merely *inconvenient*. When it fits, it fits extremely well.

**Next in the series:** notebook 3 takes the two datasets generated here and
runs a proper controlled experiment on whether domain randomization closes the
gap. If this was useful, an upvote helps — and questions in the comments get
answered.
"""),
]
