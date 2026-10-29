# Setup & Troubleshooting

**Prepared for Partner Basecamp participants.** Not for reproduction or redistribution as training material — you're free to apply these patterns in your own client work.

One page to get any laptop — including a locked-down corporate one — running the
Basecamp notebooks.

> [!IMPORTANT]
> **Setup is one command.** In a terminal at the repo root (the folder that contains `day1` and `day2`), run:
>
> ```bash
> python3 basecamp_setup.py        # macOS / Linux
> py basecamp_setup.py             # Windows (or: python basecamp_setup.py)
> ```
>
> Follow the prompts. Everything below explains what it does and how to fix the rare problem it can't.
>
> **Using an AI coding assistant?** Ask it to "set up this repo". [AGENTS.md](AGENTS.md) tells it to open this script in a terminal window, where you paste your key yourself.

---

## Running the setup

**First, open the repo root in VS Code:** **File → Open Folder** and choose the folder that directly contains `day1`, `day2` and `basecamp_setup.py`. If you downloaded a ZIP, check you're not one level too high: some unzip tools create a nested `Basecamp-Exercises-main/Basecamp-Exercises-main/`, and the inner folder is the one you want. Open the repo root itself, not a parent folder and not an exercise folder, so VS Code finds the exercises' Python environment.

Then open a terminal there (**Terminal → New Terminal**) and run the command above. It walks
you through everything:

