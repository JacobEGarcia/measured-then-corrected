# Account checklist — the only part I cannot do for you

Creating accounts requires entering passwords, so these four are yours.
Budget ~15 minutes total. Everything downstream is automated.

## 1. Kaggle — kaggle.com
- [ ] Sign up (Google SSO is fastest)
- [ ] **Phone-verify** (Settings -> Phone Verification). Without this you cannot
      use the GPU quota *or* reach Contributor tier.
- [ ] Complete Contributor checklist — see PROGRESS.md Step 0
- [ ] Create an API token: Settings -> API -> "Create New Token".
      Save the downloaded file to `~/.kaggle/kaggle.json`, then:

          chmod 600 ~/.kaggle/kaggle.json

      That token lets me push notebooks and datasets by CLI. I will still
      confirm with you before each public publish.

Note: GPU quota is 30 hr/week and resets Saturday 00:00 UTC. Sessions cap at
12 hours. Turn **Internet ON** in notebook settings — Isaac Sim pulls assets
from NVIDIA servers at runtime and pip needs the NVIDIA index.

## 2. Lightning AI — lightning.ai
- [ ] Sign up (no credit card required)
- [ ] Create a Studio, switch it to a **GPU** machine (T4 is the credit-efficient
      choice; L4/L40S burn credits far faster)
- [ ] Free tier: 80 GPU hours/month = 15 credits. On T4 that is ~22 hr.
- [ ] Note the SSH command from the Studio UI and paste it to me — then I can
      drive the box directly.

## 3. Google / Colab — colab.research.google.com
- [ ] Any Google account works. Nothing to configure.
- [ ] Runtime -> Change runtime type -> T4 GPU (best-effort on free tier)

## 4. NVIDIA Developer — developer.nvidia.com
- [ ] Free NVIDIA Developer account
- [ ] Enroll in the free DLI courses listed in `setup/04-dli.md`

## After you finish

Tell me which of the four are live and paste the Lightning SSH string. I will
verify each environment end-to-end before we publish anything.
