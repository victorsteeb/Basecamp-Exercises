# Helios RFP Agent — Multi-Agent Build

Multi-agent RFP responder for Helios Security · built for the Day 2 Agent Hackathon.

## What this is

A five-agent team — **Parser → Retriever → Drafter → Validator → Reviser** — that turns an unseen RFP into a structured, cited, internally-consistent response. The notebook is the explainer and the source of truth for the agent code; `helios_agent.html` is a self-contained, Bounteous-branded browser UI that runs the same pipeline with no backend. Robustness is the grading bar: the agent has to handle an RFP it wasn't developed against without fabricating answers or stalling on a bad input. The Validator + bounded Reviser pass is what separates this from a single-shot draft.

## Architecture

```
RFP text ─▶ Parser ─▶ Retriever ─▶ Drafter ─▶ Validator ─┐
                                       ▲                 │
                                       └── Reviser ◀─────┘
                                             (≤1 pass)
```

Model assignment:

| Agent | Model | Why |
|---|---|---|
| Parser | `claude-haiku-4-5` | Cheap, structured extraction |
| Retriever | `claude-haiku-4-5` | Tool-loop over KB; low-stakes |
| Drafter | `claude-sonnet-4-6` | Judgment + citation discipline |
| Validator | `claude-sonnet-4-6` | Cross-answer consistency |
| Reviser | `claude-sonnet-4-6` | Re-draft against critique |

Haiku on Parser + Retriever cuts ~4× off the chatty stages without giving up draft quality.

## Two ways to use it

- **Browser** (`helios_agent.html`): open in Chrome or Safari, paste your Anthropic API key, paste an RFP (or load a baked-in sample), hit **Run**. The dashboard streams per-question cards (pending → retrieving → drafting → validating → revised → final) and a live trace pane logs every agent turn. Export JSON when done.
- **Notebook** (`Agent_Engineering_Challenge.ipynb`): runs the same pipeline in Python. Use this to inspect prompts, extend the knowledge base, run the eval harness, or regenerate `helios_agent.html` from the export cell.

## Failure-mode coverage

| Failure mode | What the agent does |
|---|---|
| Malformed RFP | Parser falls back to blank-line chunking and marks `parse_quality: low`; run continues. |
| KB miss | Retriever sets `kb_gap: true`; Drafter answers narratively about the gap with `confidence: low` and `flag: "kb-gap"`. Never fabricates numbers. |
| Anthropic 4xx/5xx | That stage's card flips red; other questions continue in parallel. One bad question never blocks the run. |
| Bad JSON from any agent | 3-tier extract: `JSON.parse` → regex `\{[\s\S]*\}` → raw-response capture with `parse_error: true`. |
| Validator contradiction | 1 revision pass; if still unresolved, ship with `flags: ["unresolved-contradiction"]` rather than spin. |
| Missing/bad API key | Fail fast at **Run** click with inline error. No half-started dashboard state. |

## What's in this folder

| File | What it is |
|---|---|
| `helios_agent.html` | Self-contained browser UI. KB, prompts, samples, brand tokens all baked in. |
| `Agent_Engineering_Challenge.ipynb` | Hackathon notebook — agent definitions, synthetic RFPs, eval harness, HTML export cell. |
| `README.md` | This file. |

## What to show off

- **Live trace pane** in `helios_agent.html` — every agent turn timestamped with role, target question, outcome, latency.
- **Validator catching a planted contradiction** on the adversarial synthetic RFP (notebook Part 7, RFP `e`) — watch a Q get flagged and revised in one pass.
- **`kb_gap` handling** on the edge-case RFP — Drafter writes a narrative "we don't have this on file" answer with `confidence: low` instead of inventing a number.

---

## How to run

### Option 1 — GitHub Codespaces (no local install needed)

1. Go to the repo on GitHub and click the green **Code** button.
2. Select the **Codespaces** tab and click **Create codespace on main**.
3. Wait for the environment to load (takes about a minute).
4. Open `day2/04_agent-build-hackathon/Agent_Engineering_Challenge.ipynb`.
5. When prompted to select a kernel, choose **Python 3**.
6. In the API key cell, paste your key between the quotes.
7. Run cells with **Shift+Enter** or use **Run All** from the top menu.

---

### Option 2 — VS Code locally

1. Open VS Code and go to **File → Open Folder**, select this folder.
2. Install the **Python** and **Jupyter** extensions if prompted.
3. Open `Agent_Engineering_Challenge.ipynb` and select your Python environment as the kernel.
4. Open a terminal (**Terminal → New Terminal**) and set your API key:
   ```bash
   export ANTHROPIC_API_KEY=your_key_here
   ```
5. Run cells with **Shift+Enter** or click **Run All**.

---

### Option 3 — Jupyter locally

1. Install Jupyter if needed: `pip install notebook`
2. Open a terminal, navigate to this folder, and set your API key:
   ```bash
   export ANTHROPIC_API_KEY=your_key_here
   cd path/to/day2/04_agent-build-hackathon
   jupyter notebook Agent_Engineering_Challenge.ipynb
   ```
3. Run cells with **Shift+Enter** or use **Cell → Run All**.
