# Prompt Rescue · Build-Along

## What you're doing
You've been pulled in as a technical consultant for TechSupport Corp. They have a production prompt that processes support tickets — classifying priority, extracting entities, and drafting responses. It works on clean inputs but fails badly on messy real-world tickets. Their renewal meeting is in 48 hours. Your job: rescue the prompt.

## Main learning
How to systematically diagnose and fix a broken prompt. You'll study failure cases, identify root causes (wrong priority classification, hallucinated entities, broken JSON output), and iterate using a built-in eval harness that scores your fixes against a set of real-world test cases.

---

## How to run

Work the exercise in the repo — don't copy code out of a chat window. Pick a surface below — the setup cell asks for your API key (hidden input) and verifies the connection, so no terminal needed. Optionally, set the key once so you're never prompted:

```bash
export ANTHROPIC_API_KEY=your_key_here   # your shell, the VS Code terminal, or a local .env
```

### VS Code / Cursor (recommended)

1. **File → Open Folder** and select this folder.
2. Install the **Python** and **Jupyter** extensions if prompted.
3. Open [`Prompt_Rescue_solo.ipynb`](Prompt_Rescue_solo.ipynb) and pick a **Python 3** kernel — run cells with **Shift+Enter** or **Run All**.

### Claude Code (CLI)

`cd` into this folder and pair with Claude Code on the exercise:

```bash
cd day1/03_prompt-rescue
claude                            # work the exercise with Claude Code as your pair
```

### Claude Desktop

Keep it open alongside as your AI pair — ask it to explain a cell, debug an error, or suggest the next change while you edit.

The setup cell reads `ANTHROPIC_API_KEY` from your environment (with a hidden-prompt fallback), verifies it with a real API call, and shows a green **✓ API key verified** banner when you're connected — never paste a key into a cell.
