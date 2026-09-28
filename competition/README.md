# competition/ — AWS AI League dataset toolkit

Turns plain question/answer pairs into a valid **Amazon Nova Micro** fine-tuning
dataset (`bedrock-conversation-2024` JSONL) and validates it against every rule
the workshop says can fail a training job.

Standalone — it does **not** touch the football code under `app/`.

## Use it

1. Put your Q/A pairs in `data/qa_source.json`:

   ```json
   {
     "system_prompt": "You are a concise, helpful assistant.",
     "pairs": [
       {"question": "…", "answer": "…"}
     ]
   }
   ```

   `system_prompt` is optional and is **not** sent at scoring time — put the
   behaviour you want scored into the answers.

2. Build + validate:

   ```powershell
   python -m competition.build_dataset
   ```

   Writes `data/dataset.jsonl` and prints a report. Upload only when it says
   **READY** and the count is **>= 100** (aim 200–400).

3. Validate an existing file:

   ```powershell
   python -m competition.build_dataset --check data/dataset.jsonl
   ```

## Files

| File | Purpose |
|---|---|
| `format.py` | Build records + read/write JSONL |
| `validate.py` | Enforce all workshop rules |
| `build_dataset.py` | CLI (build / check) |
| `data/qa_source.json` | Your editable Q/A source (currently neutral placeholder data) |
| `data/dataset.jsonl` | Generated upload file |

See `../COMPETITION_PLAYBOOK.md` for the full click-by-click competition guide.
