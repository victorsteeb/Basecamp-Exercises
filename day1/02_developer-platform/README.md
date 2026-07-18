# Developer Platform · Build-Along

## What you're building
A multi-tool support ticket agent for TechFlow, a B2B SaaS company processing 500+ tickets per day. The agent reads ticket details, searches a knowledge base, and produces a structured resolution — using the Claude API directly with no framework.

## Main learning
How to build an agentic loop with tool use using the Claude API. You'll define tool schemas, handle multi-step tool calls, and use Claude Sonnet 5's adaptive thinking to let the model reason through complex ticket triage automatically.

---

## How to run

Work the exercise in the repo — don't copy code out of a chat window. Set your key once, then pick a surface:

```bash
export ANTHROPIC_API_KEY=your_key_here   # your shell, the VS Code terminal, or a local .env
```

Running the notebook? You can skip the export — the setup cell prompts for your key with a hidden input box and confirms it with a green "✓ API key verified" banner.

### VS Code / Cursor (recommended)

1. **File → Open Folder** and select this folder.
2. Install the **Python** and **Jupyter** extensions if prompted.
3. Open [`Developer_Platform.ipynb`](Developer_Platform.ipynb) and pick a **Python 3** kernel — run cells with **Shift+Enter** or **Run All**. This is a build-along: implement the ✏️ stubs as the session goes and re-run as you build.

### Claude Code (CLI)

`cd` into this folder and pair with Claude Code on the exercise:

```bash
cd day1/02_developer-platform
claude                            # work the exercise with Claude Code as your pair
```

### Claude Desktop

Keep it open alongside as your AI pair — ask it to explain a cell, debug an error, or suggest the next change while you edit.

The setup cell reads `ANTHROPIC_API_KEY` from your environment (with a hidden-prompt fallback) — never paste a key into a cell.
