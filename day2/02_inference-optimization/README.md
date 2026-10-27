# Inference Optimization · **The Margin Call** · Build-Along

**Prepared for Partner Basecamp participants.** Not for reproduction or redistribution as training material — you're free to apply these patterns in your own client work.

## What you're doing
You inherit **ClauseScan v0** — a contract-diligence agent your firm's demo team built the
night before a winning pitch. It reviews supplier contracts for a private-equity client's
acquisition (248,000-document estate, signed SLA: accuracy ≥ 90%, p50 ≤ 5s interactive,
COGS ≤ $0.02/contract). v0 is *accurate* — and slow and expensive enough to eat the
engagement margin.

The lab runs in three acts:

1. **Instrument & baseline (Parts 1–2).** Build the measurement toolkit — TTFT, TTC, OTPS,
   and *cache-aware* cost — and run the initial tests across Haiku, Sonnet, and Opus.
2. **Diagnose & learn the levers (Parts 3–4).** Run v0, read the scorecard, then work six
   optimization levers one at a time with the meter running: **prompt caching · model
   routing · structured outputs & output discipline · round-trip collapse + streaming ·
   parallelism with cache warming · two-speed (Batch API) architecture.**
3. **The optimization sprint (Parts 5–6).** Rebuild the pipeline against a scored
   leaderboard — accuracy-gated, so fast-but-wrong scores zero — verify on a holdout set,
   and auto-generate the before/after steering-committee slide with stated assumptions.

## Main learning
How to take an AI workload from "works in the demo" to "defensible at the steering
committee": measure first, optimize against an accuracy gate, and translate token economics
into engagement economics (unit COGS, SLA compliance, margin). Every lever maps to a
conversation you will have on a real client engagement.

**Scoring:** `SCORE = 50 × (baseline $ / your $) + 50 × (baseline p50 / your p50)`, zeroed
if accuracy drops below 90%. v0 indexes at 100. Post your leaderboard line in the session
chat; a strong configuration clears 400.

> 💸 Budget note: running every cell costs roughly **$2–4** of API usage — most of it in the
> deliberately wasteful v0 baseline. That is part of the lesson.

---

## How to run

Work the exercise in the repo — don't copy code out of a chat window. Set your key once, then pick a surface:

```bash
export ANTHROPIC_API_KEY=your_key_here   # your shell, the VS Code terminal, or a local .env
```

### VS Code / Cursor (recommended)

1. **File → Open Folder** and select this folder.
2. Install the **Python** and **Jupyter** extensions if prompted.
3. Open [`Inference_Optimization.ipynb`](Inference_Optimization.ipynb) and pick a **Python 3** kernel — run cells with **Shift+Enter** or **Run All**. The notebook is built to survive **Run All** end to end.
4. Prefer the terminal? Run it straight through: `python3 Inference_Optimization.py`.

### Claude Code (CLI)

`cd` into this folder, then run it end to end or pair with Claude Code on the exercise:

```bash
cd day2/02_inference-optimization
python3 Inference_Optimization.py     # run straight through
claude                                # …or work the exercise with Claude Code as your pair
```

### Claude Desktop

Keep it open alongside as your AI pair — ask it to explain a cell, debug an error, or suggest the next change while you edit.

The setup cell reads `ANTHROPIC_API_KEY` from your environment (with a hidden-prompt fallback) — never paste a key into a cell.

---

## Files

| File | What it is |
|---|---|
| `Inference_Optimization.ipynb` | The build-along notebook (run this) |
| `Inference_Optimization.py` | Canonical source in jupytext percent format — the notebook is generated from it, so the two cannot drift. Runnable as a plain script too. |
