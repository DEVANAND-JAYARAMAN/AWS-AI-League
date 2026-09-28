# AWS AI League — Competition Playbook

Your one-page battle plan. Follow it top to bottom. Decisions are already made
for you; where you see **[DECIDED]** you don't need to think, just do it.

---

## The one idea that wins this

The leaderboard does **not** look at any of your football code. It does one thing:
it sends **hidden questions** to your fine-tuned Nova Micro model (with **no system
prompt**) and scores the **answers**.

So the whole game is: **the quality and relevance of your training dataset.**

Two hard rules from the guide that decide everything:

1. **Match the challenge topic.** A dataset about the wrong subject scores near
   zero, no matter how clean it is. You get the topic at the briefing / when the
   environment opens.
2. **Behaviour, not facts.** Fine-tuning teaches *how* to answer — format, tone,
   length, structure, how to handle a question it can't answer. It does **not**
   reliably teach new facts. Write answers that model the *style* the challenge
   rewards, consistently.

---

## Timeline (JST)

| When | What you do |
|---|---|
| **Mon Sep 28, 9:00 AM** | Briefing. **Write down the exact challenge topic + how it's scored.** Tell me. |
| **Tue Sep 29, 9:00 AM** | Environment opens. Join event, copy `AwsAccountId` + `AccountAuthorizationCode`. Do the **first full run** (baseline on the board). |
| **Tue–Thu** | Iterate: better data → retrain → redeploy → resubmit. ~1 hour per loop. Office hours 3–4 PM. |
| **Thu Oct 1, 5:00 PM** | Build window closes. **Have your best model submitted well before this.** |

---

## Day 0 (now / after briefing): build the dataset

**The moment you know the topic, tell me the topic and how answers are scored.**
Then we do this together, here in the editor:

