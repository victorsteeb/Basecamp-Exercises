# Evals · Build-Along

## What you're building
An eval suite for `boutique`, a simple AI shopping assistant that looks up product prices and does math. The agent works — mostly. Your job is to figure out exactly where it breaks, why, and how to fix it using a systematic eval-driven approach.

## Main learning
How to build evals for AI agents: defining test tasks, writing graders, running the harness, and using results to make targeted improvements. You'll move from "try it and see" to a repeatable feedback loop you can point to with numbers before shipping to a customer.

---

## How to run

Work the exercise in the repo — don't copy code out of a chat window. No terminal setup needed: the **Setup — connect to Claude** cell at the top asks for your API key with a hidden prompt and shows a green **"✓ API key verified"** banner once you're connected. (If `ANTHROPIC_API_KEY` is already set in your environment, it's picked up automatically.)

### VS Code / Cursor (recommended)

1. **File → Open Folder** and select this folder.
2. Install the **Python** and **Jupyter** extensions if prompted.
3. Open [`Building_an_Eval.ipynb`](Building_an_Eval.ipynb) and pick a **Python 3** kernel — run cells with **Shift+Enter**, or **Run All** (the chat cell starts an interactive session automatically; type `quit` to move past it, or set `INTERACTIVE_CHAT = False` in that cell first to skip straight to the eval sections).
4. Prefer the terminal? Run it straight through: `python3 Building_an_Eval.py`.

### Claude Code (CLI)

`cd` into this folder, then run it end to end or pair with Claude Code on the exercise:

```bash
cd day2/01_evals
python3 Building_an_Eval.py     # run straight through
claude                          # …or work the exercise with Claude Code as your pair
```

### Claude Desktop

Keep it open alongside as your AI pair — ask it to explain a cell, debug an error, or suggest the next change while you edit.

The setup cell verifies your key with a real API call — green banner means you're connected. Never paste a key into a cell.
