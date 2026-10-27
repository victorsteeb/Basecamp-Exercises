# Partner Basecamp · Session Materials

**Prepared for Partner Basecamp participants.** Not for reproduction or redistribution as training material — you're free to apply these patterns in your own client work.

This repository contains all notebooks and supporting files for Partner Basecamp sessions. Materials are organized by day and session in the order they run.

> [!IMPORTANT]
> **Setup is one command.** In a terminal at the repo root (the folder that contains `day1` and `day2`), run:
>
> ```bash
> python3 basecamp_setup.py        # macOS / Linux
> py basecamp_setup.py             # Windows (or: python basecamp_setup.py)
> ```
>
> Follow the prompts: it installs everything, asks for your key, and checks your connection. There's nothing else to install by hand.
>
> **Using an AI coding assistant?** Ask it to "set up this repo". [AGENTS.md](AGENTS.md) tells it to open this script in a terminal window, where you paste your key yourself.

**AI agents:** your instructions for this repo are in [AGENTS.md](AGENTS.md) (Claude Code loads them through [CLAUDE.md](CLAUDE.md)). Read it before setting up or running anything.

---

## How to download

### Option A — Download as ZIP (no Git required)
1. Click the green **Code** button at the top right of this page.
2. Select **Download ZIP**.
3. Unzip the file on your computer — you'll get a `Basecamp-Exercises-main` folder with everything inside.
   Some unzip tools nest it one level deeper (`Basecamp-Exercises-main/Basecamp-Exercises-main/`).
   The folder you want is the one that **directly contains `day1`, `day2` and `basecamp_setup.py`**:
   that's the *repo root* the rest of these instructions refer to.

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
You'll need a key for all build-along sessions: an Anthropic API key, an Amazon Bedrock API key, or a key for your company's gateway. The setup script (below) asks for it and saves it to a gitignored **`.env`** at the repo root. Each notebook's setup cell reads it from there and shows a green **✓ verified** banner when you're connected. The key lives in `.env`, never in a notebook cell (notebooks have a way of ending up in client repos), and one `.env` serves every exercise.

---

## Where to run
These build-alongs are meant to run in your own tooling, not a browser scratchpad — and never by pasting code out of a chat window:

- **VS Code / Cursor** — open the folder, then the notebook (Jupyter extension) or run the `.py` in the terminal.
- **Claude Code (CLI)** — `claude` inside the repo: run the `.py`, or work the exercise with Claude Code as your pair.
- **Claude Desktop** — keep it open alongside as your AI pair for concepts and debugging.

Each session's README has the exact steps.

---

## Setup & troubleshooting

1. **Open the repo root in VS Code:** **File → Open Folder** and choose the folder that directly contains `day1`, `day2` and `basecamp_setup.py` (see "How to download" if your unzip made a nested folder). Not a parent folder, not an exercise folder.
2. **Run the setup once:** open **Terminal → New Terminal** (it starts in the repo root) and run:

```bash
python3 basecamp_setup.py        # macOS / Linux
py basecamp_setup.py             # Windows — or: python basecamp_setup.py if py isn't found
```

It installs [uv](https://docs.astral.sh/uv/) if needed, creates `.venv` with everything the exercises use, registers the **Anthropic Basecamp (.venv)** kernel, asks for your key, and checks the connection. Your system Python is never touched, and no admin rights are needed. If you hit a wall, **[SETUP.md](SETUP.md)** is the one-page fix — it covers the VS Code "wrong kernel" trap, corporate proxies, and Bedrock or gateway keys.

Check the [SETUP.md](SETUP.md) file for troubleshooting, Bedrock and gateway keys, and [the manual setup steps](SETUP.md#if-you-want-to-run-the-steps-manually).
