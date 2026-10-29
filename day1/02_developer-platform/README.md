# Developer Platform · Build-Along

**Prepared for Partner Basecamp participants.** Not for reproduction or redistribution as training material — you're free to apply these patterns in your own client work.

## What you're building
A multi-tool support ticket agent for TechFlow, a B2B SaaS company processing 500+ tickets per day. The agent reads ticket details, searches a knowledge base, and produces a structured resolution — using the Claude API directly with no framework.

## Main learning
How to build an agentic loop with tool use using the Claude API. You'll define tool schemas, handle multi-step tool calls, and use Claude Sonnet 5's adaptive thinking to let the model reason through complex ticket triage automatically.

---

## How to run

Work the exercise in the repo — don't copy code out of a chat window. First time on this machine? From the repo root (the folder that contains `day1` and `day2`), run `python3 basecamp_setup.py` once (Windows: `py basecamp_setup.py`) — it installs everything and saves your key (see [SETUP.md](../../SETUP.md)). Then pick a surface:

### VS Code / Cursor (recommended)

1. **File → Open Folder** and select the repo root — the folder that contains `day1` and `day2` (after unzipping, check it isn't nested one level down) — then open this exercise's folder in the Explorer.
2. Install the **Python** and **Jupyter** extensions if prompted.
3. Open [`Developer_Platform.ipynb`](Developer_Platform.ipynb) and pick the **Anthropic Basecamp (.venv)** kernel — run cells with **Shift+Enter** or **Run All**. This is a build-along: implement the ✏️ stubs as the session goes and re-run as you build.

### Claude Code (CLI)

`cd` into this folder and pair with Claude Code on the exercise:

```bash
cd day1/02_developer-platform
claude                            # work the exercise with Claude Code as your pair
```

### Claude Desktop

Keep it open alongside as your AI pair — ask it to explain a cell, debug an error, or suggest the next change while you edit.

The setup cell reads your key from the repo's `.env` (or your shell) and verifies it with a real API call — never paste a key into a cell.
