# Partner Basecamp · Session Materials

**Prepared for Partner Basecamp participants.** Not for reproduction or redistribution as training material — you're free to apply these patterns in your own client work.

This repository contains all notebooks and supporting files for Partner Basecamp sessions. Materials are organized by day and session in the order they run.

---

## How to download

### Option A — Download as ZIP (no Git required)
1. Click the green **Code** button at the top right of this page.
2. Select **Download ZIP**.
3. Unzip the file on your computer — you'll get a `Basecamp-Exercises-main` folder with everything inside.

### Option B — Clone with Git
```bash
git clone https://github.com/victorsteeb/Basecamp-Exercises.git
```

---

---

> ### ⚠️ Run these locally — not in OneDrive, Dropbox, or iCloud Drive
>
> These exercises run **on your machine**: a local Python environment, local files, a local
> Git repo. Cloud-sync folders aren't a normal local folder, and putting the exercises in
> one will break them. Unzip or clone somewhere plain instead — `C:\dev\`, `~/projects/`,
> your Desktop.
>
> The reason is literal, not just cautionary. With OneDrive's **Files On-Demand**, your
> files may not actually be on the disk — they're placeholders that download when opened.
> A notebook that looks fine in Explorer can be read as truncated, and saving over it
> destroys the real content, silently. On top of that, sync fights the things setup
> creates: it locks the thousands of small files in `.venv` mid-install, and it can corrupt
> a `.git` folder outright — Microsoft's own tooling warns about exactly this.
>
> One more, worth knowing: your API key lives in a gitignored `.env`. `.gitignore` keeps it
> out of Git. It does **nothing** to stop OneDrive uploading it to corporate cloud storage.
>
> **Already unzipped into OneDrive?** Move the folder somewhere local, delete `.venv`, and
> redo setup. Don't try to repair it in place.

---

## What's inside

### Day 1
| Folder | Session | Type |
|--------|---------|------|
| `day1/01_claude-code-workshop` | Claude Code Workshop | Offline guide |
| `day1/02_developer-platform` | Developer Platform | Build-Along |
| `day1/03_prompt-rescue` | Prompt Rescue | Build-Along |
| `day1/04_diagnosing-ai-problems` | Diagnosing AI Problems | Session materials |

### Day 2
| Folder | Session | Type |
|--------|---------|------|
| `day2/01_evals` | Evals | Build-Along |
| `day2/02_inference-optimization` | Inference Optimization | Build-Along |

Each folder has its own README with the exercise description and step-by-step run instructions.

---

## API key
You'll need an Anthropic API key for all build-along sessions — and you don't need a terminal to set it. Run the notebook's setup cell once: it creates a gitignored **`.env`** file. Open it, paste your key after `ANTHROPIC_API_KEY=`, save, and re-run — a green **"✓ API key verified"** banner confirms you're connected. The key lives in `.env`, never in a notebook cell (notebooks have a way of ending up in client repos), it survives kernel restarts, and a single `.env` at the repo root serves every exercise.

Prefer to set it once for everything? That works too:

```bash
export ANTHROPIC_API_KEY=your_key_here   # your shell, the VS Code terminal, or a local .env
```

---

## Where to run
These build-alongs are meant to run in your own tooling, not a browser scratchpad — and never by pasting code out of a chat window:

- **VS Code / Cursor** — open the folder, then the notebook (Jupyter extension) or run the `.py` in the terminal.
- **Claude Code (CLI)** — `claude` inside the repo: run the `.py`, or work the exercise with Claude Code as your pair.
- **Claude Desktop** — keep it open alongside as your AI pair for concepts and debugging.

Each session's README has the exact steps.

---

## Setup & troubleshooting

The notebooks install what they need on first run and survive locked-down corporate Pythons
(the `externally-managed-environment` / PEP 668 error, no-admin machines, proxies). If you hit
a wall, **[SETUP.md](SETUP.md)** is the one-page fix — it covers the venv path, the VS Code
"wrong kernel" trap, and corporate-proxy installs. For a pinned environment up front:

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