1. I generate 100–300 varied, on-topic question/answer pairs into
   `competition/data/qa_source.json` (you don't hand-write these).
2. Build + validate in one command:

   ```powershell
   python -m competition.build_dataset
   ```

   This writes `competition/data/dataset.jsonl` and prints a validation report.
   **Do not upload anything until it says `RESULT: READY`** and the record count
   is **at least 100** (aim for 200–400).

3. Download / locate `competition/data/dataset.jsonl` — that single file is what
   you upload in Module 1.

To re-check any `.jsonl` you were handed:

```powershell
python -m competition.build_dataset --check path\to\file.jsonl
```

### What "good data" looks like (from the guide)
- **~200–400 examples**, not thousands. Returns flatten past ~500.
- **Diverse**: vary question types (factual, recommendation, comparison,
  planning, practical), lengths (1–2, 2–3, 3–4 sentences), and phrasing.
- **Consistent voice** across every answer. Same tone, same format.
- **Accurate**: a confidently wrong answer teaches the model to be confidently
  wrong. Review generated content before training.
- **Self-contained answers**: since there's no system prompt at scoring time,
  the behaviour must be visible in the answers themselves.

---

## Module 1 — Train (SageMaker Studio, ~20–25 min) **[all clicks]**

1. AWS Console → search **Amazon SageMaker AI** → left menu **SageMaker Studio**
   → profile **AILeagueUser** → **Open Studio** → **Skip Tour**.
2. Left menu → **Models** → **JumpStart models** → search **Nova Micro** →
   open the **Nova Micro** card.
3. Top-right **Customize model** → **Customize with UI**.
4. Settings:
   - **Custom model name**: `model-01` (bump the number each run: `model-02`, …).
   - **Base model**: Nova Micro **[DECIDED — verify it says Nova Micro]**
   - **Customization technique**: Supervised Fine-Tuning **[DECIDED — leave]**
   - **Training type**: LoRA **[DECIDED — leave]**
   - **Sequence length**: 8K **[DECIDED — leave]**
5. **Dataset and output** → **Upload files** → pick your `dataset.jsonl` →
   **Save** → **Dataset name** `dataset-01` (letters/numbers/hyphens only) → **Create**.
6. **Output artifact location**: leave the pre-filled S3 path **[DECIDED]**.
7. **Compute** → verify **Run on SageMaker Training jobs** **[DECIDED]**.
8. **MLflow** (under Advanced options) is **required** — make sure the tracking
   server is **not** still "Creating", or the job fails.
9. **Hyperparameters** — for the **first** run, use the guide's defensible start:

   | Field | First run | Why |
   |---|---|---|
   | Warmup steps | **1** | Critical on small data — the default 10 can be longer than the whole run, so the learning rate never arrives |
   | Learning rate | **0.00005** (5e-5) | AWS's recommended LoRA rate |
   | Minimum learning rate | **0.000001** (1e-6) | must stay **below** learning rate |
   | Number of epochs | **3** | small datasets need more passes (AWS ceiling ~5) |
   | Batch size | **64** | the minimum → the most training steps |
   | Alpha | **128** | leave default |
   | Max context length | **8192** | leave default |

   > If you're nervous on the very first submit, you can instead leave **all**
   > defaults and just get *a* model on the board — then switch to the table
   > above on run 2. Either is fine.
10. **Submit**. Status shows **In progress** (~20–25 min). Wait for **Completed**.
11. Click **View custom model** → go to Module 2.

---

## Module 2 — Deploy to Bedrock (~10–15 min) **[all clicks]**

1. On the custom model page → **Actions** → **Deploy with Bedrock**.
   > **Not** "Deploy with SageMaker" — a SageMaker endpoint is rejected at submission.
2. In the dialog: **On-Demand** **[DECIDED — leave]**, **Deployment name**
   `deployment-01` (A–Z, 0–9, `_`, `-`), IAM role `SageMakerExecutionRole`
   **[DECIDED — leave]** → **Deploy**.
3. Wait for status **In Service** (~10–15 min).
4. **View details** → copy the **Deployment ARN**.
   > ⚠️ Copy the **Deployment ARN**, not the Model ARN. The right one contains
   > `custom-model-deployment/`. The wrong one contains `custom-model/imported/`
   > and will fail scoring.
5. *(Optional but smart)* Use the **Playground** on that page to ask a few
   challenge-style questions and see how it answers before you submit.

---

## Module 3 — Register & Submit **[all clicks]**

1. Go to the **AWS AI League Leaderboard** site → **Sign in with AWS Builder ID**.
2. Join the leaderboard: enter **Event ID** (the event code), your **AWS Account
   ID**, the **Authorization Code** (the 32-char one from the event outputs), and
   a profile name → **Join**.
3. **Artifact Management** → **Register New Artifact**:
   - **Model Name**: `model-01`
   - **Deployment ARN**: paste the `custom-model-deployment/...` ARN → **Register**.
4. **Leaderboard Submission** → **Submit your artifact** → pick your artifact →
   **Next** → review → **Submit**. Score posts within ~15 minutes.

**That's a full loop.** You now have a baseline on the board.

---

## Module 4 — Climb (the iterate loop)

Each loop is ~1 hour (train + deploy + score). You can run **2 training jobs at
once**. Plan **3–4 deliberate experiments**, not twenty. **Change one thing per
run and write down what it did.**

**Order of changes, biggest lever first:**

1. **The dataset** — by far the biggest lever. First, open your deployment in the
   Bedrock **Playground** and find *how* it fails (wrong subject? wrong format?
   too long/short? makes things up?). Fix *that* in the data. Tell me what you see
   and I'll generate targeted examples. Grow the set deliberately (e.g. 200 → 350).
2. **Warmup steps → 1** (if you hadn't already).
3. **Learning rate → 5e-5** (if loss in MLflow is jumpy, drop to 5e-6 instead).
4. **Epochs → 3–5** (small data needs more passes; too many = memorising).
5. **Alpha → 160 or 192** if tuning barely registered; **→ 64** if answers went
   incoherent.
6. Leave batch size at 64, and leave context length / sequence length alone.

**Read the MLflow loss curve** (open the run for your training job):
- Still falling at the end → learned more is possible: more epochs / higher LR.
- Flat → nothing learned: LR too low, or warmup ate the run (set warmup 1–2).
- Spiky → LR too high: cut it.
- Falls fast then flat → converged: don't add epochs.

**Experiment log — copy this and fill one row per run:**

| Run | Dataset rows | Epochs | LR | Min LR | Batch | Alpha | Warmup | Score | MLflow loss note |
|---|---|---|---|---|---|---|---|---|---|
| 1 (baseline) | | 3 | 5e-5 | 1e-6 | 64 | 128 | 1 | | |
| 2 | | | | | | | | | |
| 3 | | | | | | | | | |

---

## Gotchas (each one has bitten people)

- **`schemaVersion` must be exactly** `bedrock-conversation-2024`. Our tool sets it.
- **Reserved strings fail the job** if they appear in any user/system text:
  `User:` `Bot:` `Assistant:` `System:` `<image>` `<video>` `[EOS]`. Our validator
  catches these.
- **Minimum 100 records** or training fails. Aim 200–400. Our validator warns.
- **Deployment ARN, not Model ARN.** (`custom-model-deployment/`)
- **Deploy with Bedrock, not SageMaker.**
- **MLflow tracking server** must be ready before you submit the training job.
- **Unique names** every run: `model-02`, `dataset-02`, `deployment-02`, …
- **Don't use your personal AWS credits/account** — the workshop runs entirely
  inside the provisioned account they give you (us-east-1).

---

## The 30-second version

1. Briefing → tell me the **topic**.
2. I generate on-topic Q/A → `python -m competition.build_dataset` → get
   `dataset.jsonl` that says **READY**.
3. SageMaker: Nova Micro → Customize with UI → upload dataset → warmup 1 / LR 5e-5
   / epochs 3 / batch 64 → Submit → wait for Completed.
4. Deploy with Bedrock (On-Demand) → copy the **Deployment ARN**.
5. Leaderboard: Register artifact → Submit. Baseline on the board.
6. Playground shows how it fails → fix the data → repeat. Best model in before
   **Thu 5:00 PM JST**.