1. **Installs [uv](https://docs.astral.sh/uv/)** if you don't have it (it asks first). uv
   manages the exercises' Python packages.
2. **Asks for your key** and saves it to `.env` at the repo root, which
   is gitignored, so it's never committed. It recognizes what you paste:
   - an **Anthropic API key** (`sk-ant-…`): nothing else to answer.
   - an **Amazon Bedrock API key**: it asks for your AWS region.
   - **anything else** is treated as a **company gateway key**: it asks for the gateway URL
     and the model ID prefix (press Enter to accept `bedrock.anthropic.`).
3. **Creates `.venv`** and installs everything the exercises need into it (`uv sync`). Your
   system Python is never modified.
4. **Registers the "Anthropic Basecamp (.venv)" kernel** for VS Code and Jupyter, and sets VS Code to
   use `.venv` for this folder.
5. **Tests certificates** for your Claude endpoint and, only if this machine needs it, saves
   the setting that works to `.env` (see [certificate errors](#corporate-proxy-blocked-pypi-or-certificate-errors)).
6. **Checks your connection** with a real call to Claude.

Then open any notebook. If VS Code hasn't picked the kernel already, click the kernel name
(top right) and choose **Anthropic Basecamp (.venv)**. Run the setup cell; a green **✓ verified**
banner means you're connected.

Run the script again any time, for example to switch keys. It keeps what's already done.

---

## Using an Amazon Bedrock key

The exercises run on either an Anthropic API key or an Amazon Bedrock key — the setup
cell detects which one you have and connects accordingly. You don't change any exercise
code; only the credentials differ.

`basecamp_setup.py` recognizes a Bedrock API key and asks for your region. To set it up by
hand instead, put **both** of these in your `.env` (or export them in your shell), and
comment out or delete the `ANTHROPIC_API_KEY` line:

```
# ANTHROPIC_API_KEY=paste-your-key-here
AWS_BEARER_TOKEN_BEDROCK=<your Bedrock API key>
AWS_REGION=us-east-1
```

`AWS_REGION` is required — Bedrock has no default. Use the region your Claude models are
enabled in. When it connects you'll see a green banner naming the provider and region:
**"✓ Bedrock key verified (us-east-1) — you're connected to Claude as
anthropic.claude-sonnet-5."**

Two things to know:

- **Model access is per account *and* per region.** A valid key can still fail with
  "model isn't available to you in `<region>`" — that means the model isn't enabled for
  your account there. Enable it in the Bedrock console under **Model access**, or switch
  `AWS_REGION` to a region where it is. The setup cell checks this up front so you find
  out at setup rather than four cells later.
- **Model IDs differ.** Bedrock prefixes them (`anthropic.claude-sonnet-5`); the
  Anthropic API uses the bare ID (`claude-sonnet-5`). The notebooks handle this for you
  via the `MODEL` / `FAST_MODEL` / `BIG_MODEL` variables the setup cell defines — use
  those rather than hardcoding an ID, and your code runs on both.

**If both credentials are set, the Anthropic API key wins.** To force the Bedrock path,
unset or comment out `ANTHROPIC_API_KEY`.

**One exercise differs on Bedrock:** Day 2's Inference Optimization demonstrates the
Batch API, which is an Anthropic API endpoint that Bedrock doesn't expose. The notebook
detects this, builds and shows the batch requests, and skips only the live submission —
the cost model that follows is the actual teaching point and is unaffected. (Bedrock has
its own batch-inference product with a different API.)

---

## Going through a company gateway or proxy

Some firms put a gateway in front of Claude, often a proxy in front of Bedrock. If yours
does, your gateway team gives you a key and an address, and sometimes a model-ID prefix.
`basecamp_setup.py` recognizes a non-standard key and asks for the other two. By hand, the
`.env` looks like this:

```
ANTHROPIC_API_KEY=<the key your gateway issued>
ANTHROPIC_BASE_URL=https://your-gateway.example.com
ANTHROPIC_MODEL_PREFIX=bedrock.anthropic.     # only if the gateway expects one
```

- **The key doesn't have to start with `sk-ant-`.** Gateway-issued keys come in other formats.
- **`ANTHROPIC_BASE_URL` sends every call through the gateway.** This works with either
  credential: an `ANTHROPIC_API_KEY` as above, or `AWS_BEARER_TOKEN_BEDROCK` for a gateway
  in front of Bedrock Mantle (then `AWS_REGION` is optional).
- **`ANTHROPIC_MODEL_PREFIX` replaces the default prefix.** With the line above, `MODEL`
  becomes `bedrock.anthropic.claude-sonnet-5`. Leave it out if the gateway takes bare IDs.
- **If it fails with "doesn't know model …"**, the prefix is wrong. Ask your gateway team
  for the exact model ID format. **If it can't connect at all**, check that you're on the
  VPN or network the gateway needs.

When it connects you'll see **"✓ Gateway key verified via https://… — you're connected
to Claude as bedrock.anthropic.claude-sonnet-5."** As on Bedrock, Inference Optimization
skips only the live Batch API submission when you're on a gateway.

---

## Common problems

### "📦 Packages missing" when you run a notebook
The notebook isn't using the Basecamp kernel, so it can't see the packages in `.venv`. In
the open notebook, click the kernel name (top right) → **Select Another Kernel** → pick
**Anthropic Basecamp (.venv)** (under Jupyter Kernels, or the `.venv` entry under Python
Environments). Not in the list? Check VS Code has the repo root open (the folder that directly contains `day1`, `day2` and `basecamp_setup.py`),
run the setup script, then **Developer: Reload Window** and look again.

### uv won't install
A company network can block the official installer. Install uv another way, then run the
setup script again:
- macOS: `brew install uv`
- Windows: `winget install --id=astral-sh.uv -e`
- Anything else: [docs.astral.sh/uv/getting-started/installation](https://docs.astral.sh/uv/getting-started/installation/)

### "Couldn't reach …" or a timeout
The endpoint didn't answer within a few seconds, so the network is in the way, not your key.
For a company gateway, check you're on the company VPN; if you are, switch to your phone's
hotspot, keep the VPN on, and try again. For the Anthropic API or Bedrock, the network
you're on may be blocking it: switch to your phone's hotspot. During setup, the script waits
for you to switch and press Enter, then tries again.

### Corporate proxy, blocked PyPI, or certificate errors
- **Behind a proxy:** set it before running the script.
  ```bash
  export HTTPS_PROXY=http://user:pass@proxy.company.com:8080      # macOS / Linux
  python3 basecamp_setup.py
  ```
  ```powershell
  $env:HTTPS_PROXY="http://user:pass@proxy.company.com:8080"     # Windows PowerShell
  py basecamp_setup.py
  ```
- **Certificate errors:** networks that inspect HTTPS traffic re-sign it with a company
  certificate, which your operating system's certificate store trusts. Sometimes
  `SSL_CERT_FILE` is set on the machine and points to a certificate bundle that's missing
  certificates, and Python tools trust that file instead. The script handles both, for the
  exercises only (your shell and system settings are never changed):
  - **Installing packages:** if a download fails on a certificate, it retries with your
    system's certificate store, setting `SSL_CERT_FILE` aside for that install.
  - **Notebooks:** it tests which certificates reach your Claude endpoint and, if the
    default doesn't, saves the one that works to `.env` as `BASECAMP_TLS`. The setup cell
    uses it, and its green banner says so.

  If a notebook later reports a certificate error (after changing networks, or after IT
  updates your certificates), re-test without redoing the whole setup:
  ```bash
  python3 basecamp_setup.py --check-tls     # macOS / Linux
  py basecamp_setup.py --check-tls          # Windows
  ```
- **PyPI blocked entirely:** ask IT for the internal package mirror and point uv at it:
  `UV_DEFAULT_INDEX=https://<your-mirror>/simple python3 basecamp_setup.py` (macOS / Linux) or
  `$env:UV_DEFAULT_INDEX="https://<your-mirror>/simple"; py basecamp_setup.py` (Windows PowerShell)

### No admin rights
You don't need them. uv installs into your home folder and `.venv` lives in the repo, both
owned by you.

### "I don't have Python" / wrong version
You need any Python 3.8 or newer to run the script; check with `python3 --version` (Windows:
`py --version`). The
exercises themselves need 3.10+, and if your Python is older, uv downloads a suitable one
for `.venv` automatically (unless your network blocks that too). No Python at all? Install
it from [python.org](https://www.python.org/downloads/) or your company's software portal,
then re-open the terminal.

### API key
Your key lives in `.env` at the repo root, never in a notebook cell (notebooks have a way of
ending up in client repos). `basecamp_setup.py` writes it for you; to edit it by hand, copy
`.env.example` to `.env` and fill in one option. After any edit, just run the notebook's
setup cell again: it re-reads `.env` every time, no kernel restart needed. A value exported
in your shell wins over `.env`. An Anthropic API key starts with `sk-ant-`; a gateway-issued
key may not.

---

## Still stuck?
Read the banner the setup cell shows: every failure names a specific next step rather than
a raw traceback. Re-running the setup script resolves most problems, because it
re-checks every step and tells you which one fails.

---

## If you want to run the steps manually

The script is the recommended path. If you'd rather do it yourself, these are the same
steps, with uv in place of the old `python -m venv` + `pip install`. Run them from the repo
root.

1. **Install uv** (see [uv won't install](#uv-wont-install) if this is blocked):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh                        # macOS / Linux
   ```
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows
   ```
   Then open a new terminal so `uv` is on your PATH.
2. **Create `.venv` and install the packages:** this replaces `python -m venv .venv` and
   `pip install -r requirements.txt`. uv reads `pyproject.toml` and downloads Python 3.10+
   for `.venv` if yours is older.
   ```bash
   uv sync
   ```
3. **Register the kernel** so VS Code and Jupyter list it:
   ```bash
   uv run python -m ipykernel install --user --name basecamp-exercises --display-name "Anthropic Basecamp (.venv)"
   ```
4. **Add your key:** copy the template and fill in one option (Anthropic API key, Bedrock
   key, or gateway key, as described in the file):
   ```bash
   cp .env.example .env          # macOS / Linux
   copy .env.example .env        # Windows
   ```
5. **Check your connection:**
   ```bash
   uv run python -c "import basecamp_setup; basecamp_setup.connect()"
   ```
   A line starting with ✓ means you're connected. On a certificate error, run
   `uv run python basecamp_setup.py --check-tls`, then check again.

There's no need to activate `.venv`: `uv run` uses it automatically. If you want it active
in your shell anyway, run `source .venv/bin/activate` (macOS / Linux) or
`.venv\Scripts\activate` (Windows). In VS Code, open a notebook and pick
**Anthropic Basecamp (.venv)** as the kernel.
