# AGENTS.md

Instructions for AI coding agents (Claude Code, GitHub Copilot, Cursor, Codex, Gemini CLI, …)
working in this repo. People: start with [README.md](README.md).

## What this repo is

Training exercises for Partner Basecamp: Jupyter notebooks and Python scripts under `day1/`
and `day2/`. The person you're helping is a participant. Each exercise folder has a README,
and some have their own agent notes (for example `day1/04_diagnosing-ai-problems/CLAUDE.md`)
that take precedence inside that folder.

## Setup is one script, run by the user in a terminal they can see

`basecamp_setup.py` at the repo root (the folder that contains `day1` and `day2`) does all of
the setup: it installs uv, builds `.venv`, registers the "Anthropic Basecamp (.venv)" kernel,
asks for the user's key, saves it to `.env`, tests certificates, and checks the connection.

Use this procedure when the user asks to set up the repo, or when a notebook or script stops
with "📦 Packages missing" or "📋 Add your credentials to continue":

1. **Don't run the script in your own shell, and don't do the setup another way.** The
   script asks for the key interactively, and your shell can't take the user's input. No
   `pip install`, no hand-made venv, no writing a key into `.env` yourself.
2. **Open a new terminal window that runs it**, so the user sees it and can type into it.
   Replace `<repo-root>` with the repo root's absolute path:
   - **Windows** (works from PowerShell, cmd or Git Bash):
     ```
     powershell -NoProfile -Command "Start-Process powershell -WorkingDirectory '<repo-root>' -ArgumentList '-NoExit','-Command','py basecamp_setup.py'"
     ```
     If the `py` launcher isn't installed, use `python basecamp_setup.py` instead.
   - **macOS** (the first time, macOS may ask the user to allow controlling Terminal):
     ```
     osascript -e 'tell application "Terminal" to activate' -e 'tell application "Terminal" to do script "cd " & quoted form of "<repo-root>" & " && python3 basecamp_setup.py"'
     ```
   - **Linux:**
     ```
     x-terminal-emulator -e bash -c 'cd "<repo-root>" && python3 basecamp_setup.py; exec bash'
     ```
   If you can't open a window, ask the user to run it themselves: in VS Code,
   **Terminal → New Terminal**, then `py basecamp_setup.py` (Windows) or
   `python3 basecamp_setup.py` (macOS / Linux).
3. **Tell the user what to do there:** paste the key into that terminal window when it asks,
   never into this chat; press Enter to accept the suggested defaults; reply here when it
   says "You're all set!".
4. **Verify once they reply**, from the repo root. This prints the connection result and
   never the key:
   ```
   uv run --no-sync python -c "import basecamp_setup; basecamp_setup.connect()"
   ```
   A line starting with ✓ means connected. Otherwise relay its message: it names the fix.

Running `basecamp_setup.py` in your own shell is fine only when `.env` already holds a key
(for example, to reinstall packages): with no terminal attached, it skips the questions and
keeps `.env` as it is.

## Certificates

If a notebook or the check above reports a certificate error, run
`python3 basecamp_setup.py --check-tls` (Windows: `py basecamp_setup.py --check-tls`) from
the repo root. It asks nothing, so you can run it yourself. It tests which certificates
reach the Claude endpoint and records the answer in `.env` as `BASECAMP_TLS`; then have the
user re-run the notebook's setup cell.

Never turn off certificate verification, and never change the user's global environment
(`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, shell profiles, Windows environment variables) to
work around an error: other tools on the machine depend on them. The script handles these
cases for the exercises only.

## Keys and `.env`

- Never ask the user to paste a key into chat, and never print, quote or commit values from
  `.env`. Checking whether a variable name is present is fine.
- `.env` is gitignored; `.env.example` is the template and documents every option.

## Running the exercises

- Notebooks use the **Anthropic Basecamp (.venv)** kernel; their first code cell calls
  `connect()` from `basecamp_setup.py`, which reads `.env` fresh on every run.
- Scripts run with `uv run python <script>.py` from the exercise folder.
- Troubleshooting for people, including corporate networks and gateway keys:
  [SETUP.md](SETUP.md).
