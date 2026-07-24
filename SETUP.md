# Setup & Troubleshooting

One page to get any laptop — including a locked-down corporate one — running the
Basecamp notebooks. **The fastest reliable path is a virtual environment in VS Code.**

---

## The 4-command setup (do this once)

```bash
python3 -m venv .venv                 # create an isolated environment
source .venv/bin/activate             # macOS/Linux  (Windows: .venv\Scripts\activate)
pip install -r requirements.txt       # install everything the exercises need
export ANTHROPIC_API_KEY=sk-ant-...   # your key (Windows PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-...")
```

Then open any `.ipynb` in VS Code and **select the `.venv` interpreter as the kernel**
(see "Wrong kernel" below). Run the first cell — you should see `✓ Dependencies ready`
followed by `✓ API key verified`.

> The venv isn't optional anymore — every notebook now refuses to run on a bare system
> Python (see "Why the notebook just stopped" below). It's still the one setup that
> sidesteps *every* problem on this page at once.

---

## Why the notebook just stopped

Every notebook now checks, in its very first code cell, whether it's running inside
an isolated environment (a `.venv` or a conda env) before anything below it tries to
install a package. If it isn't, the notebook stops immediately with:

> ⛔ This notebook is running on your SYSTEM Python, not an isolated environment...

**This is expected and intentional** — it replaces the old behavior where the setup
cell would quietly fall back to installing into whatever Python the kernel happened
to be (including, in the worst case, `--break-system-packages` against your system
install). On a personal laptop that's merely messy; on a corporate-managed machine
it can mean an IT ticket. The guard catches this *before* any install happens instead
of after.

**Fix:** do the venv setup at the top of this page, then pick that `.venv` interpreter
in the kernel picker — see "Wrong kernel selected" below. Using conda instead of venv?
`conda activate <your-env-name>` (not `base`) satisfies the same check.

**Already have everything installed globally, on purpose (facilitator demo box,
self-managed system Python)?** Set `BASECAMP_ALLOW_SYSTEM_PYTHON=1` in your shell
before launching VS Code/Jupyter to bypass the check for that session. This is an
intentional escape hatch for people who know what they're doing — don't hand this
out as a default fix to a participant who's actually hit the corporate-IT case above.

---

## Common problems

### `error: externally-managed-environment` (PEP 668)
**Why:** you're installing into a system Python (Homebrew on macOS, or the OS Python on
Debian/Ubuntu) that's marked off-limits for `pip`. **Fix:** usually nothing — the setup
cell detects a locked-down Python and installs into your user space automatically on the
**first** run, printing just `✓ Dependencies ready` (no PEP 668 wall of text). Prefer not
to touch the system Python at all? Use the venv above; it's the cleanest path. You'll only
get a message if **every** install strategy fails — an offline machine or a blocked PyPI
(see the proxy section below).

### Wrong kernel selected (the most common VS Code trap)
A notebook can run against a different Python than your terminal — so your `pip install`
lands somewhere the notebook can't see. **Fix:** in an open notebook, click the kernel
name (top-right) → **Select Another Kernel → Python Environments** → pick the one ending
in `.venv`. If you don't see it, run **Developer: Reload Window** and look again.

### No admin rights / `permission denied` on install
A venv is owned by you, so it needs no admin rights — use it. If you can't make one, the
notebook's automatic `--user` fallback installs into your home directory instead.

### Corporate proxy / PyPI blocked by the firewall
Point pip at your proxy, then install:
```bash
export HTTPS_PROXY=http://user:pass@proxy.company.com:8080
export HTTP_PROXY=$HTTPS_PROXY
pip install -r requirements.txt
```
If PyPI itself is blocked, ask IT for your internal package mirror and use it:
`pip install -r requirements.txt --index-url https://<your-mirror>/simple`.

### "I don't have Python" / wrong version
You need **Python 3.10+**. Install from [python.org](https://www.python.org/downloads/)
or your company's software portal, then re-open VS Code so it's detected. Check with
`python3 --version`.

### API key
The setup cell creates a gitignored **`.env` file** the first time you run it — never paste
your key into a notebook cell. Open the `.env`, paste your key after `ANTHROPIC_API_KEY=`,
save, and re-run the cell. The key never touches the notebook, and it survives kernel
restarts so you paste it once. A single `.env` at the repo root serves every exercise (the
cell walks up the folders to find it). You can also set `ANTHROPIC_API_KEY` in your shell —
it wins over the file — and if neither is set, the cell shows a hidden input box as a
fallback. A key starts with `sk-ant-`.

---

## Still stuck?
Run the first cell and read the message — the install and key-check cells print a specific
next step rather than a raw traceback. If it points you back here, the venv path at the top
resolves it in the large majority of cases.
