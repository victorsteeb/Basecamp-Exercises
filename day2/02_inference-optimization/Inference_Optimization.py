# %% [markdown]
# # Inference Optimization Lab — **The Margin Call**
#
# Your firm signed **Project HELVETICA**: an AI-assisted contract-diligence engagement for
# **Aldgate Capital Partners**, who are acquiring Volta Industrial Group — a roll-up of 14
# companies with a supplier-contract estate of **248,000 documents**. The deal team needs every
# contract triaged for change-of-control consent, liability caps, auto-renewal, and governing law.
#
# The demo team built an agent — **ClauseScan v0** — the night before the pitch. It works.
# It is also slow enough that analysts alt-tab away while it thinks, and its unit economics
# quietly eat the engagement margin. The pitch landed, the SOW is signed, and as of this
# morning **you own it**.
#
# What the client signed:
#
# | SLA term | Commitment |
# |---|---|
# | Accuracy | ≥ 90% on audited fields |
# | Interactive latency | p50 ≤ 5s per contract in analyst working sessions |
# | Unit economics | COGS ≤ $0.02 per contract at production scale |
# | Fee | $0.75 per reviewed contract (fixed) |
#
# **The lab in three acts:**
# 1. **Parts 1–2 — Instrument & baseline.** Build the measurement toolkit, run the initial tests
#    across Haiku / Sonnet / Opus.
# 2. **Parts 3–4 — Diagnose & learn the levers.** Run ClauseScan v0, see the damage, then work
#    through six optimization levers one at a time, measuring each.
# 3. **Parts 5–6 — The optimization sprint.** Rebuild the pipeline, climb the leaderboard, and
#    auto-generate the before/after slide you'd take to the steering committee.
#
# **Key metrics:**
# - **TTFT** — Time To First Token: how long the analyst stares at a spinner.
# - **TTC** — Time To Completion: total request duration.
# - **OTPS** — Output Tokens Per Second: generation throughput after streaming starts.
# - **$/contract** — fully loaded cost per document, including cache reads and writes.
#
# > 💸 Running every cell in this notebook costs roughly **$2–4** of API usage, most of it in the
# > deliberately wasteful v0 baseline. That's part of the lesson.

# %% [markdown]
# # Part 0 · Setup
#
# Dependencies first, then your API key. Never paste a key into a cell — you will paste
# notebooks into client repos one day; build the habit now.

# %%
# Install dependencies into THIS kernel — safe to re-run; survives locked-down (PEP 668) Pythons.
import importlib.util, subprocess, sys

def _ensure_packages(requirements):
    """requirements: list of (import_name, pip_spec). Install only what is missing,
    into the running interpreter. Tries a normal install, then user-space, then a
    PEP 668 override (user-space first, system-wide only as a last resort). Every
    attempt is silent — pip's output is captured, not streamed — so a locked-down
    Python (Homebrew or Debian, PEP 668) no longer dumps a scary
    'externally-managed-environment' wall of text when a fallback is what actually
    succeeds. Only if every strategy fails does it surface the reason, with the
    venv fix instead of a raw traceback."""
    missing = [pip for mod, pip in requirements if importlib.util.find_spec(mod) is None]
    if not missing:
        return
    print("Installing " + ", ".join(missing) + " — first run only, please wait…", flush=True)
    base = [sys.executable, "-m", "pip", "install", "-q"]
    last = None
    for extra in ([], ["--user"], ["--user", "--break-system-packages"], ["--break-system-packages"]):
        last = subprocess.run(base + extra + missing, capture_output=True, text=True)
        if last.returncode == 0:
            return
    pip_said = (last.stderr or last.stdout or "").strip().splitlines() if last else []
    tail = "\n      ".join(pip_said[-3:]) if pip_said else "(no output from pip)"
    raise SystemExit(
        "\n  Couldn't install: " + ", ".join(missing) + "\n"
        "  This Python is locked down (PEP 668) or offline. Quickest fix is a venv:\n"
        f"      {sys.executable} -m venv .venv\n"
        "      source .venv/bin/activate          # Windows: see SETUP.md\n"
        f"      pip install {' '.join(missing)}\n"
        "  Then pick the .venv interpreter in VS Code (kernel picker, top-right) and Run All.\n"
        "  Corporate proxy or PyPI blocked? See SETUP.md in the repo root.\n"
        f"  (pip said: {tail})\n"
    )

_ensure_packages([("anthropic", "anthropic"), ("tabulate", "tabulate")])
print("✓ Dependencies ready")

import os
import json
import time
import statistics
from dataclasses import dataclass, field
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor
from tabulate import tabulate

import anthropic

# %% [markdown]
# ### Setup — connect to Claude
#
# Run the next cell first. The setup cell creates a **`.env` file** the first time you run it (gitignored — your key
# is never committed). Open it, paste your key after `ANTHROPIC_API_KEY=`, save, and re-run —
# it survives kernel restarts, so you paste once. *(No `.env` yet? A hidden input box appears
# as a fallback.)* You're locked in when you see the green **"✓ API key verified"** banner. Red banner? Do what it
# says and run the cell again.

# %%
import os

def _status(ok, msg):
    """Green/red banner in notebooks; plain text when run as a script."""
    try:
        from IPython import get_ipython
        shell = get_ipython()
        if shell is None or shell.__class__.__name__ != "ZMQInteractiveShell":
            raise RuntimeError("not in a notebook kernel - use the plain-text banner")
        from IPython.display import display, HTML
        color = "#1a7f37" if ok else "#b42318"
        bg = "#e6f4ea" if ok else "#fdecea"
        icon = "✓" if ok else "✗"
        display(HTML(
            f'<div style="padding:12px 16px;border-radius:8px;background:{bg};'
            f'border:1.5px solid {color};color:{color};font-weight:600;'
            f'font-size:15px;font-family:sans-serif;">{icon} {msg}</div>'
        ))
    except Exception:
        print(("[OK] " if ok else "[!!] ") + msg)

import os, pathlib

# ── API key via .env (gitignored — never committed) ──
# Your key lives in a .env file. We look for one next to this notebook or in any parent
# folder, so a single .env at the repo root can serve every exercise (paste once). If none
# exists yet, we create one from this template — fill it in, save, and re-run the cell.
_ENV_TEMPLATE = (
    "# Paste your Anthropic API key after the = (no quotes, no spaces), then save\n"
    "# and re-run the setup cell. Get a key at https://console.anthropic.com/\n"
    "# This file is gitignored — your key is never committed.\n"
    "ANTHROPIC_API_KEY=paste-your-key-here\n"
)

def _resolve_env_file():
    """Nearest existing .env walking up from the working dir (so one root .env serves every
    exercise); if none exists yet, point at the repo root — or this folder if the notebook
    was opened on its own."""
    here = pathlib.Path.cwd().resolve()
    for d in [here, *here.parents]:
        if (d / ".env").is_file():
            return d / ".env"
    root = next((d for d in [here, *here.parents]
                 if (d / "SETUP.md").exists() or (d / ".git").exists()), here)
    return root / ".env"

_env_file = _resolve_env_file()
if not _env_file.exists():
    _env_file.write_text(_ENV_TEMPLATE)
    print(f"Created {_env_file.name} in {_env_file.parent} — open it, paste your key after "
          "ANTHROPIC_API_KEY=, save, then re-run this cell.")

# Tiny .env parser (no python-dotenv dependency). Re-read on every run, so pasting your
# key and re-running picks it up. A real key in the environment (shell / Claude Code / CI)
# wins; the placeholder never sticks.
_file = {}
for _line in (_env_file.read_text().splitlines() if _env_file.exists() else []):
    _line = _line.strip()
    if _line and not _line.startswith("#") and "=" in _line:
        _k, _v = _line.split("=", 1)
        _file[_k.strip()] = _v.strip().strip('"').strip("'")
for _k, _v in _file.items():
    if _k != "ANTHROPIC_API_KEY":
        os.environ.setdefault(_k, _v)
_shell = os.environ.get("ANTHROPIC_API_KEY", "").strip()
api_key = _shell if _shell.startswith("sk-ant-") else _file.get("ANTHROPIC_API_KEY", "").strip()
if not api_key.startswith("sk-ant-"):
    print(
        "\n📋 Add your key to continue:\n"
        f"   1. Open this file:  {_env_file}\n"
        "   2. Replace  paste-your-key-here  with your key (it starts with sk-ant-)\n"
        "   3. Save the file, then click ▶ on this cell again.\n"
    )
else:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key, timeout=30.0, max_retries=1)
    try:
        client.messages.create(model="claude-haiku-4-5", max_tokens=1,
                               messages=[{"role": "user", "content": "ping"}])
    except anthropic.AuthenticationError:
        _status(False, "That key was rejected. Run this cell again and paste the whole key (it starts with sk-ant-).")
        raise SystemExit("API key not accepted - re-run this cell and try again.")
    except Exception as exc:
        _status(False, "Could not reach the Claude API (" + type(exc).__name__ + "). Check your connection, then run this cell again.")
        raise
    else:
        os.environ["ANTHROPIC_API_KEY"] = api_key  # later cells (and any !python commands) pick it up from here
        _status(True, "API key verified - you're connected to Claude.")

# %%
# The lab client: SDK defaults (long timeout, standard retries). The verification client
# above uses a short 30s timeout — fine for a 1-token ping, fatal for v0's deliberately
# slow, non-streamed essay calls. Re-create it; the key is in the environment now.
client = anthropic.Anthropic()

# The model portfolio. Aliases, not date-pinned IDs — aliases track the current snapshot
# and don't 404 when a snapshot is retired.
MODEL_HAIKU = "claude-haiku-4-5"
MODEL_SONNET = "claude-sonnet-5"
MODEL_OPUS = "claude-opus-4-8"

print(f"SDK {anthropic.__version__} · portfolio: {MODEL_HAIKU}, {MODEL_SONNET}, {MODEL_OPUS}")

# %% [markdown]
# # Part 1 · The instrument panel
#
# You cannot optimize what you cannot measure, and you cannot bill a client for an improvement
# you cannot prove. Everything in this lab flows through one streaming helper and one
# cache-aware cost function.

# %%
@dataclass
class BenchmarkResult:
    """Timing, tokens, and cost for a single API call."""
    ttft: float                    # Time to First Token (seconds)
    total_time: float              # Time to Completion (seconds)
    input_tokens: int
    output_tokens: int
    model: str
    test_name: str
    otps: Optional[float] = None   # Output Tokens Per Second
    cost: Optional[float] = None   # Dollars, cache-aware
    cache_read: int = 0
    cache_write: int = 0


@dataclass
class BenchmarkSuite:
    """Collects results across runs and prints a comparison table."""
    results: List[BenchmarkResult] = field(default_factory=list)

    def add(self, result: BenchmarkResult):
        self.results.append(result)

    def clear(self):
        self.results = []

    def summary(self) -> str:
        if not self.results:
            return "No results."
        groups: dict = {}
        for r in self.results:
            groups.setdefault(r.test_name, []).append(r)
        rows = []
        for name, group in groups.items():
            rows.append([
                name,
                len(group),
                f"{statistics.mean(r.ttft for r in group) * 1000:.0f}",
                f"{statistics.mean(r.total_time for r in group) * 1000:.0f}",
                f"{statistics.mean(r.otps or 0 for r in group):.1f}",
                f"${sum(r.cost or 0 for r in group) * 1000:.2f}",
            ])
        headers = ["Test", "Runs", "TTFT(ms)", "TTC(ms)", "OTPS", "$/1K calls"]
        return tabulate(rows, headers=headers, tablefmt="grid")


suite = BenchmarkSuite()
print("BenchmarkSuite ready")

# %% [markdown]
# **The streaming helper.** Streaming is the default posture for anything user-facing: the
# analyst sees tokens immediately (TTFT) instead of waiting for the whole response (TTC), and
# long responses can't hit HTTP timeouts. We watch the event stream for the first
# `content_block_start` to stamp TTFT, then collect the final message.

# %%
def _stream_request(messages, model, max_tokens=1024, system=None, **kwargs):
    """Stream a request; return (ttft_seconds, total_seconds, final_message)."""
    ttft = None
    params = dict(model=model, max_tokens=max_tokens, messages=messages, **kwargs)
    if system is not None:
        params["system"] = system
    start = time.perf_counter()
    with client.messages.stream(**params) as stream:
        for event in stream:
            if ttft is None and event.type == "content_block_start":
                ttft = time.perf_counter() - start
        response = stream.get_final_message()
    total = time.perf_counter() - start
    return ttft if ttft is not None else total, total, response


def compute_otps(ttft, total_time, output_tokens):
    """Output Tokens Per Second, measured over generation time (TTC minus TTFT).
    Time before the first token is waiting, not generating."""
    gen_time = max(total_time - ttft, 1e-9)
    return output_tokens / gen_time, gen_time


def text_of(response) -> str:
    return "".join(b.text for b in response.content if b.type == "text")


ttft, total, resp = _stream_request(
    [{"role": "user", "content": "What is 2 + 2? Answer in one word."}], model=MODEL_SONNET)
otps, gen = compute_otps(ttft, total, resp.usage.output_tokens)
print(f"Response: {text_of(resp).strip()}")
print(f"TTFT {ttft*1000:.0f}ms · TTC {total*1000:.0f}ms · OTPS {otps:.1f} tok/s")

# %% [markdown]
# **Cache-aware cost.** Most cost functions you'll see in the wild price `input × rate +
# output × rate` and stop. That misprices any cached workload badly: cache **writes** bill at
# **1.25×** the input rate (5-minute TTL) and cache **reads** at **0.1×**. When you stand in
# front of a client CFO, your unit economics need all four terms.
#
# | Model | Input $/MTok | Output $/MTok |
# |---|---|---|
# | Haiku 4.5 | $1.00 | $5.00 |
# | Sonnet 5 | $3.00 | $15.00 |
# | Opus 4.8 | $5.00 | $25.00 |
#
# *(Verify against the pricing page before quoting in a deliverable — table cached June 2026.
# Batch API runs at 50% of everything; that lever arrives in Part 4.)*

# %%
PRICING = {
    MODEL_HAIKU:  {"input": 1.00, "output": 5.00},
    MODEL_SONNET: {"input": 3.00, "output": 15.00},
    MODEL_OPUS:   {"input": 5.00, "output": 25.00},
}
CACHE_WRITE_MULT = 1.25   # 5-minute TTL cache writes
CACHE_READ_MULT = 0.10
BATCH_DISCOUNT = 0.50     # Batch API: 50% off all token charges


def calculate_cost(model: str, usage) -> float:
    """Fully loaded cost in dollars for one API call, including cache economics."""
    p = PRICING[model]
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    return (
        usage.input_tokens * p["input"]
        + cache_write * p["input"] * CACHE_WRITE_MULT
        + cache_read * p["input"] * CACHE_READ_MULT
        + usage.output_tokens * p["output"]
    ) / 1e6


def measure(prompt: str, model: str, test_name: str, max_tokens: int = 256) -> BenchmarkResult:
    """One measured streaming call → a BenchmarkResult."""
    ttft, total, resp = _stream_request(
        [{"role": "user", "content": prompt}], model=model, max_tokens=max_tokens)
    otps, _ = compute_otps(ttft, total, resp.usage.output_tokens)
    return BenchmarkResult(
        ttft=ttft, total_time=total,
        input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens,
        model=model, test_name=test_name, otps=otps,
        cost=calculate_cost(model, resp.usage),
        cache_read=getattr(resp.usage, "cache_read_input_tokens", 0) or 0,
        cache_write=getattr(resp.usage, "cache_creation_input_tokens", 0) or 0,
    )


print(f"Cost of the 2+2 call above: ${calculate_cost(MODEL_SONNET, resp.usage):.6f}")

# %% [markdown]
# # Part 2 · Initial tests — the model portfolio
#
# Same prompt, three models, four runs each. This is the single biggest lever you have, so it
# goes first: before optimizing *how* you call a model, decide *which* model each piece of work
# deserves.

# %%
PROBE = "What is machine learning? Answer in 2 sentences."

suite.clear()
for model_id, label in [(MODEL_HAIKU, "haiku"), (MODEL_SONNET, "sonnet"), (MODEL_OPUS, "opus")]:
    print(f"Benchmarking {label}...")
    for i in range(4):
        r = measure(PROBE, model=model_id, test_name=label)
        suite.add(r)
        print(f"  run {i+1}: TTFT {r.ttft*1000:.0f}ms · TTC {r.total_time*1000:.0f}ms"
              f" · OTPS {r.otps:.1f} · ${r.cost:.6f}")

print()
print(suite.summary())

# %% [markdown]
# **Read the table like a partner, not a benchmark blog.** Haiku is typically several times
# cheaper and noticeably faster to first token; Opus buys depth you only need on hard cases.
# The right architecture is almost never "pick one" — it's a **portfolio**: cheap models for
# high-volume routine work, expensive models for the judgment calls, and a router deciding
# which is which. Hold that thought; it becomes Lever 2.

# %% [markdown]
# # Part 3 · The engagement — meet ClauseScan v0
#
# Below is the lab-scale version of the HELVETICA workload: a six-contract sample of the Volta
# supplier estate (production contracts are ~8× longer — we extrapolate honestly in Part 6),
# the firm's **diligence playbook** (the standards document every reviewer follows — long, and
# identical on every single call), **gold labels** an associate prepared by hand, and a grader.
#
# Then we run the agent you inherited, exactly as the demo team wrote it. Run it before
# reading ahead — the smell test is part of the job.

# %%
# ── The contract sample (lab-scale stand-ins for the 248K-document estate) ──────────────
CONTRACTS = [
    {
        "id": "C-101", "vendor": "NorthWind Logistics GmbH",
        "text": """MASTER SERVICES AGREEMENT — NorthWind Logistics GmbH ("Supplier") and Volta Industrial Group ("Customer").

1. SERVICES. Supplier provides freight forwarding and warehouse management services per attached SOWs.
2. TERM AND RENEWAL. Initial term of twenty-four (24) months. This Agreement automatically renews for successive twelve (12) month periods unless either party gives written notice of non-renewal at least sixty (60) days before the end of the then-current term.
3. FEES AND PAYMENT. Fees per Schedule A. Invoices payable net forty-five (45) days. Late amounts accrue interest at 1% per month.
4. LIMITATION OF LIABILITY. EXCEPT FOR BREACHES OF CONFIDENTIALITY, EACH PARTY'S AGGREGATE LIABILITY ARISING OUT OF THIS AGREEMENT SHALL NOT EXCEED TWO HUNDRED FIFTY THOUSAND U.S. DOLLARS ($250,000).
5. ASSIGNMENT. Either party may assign this Agreement to an affiliate or in connection with a merger or sale of substantially all assets without the consent of the other party, upon written notice.
6. CONFIDENTIALITY. Standard mutual obligations for 3 years post-termination.
7. GOVERNING LAW. This Agreement is governed by the laws of the State of Delaware, without regard to conflicts of law principles.""",
    },
    {
        "id": "C-102", "vendor": "Apex Facilities Co.",
        "text": """FACILITIES MAINTENANCE AGREEMENT — Apex Facilities Co. ("Contractor") and Volta Industrial Group ("Client").

1. SCOPE. HVAC, electrical, and janitorial maintenance for the sites listed in Exhibit 1.
2. TERM. Fixed term of thirty-six (36) months from the Effective Date. This Agreement expires at the end of the term and does not renew automatically; any extension requires a written amendment signed by both parties.
3. PRICING. Monthly fixed fee of $18,400 plus materials at cost +10%.
4. LIMITATION OF LIABILITY. Contractor's total cumulative liability under this Agreement shall not exceed ONE HUNDRED THOUSAND U.S. DOLLARS ($100,000). Neither party is liable for indirect or consequential damages.
5. ASSIGNMENT. Either party may freely assign this Agreement, including in connection with any change of control, without consent.
6. INSURANCE. Contractor maintains commercial general liability coverage of $2,000,000 per occurrence.
7. GOVERNING LAW. The laws of the State of New York govern this Agreement.""",
    },
    {
        "id": "C-103", "vendor": "Cobalt Data Services Ltd.",
        "text": """DATA PROCESSING AND HOSTING AGREEMENT — Cobalt Data Services Ltd. ("Provider") and Volta Industrial Group ("Company").

1. SERVICES. Provider hosts Company's plant telemetry platform and processes operational data.
2. TERM AND RENEWAL. Initial term of twelve (12) months, automatically renewing for successive one-year terms unless either party provides ninety (90) days' written notice of termination.
3. SERVICE LEVELS. 99.9% monthly uptime; service credits per Schedule 2.
4. LIMITATION OF LIABILITY. PROVIDER'S AGGREGATE LIABILITY SHALL NOT EXCEED FIVE HUNDRED THOUSAND U.S. DOLLARS ($500,000) OR THE FEES PAID IN THE PRIOR 12 MONTHS, WHICHEVER IS GREATER, PROVIDED THE CAP SHALL IN NO EVENT EXCEED $500,000.
5. ASSIGNMENT AND CHANGE OF CONTROL. Neither party may assign this Agreement, whether by operation of law, change of control, merger, or otherwise, without the prior written consent of the other party, such consent not to be unreasonably withheld.
6. DATA PROTECTION. Provider processes personal data per the DPA in Exhibit C.
7. GOVERNING LAW. This Agreement is governed by the laws of the State of California.""",
    },
    {
        "id": "C-104", "vendor": "Ironclad Security Services plc",
        "text": """SECURITY SERVICES AGREEMENT — Ironclad Security Services plc ("Ironclad") and Volta Industrial Group ("Principal").

1. SERVICES. Manned guarding, alarm response, and access control for Principal's UK sites.
2. TERM. Twelve (12) months from the Commencement Date, terminating automatically at expiry. Renewal only by mutual written agreement.
3. INDEMNITY. Ironclad indemnifies Principal against third-party claims arising from Ironclad's negligence; Principal indemnifies Ironclad against claims arising from site conditions not disclosed in the Site Survey. Each indemnity is uncapped and survives termination for six (6) years.
4. LIABILITY. The parties acknowledge the indemnities in Section 3. This Agreement does not otherwise state any cap, ceiling, or other limitation on either party's liability.
5. ASSIGNMENT AND CHANGE OF CONTROL. Ironclad may terminate this Agreement on thirty (30) days' notice upon any change of control of Principal. Any assignment by either party requires the prior written consent of the other.
6. TUPE. The parties acknowledge the potential application of TUPE regulations to guard personnel on expiry.
7. GOVERNING LAW. This Agreement and any dispute arising out of it are governed by the laws of England and Wales.""",
    },
    {
        "id": "C-105", "vendor": "Helios Components S.A.",
        "text": """SUPPLY AGREEMENT — Helios Components S.A. ("Helios") and Volta Industrial Group ("Buyer").

1. SUPPLY. Helios supplies the precision components listed in Annex 1 per Buyer's purchase orders.
2. TERM AND RENEWAL. Initial term of twenty-four (24) months, automatically extending for successive twelve-month periods unless either party gives one hundred twenty (120) days' notice.
3. PRICING. Annex 2 price list, adjusted annually per the PPI index, capped at 4% per year.
4. LIMITATION OF LIABILITY. Subject to Section 9 (IP Indemnity), each party's aggregate liability under this Agreement shall not exceed ONE MILLION U.S. DOLLARS ($1,000,000).
5. ASSIGNMENT AND CHANGE OF CONTROL. Any direct or indirect change of control of Buyer requires Helios's prior written consent. Helios may withhold consent in its sole discretion.
6. QUALITY. Components conform to the specifications in Annex 3; non-conforming lots replaced at Helios's cost.
7. GOVERNING LAW. This Agreement is governed by the laws of the State of Texas.

AMENDMENT NO. 2 (executed and effective). The parties agree as follows: Section 4 (Limitation of Liability) of the Agreement is deleted in its entirety and shall be of no further force or effect. For the avoidance of doubt, following this Amendment the Agreement states no cap on either party's liability. All other terms remain unchanged.""",
    },
    {
        "id": "C-106", "vendor": "Brightline Staffing LLC",
        "text": """STAFFING SERVICES AGREEMENT — Brightline Staffing LLC ("Brightline") and Volta Industrial Group ("Client").

1. SERVICES. Brightline supplies temporary production and warehouse personnel on request.
2. TERM AND RENEWAL. One (1) year initial term, renewing automatically for successive one-year terms unless either party gives thirty (30) days' written notice prior to renewal.
3. RATES. Bill rates per Rate Card v7; overtime at 1.5×; conversion fee of 20% of first-year salary for direct hires within 12 months.
4. WORKER CLASSIFICATION. Brightline is the employer of record and is responsible for wages, withholding, and workers' compensation coverage.
5. ASSIGNMENT. Either party may assign this Agreement without the other party's consent, including in connection with a change of control, provided the assignee assumes all obligations.
6. WARRANTIES. Services performed in a professional and workmanlike manner. THE PARTIES HAVE NOT AGREED ANY LIMITATION OR CAP ON LIABILITY UNDER THIS AGREEMENT.
7. GOVERNING LAW. This Agreement is governed by the laws of the State of Illinois.""",
    },
]

# Gold labels — prepared by hand, the way an associate would on a real engagement.
# risk_tier rule (also stated in the playbook): HIGH = change-of-control consent required AND
# no liability cap; MEDIUM = exactly one of those red flags; LOW = neither.
GOLD = {
    "C-101": {"auto_renewal": True,  "change_of_control": False, "liability_cap_usd": 250000,
              "governing_law": "Delaware",          "risk_tier": "LOW"},
    "C-102": {"auto_renewal": False, "change_of_control": False, "liability_cap_usd": 100000,
              "governing_law": "New York",          "risk_tier": "LOW"},
    "C-103": {"auto_renewal": True,  "change_of_control": True,  "liability_cap_usd": 500000,
              "governing_law": "California",        "risk_tier": "MEDIUM"},
    "C-104": {"auto_renewal": False, "change_of_control": True,  "liability_cap_usd": None,
              "governing_law": "England and Wales", "risk_tier": "HIGH"},
    "C-105": {"auto_renewal": True,  "change_of_control": True,  "liability_cap_usd": None,
              "governing_law": "Texas",             "risk_tier": "HIGH"},
    "C-106": {"auto_renewal": True,  "change_of_control": False, "liability_cap_usd": None,
              "governing_law": "Illinois",          "risk_tier": "MEDIUM"},
}

print(f"Loaded {len(CONTRACTS)} contracts with gold labels")

# %% [markdown]
# **The diligence playbook.** Every reviewer — human or model — works from the same standards
# document: field definitions, the risk rubric, a clause library, negotiation precedent. It's
# long, it's authoritative, and it is **byte-identical on every call**. Remember that phrase.

# %%
PLAYBOOK_CORE = """You are ClauseScan, the contract-diligence reviewer for Project HELVETICA \
(Aldgate Capital Partners' acquisition of Volta Industrial Group). You review supplier \
contracts and report five audited fields. Work only from the contract text provided. Never \
guess: if the contract is silent on a point, report it as absent rather than inventing terms.

## Audited fields
1. auto_renewal (boolean) — true only if the contract renews automatically absent notice. A \
fixed term that expires, or renewal "by mutual written agreement", is NOT auto-renewal.
2. change_of_control (boolean) — true if assignment or change of control of either party \
requires the counterparty's prior consent, or gives the counterparty a termination right. \
Free assignment or notice-only assignment is false.
3. liability_cap_usd (number or null) — the aggregate liability cap in USD. null if no cap is \
stated, if liability is expressly uncapped, or if an amendment removed the cap. Amendments \
override the original clause — always check for amendments before reporting.
4. governing_law (string) — the governing jurisdiction, e.g. "Delaware" or "England and Wales".
5. risk_tier (LOW | MEDIUM | HIGH) — apply this rule exactly:
   HIGH = change-of-control consent/termination right present AND no liability cap.
   MEDIUM = exactly one of those two red flags present.
   LOW = neither red flag (no change-of-control restriction AND a cap is stated).

## Review discipline
- Read every section, then re-check the two red-flag clauses before concluding.
- Quote-check: the evidence you cite must appear in the contract.
- Deal context: Aldgate's purchase will itself trigger change-of-control clauses across the \
estate — that is why the field is audited.
"""

# The clause library and precedent notes make the playbook realistically long. On a real
# engagement this is the 40-page standards PDF your firm maintains.
CLAUSE_LIBRARY = [
    ("Automatic renewal (evergreen)", "Term continues for successive periods unless a party gives notice by a stated deadline. Capture the notice window and the renewal period length.", "Notice windows under 30 days are operationally dangerous during an integration."),
    ("Fixed term with mutual-agreement renewal", "Agreement expires at the end of the stated term; any continuation needs a signed amendment.", "Often misread as auto-renewal. It is not."),
    ("Assignment with consent", "Neither party may assign without prior written consent; usually includes 'by operation of law' and merger language.", "This is a change-of-control restriction even when the words 'change of control' never appear."),
    ("Free assignment", "Either party may assign to affiliates or acquirers, sometimes with notice only.", "Notice-only assignment is NOT a change-of-control restriction."),
    ("Change-of-control termination right", "Counterparty may terminate upon a change of control of the other party.", "A termination right is as dangerous to deal value as a consent right — treat it as change_of_control = true."),
    ("Aggregate liability cap", "A single dollar ceiling on total liability under the agreement.", "Check whether carve-outs (confidentiality, IP, indemnity) sit outside the cap."),
    ("Capped at fees paid", "Liability limited to fees paid over a trailing window, sometimes with a dollar ceiling on top.", "Report the effective ceiling where one is stated; otherwise treat as a cap of unstated amount."),
    ("Uncapped liability", "No limitation-of-liability clause, or an express statement that liability is unlimited.", "Silence is a red flag, not a default. Report null."),
    ("Amendment overriding liability terms", "Later amendments may delete or rewrite the limitation-of-liability section.", "The amendment controls. Re-read amendments before reporting any cap."),
    ("Mutual indemnity, uncapped", "Each party indemnifies the other for defined claim classes with no ceiling.", "Uncapped indemnities alongside a deleted cap compound exposure."),
    ("Governing law", "The jurisdiction whose law governs the contract.", "Distinguish governing law from venue/forum; report the law."),
    ("Service levels and credits", "Uptime or performance commitments with credit remedies.", "Credits are usually the exclusive remedy — note but do not audit."),
    ("Payment terms", "Net-day windows, late interest, price-adjustment indices.", "Index-linked price escalators matter for the operating model, not this audit."),
    ("Confidentiality", "Mutual non-disclosure obligations with survival periods.", "Often carved out of the liability cap."),
    ("Insurance requirements", "Required coverage types and limits.", "Insurance limits are not liability caps. Do not conflate."),
    ("TUPE / employee transfer", "EU/UK staff-transfer regulations on outsourcing changes.", "Integration planning input; not an audited field."),
    ("Exclusivity", "Sole-supplier or minimum-purchase commitments.", "Flag in evidence notes if material; not an audited field."),
    ("Termination for convenience", "Either party may exit on notice without cause.", "Shortens effective exposure; note the notice window."),
    ("Most-favored-customer pricing", "Supplier promises pricing no worse than comparable customers.", "Diligence interest for procurement, not this audit."),
    ("IP indemnity", "Supplier defends infringement claims; sometimes uncapped.", "Carve-outs can sit outside the cap — read the cap clause's 'subject to' language."),
    ("Force majeure", "Excused performance on defined events.", "Not audited."),
    ("Audit rights", "Customer may audit supplier records or facilities.", "Not audited here; useful for integration."),
]

PRECEDENT_NOTES = [
    "Volta's 2024 acquisition of Kessler Tooling stalled five weeks on unflagged change-of-control consents across 1,100 supplier contracts.",
    "Aldgate's deal team treats any uncapped-liability supplier with consent rights as a Day-1 escalation.",
    "Notice windows: the integration office needs 90+ days of runway; sub-30-day windows go on the watch list.",
    "Caps stated in non-USD currencies are converted at the deal-model rate; report the stated figure and flag the currency in evidence.",
    "Where an MSA and SOW conflict, the MSA controls unless the SOW says otherwise — playbook v7, §3.2.",
    "Indemnity carve-outs outside the cap do not change liability_cap_usd; they belong in evidence.",
    "A termination-on-change-of-control right is reported as change_of_control = true even absent a consent requirement.",
    "Renewal 'by mutual written agreement' is not auto-renewal; the deal model treats those contracts as expiring.",
    "If two clauses conflict and no amendment resolves them, report the more conservative reading and say so in evidence.",
    "Evidence must cite section numbers; reviewers spot-check 10% of output against source text.",
]

WORKED_EXAMPLES = """
## Worked examples
Example A: a contract with free assignment and a $400,000 aggregate cap → change_of_control \
false, liability_cap_usd 400000, risk_tier LOW.
Example B: a contract requiring consent for change of control with a $1M cap → \
change_of_control true, cap 1000000, exactly one red flag → risk_tier MEDIUM.
Example C: a contract with a consent requirement whose cap was deleted by amendment → \
change_of_control true, liability_cap_usd null, both red flags → risk_tier HIGH.
"""


def _build_playbook() -> str:
    parts = [PLAYBOOK_CORE, "\n## Clause library\n"]
    for name, definition, red_flag in CLAUSE_LIBRARY:
        parts.append(f"### {name}\n{definition}\nRed flag note: {red_flag}\n")
    parts.append("\n## Negotiation precedent notes\n")
    for note in PRECEDENT_NOTES:
        parts.append(f"- {note}")
    parts.append(WORKED_EXAMPLES)
    text = "\n".join(parts)
    # Pad deterministically past the largest minimum cacheable prefix (4096 tokens on
    # Opus/Haiku; ~4 chars per token) so the caching lever works on every model.
    annex = "\n\n## Annex: clause library (deal-team annotated re-issue)\n" + "\n".join(
        f"### {n}\n{d}\nRed flag note: {r}\n" for n, d, r in CLAUSE_LIBRARY)
    while len(text) < 22000:
        text += annex
    return text


PLAYBOOK = _build_playbook()
print(f"Playbook built: {len(PLAYBOOK):,} chars (~{len(PLAYBOOK)//4:,} tokens) — identical on every call")

# %% [markdown]
# **The grader.** Five audited fields per contract, deterministic checks, gold prepared by
# hand. Accuracy is the **gate**: an optimization that breaks accuracy isn't an optimization,
# it's a liability transfer from your COGS line to your malpractice insurance.

# %%
def _normalize_cap(value):
    """Coerce model output for liability_cap_usd into a float or None."""
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip().lower().replace("$", "").replace(",", "")
        if v in ("", "none", "null", "n/a", "uncapped", "no cap"):
            return None
        try:
            return float(v)
        except ValueError:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def grade_fields(fields: dict, gold: dict) -> dict:
    """Per-field pass/fail for one contract."""
    f = fields or {}
    checks = {}
    checks["auto_renewal"] = bool(f.get("auto_renewal")) == gold["auto_renewal"]
    checks["change_of_control"] = bool(f.get("change_of_control")) == gold["change_of_control"]
    cap = _normalize_cap(f.get("liability_cap_usd"))
    if gold["liability_cap_usd"] is None:
        checks["liability_cap_usd"] = cap is None
    else:
        checks["liability_cap_usd"] = cap is not None and abs(cap - gold["liability_cap_usd"]) < 1
    gl, gg = str(f.get("governing_law") or "").lower(), gold["governing_law"].lower()
    checks["governing_law"] = bool(gl) and (gg in gl or gl in gg)
    checks["risk_tier"] = str(f.get("risk_tier") or "").strip().upper() == gold["risk_tier"]
    return checks


def extract_json(text: str):
    """Pull the first valid JSON object out of free text (v0 needs this; v1 may not)."""
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    for start, ch in enumerate(text):
        if ch != "{":
            continue
        depth = 0
        for end in range(start, len(text)):
            if text[end] == "{":
                depth += 1
            elif text[end] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:end + 1])
                    except json.JSONDecodeError:
                        break
    return None


print("Grader ready — 5 audited fields × 6 contracts = 30 checks; gate is ≥ 90% (27/30)")

# %% [markdown]
# **ClauseScan v0 — exactly as inherited.** Read it the way you'd read a client's codebase on
# day one of a rescue: not to mock it, but to find where the money and the seconds go.

# %%
EXTRACT_INSTRUCTION = (
    "Determine the five audited fields for the contract below. Respond with a JSON object "
    "with keys auto_renewal, change_of_control, liability_cap_usd, governing_law, risk_tier, "
    "evidence.\n\nCONTRACT:\n"
)


def clausescan_v0(contract: dict) -> dict:
    """The pipeline the demo team shipped. Two passes, Opus for everything, no caching,
    verbose output, no streaming, sequential by construction."""
    t0 = time.perf_counter()
    calls = []

    # PASS 1 — "first, really understand the contract" (a full briefing nobody reads)
    r1 = client.messages.create(
        model=MODEL_OPUS, max_tokens=8000,
        system=PLAYBOOK,  # 5K+ tokens, re-billed at full price on every single call
        messages=[{"role": "user", "content":
                   "Write a detailed clause-by-clause briefing of this contract, with "
                   "commentary on anything unusual, before any extraction is attempted.\n\n"
                   + contract["text"]}],
    )
    calls.append((MODEL_OPUS, r1.usage))

    # PASS 2 — extraction, with the briefing AND the contract AND the playbook again
    r2 = client.messages.create(
        model=MODEL_OPUS, max_tokens=8000,
        system=PLAYBOOK,
        messages=[{"role": "user", "content":
                   "Here is an internal briefing of a contract:\n\n" + text_of(r1)
                   + "\n\nNow, explain your reasoning step by step in detail, and then output "
                   + "a JSON object with keys auto_renewal, change_of_control, "
                   + "liability_cap_usd, governing_law, risk_tier, evidence.\n\nCONTRACT:\n"
                   + contract["text"]}],
    )
    calls.append((MODEL_OPUS, r2.usage))

    return {
        "fields": extract_json(text_of(r2)),
        "calls": calls,
        "elapsed": time.perf_counter() - t0,
    }


print("ClauseScan v0 loaded — run the portfolio in the next cell")

# %%
def run_portfolio(pipeline, contracts=CONTRACTS, gold=GOLD, workers: int = 0,
                  warm_first: bool = True) -> dict:
    """Run a pipeline over the contract sample; grade, time, and price every contract."""

    def run_one(contract):
        out = pipeline(contract)
        checks = grade_fields(out["fields"], gold[contract["id"]])
        return {
            "id": contract["id"], "vendor": contract["vendor"],
            "fields": out["fields"], "checks": checks,
            "n_correct": sum(checks.values()), "n_fields": len(checks),
            "elapsed": out["elapsed"],
            "cost": sum(calculate_cost(m, u) for m, u in out["calls"]),
            "calls": len(out["calls"]),
        }

    wall0 = time.perf_counter()
    if workers and len(contracts) > 1:
        rows = []
        head = contracts[0]
        if warm_first:
            rows.append(run_one(head))  # one call writes the cache before the fan-out
            remaining = contracts[1:]
        else:
            remaining = contracts
        with ThreadPoolExecutor(max_workers=workers) as ex:
            rows.extend(ex.map(run_one, remaining))
    else:
        rows = [run_one(c) for c in contracts]
    wall = time.perf_counter() - wall0

    total_fields = sum(r["n_fields"] for r in rows)
    return {
        "rows": rows,
        "accuracy": sum(r["n_correct"] for r in rows) / total_fields,
        "p50_s": statistics.median(r["elapsed"] for r in rows),
        "cost_per_contract": sum(r["cost"] for r in rows) / len(rows),
        "total_cost": sum(r["cost"] for r in rows),
        "wall_s": wall,
    }


def print_report(report: dict, label: str):
    rows = [[r["id"], r["vendor"][:28], f"{r['n_correct']}/{r['n_fields']}",
             f"{r['elapsed']:.1f}s", f"${r['cost']:.4f}", r["calls"]]
            for r in report["rows"]]
    print(f"\n── {label} " + "─" * max(1, 64 - len(label)))
    print(tabulate(rows, headers=["ID", "Vendor", "Fields", "TTC", "Cost", "Calls"],
                   tablefmt="simple"))
    print(f"\n  accuracy {report['accuracy']*100:.0f}%   ·   p50 {report['p50_s']:.1f}s/contract"
          f"   ·   ${report['cost_per_contract']:.4f}/contract"
          f"   ·   batch wall-clock {report['wall_s']:.0f}s")


print("Running ClauseScan v0 on the six-contract sample (sequential, ~2-4 minutes — "
      "the slowness IS the data)...")
BASELINE = run_portfolio(clausescan_v0)
print_report(BASELINE, "ClauseScan v0 — the inherited baseline")

sla_p50 = "PASS" if BASELINE["p50_s"] <= 5 else "FAIL"
print(f"\n  SLA check: p50 ≤ 5s → {sla_p50}   ·   accuracy ≥ 90% → "
      f"{'PASS' if BASELINE['accuracy'] >= 0.9 else 'FAIL'}")

# %% [markdown]
# **The diagnosis.** v0 is *correct* — and that's exactly what makes it dangerous: nothing
# looks broken in the demo, so it ships, and the waste compounds 248,000 times. Name the sins:
#
# 1. **Opus for everything.** Most of a contract estate is boilerplate a cheaper model reads
#    perfectly well.
# 2. **The 5K-token playbook is re-billed at full price on every call** — twice per contract.
#    It never changes. It's the textbook prompt-caching candidate.
# 3. **Two serial round trips** where one would do. The "briefing" pass doubles latency and
#    bills its own output as the next call's input.
# 4. **Verbose free-text output** — "explain step by step in detail, then JSON." Output tokens
#    are **5× the price** of input tokens, and every extra token also costs wall-clock time.
# 5. **No streaming.** The analyst stares at a dead screen for the full TTC.
# 6. **Sequential batch.** Six contracts take six contracts' worth of wall-clock; 248,000 take
#    a quarter-million.
#
# Five of these are levers you pull to make the surviving calls cheaper or faster. The sixth,
# the round trip, isn't — it's a call you delete before you optimize the rest. Part 4 takes
# them one at a time, with the meter running.

# %% [markdown]
# # Part 4 · The six levers
#
# **First, eliminate the round trip you never needed.** Before you make any call cheaper, delete
# the one you didn't need. Every serial round trip pays full freight: network + prefill +
# generation, and chained calls re-bill earlier output as new input. v0's "briefing" pass is
# pure round-trip tax — the same tax you'll meet again with tool calls (request → `tool_use` →
# execute → result → response) and multi-step chains. Collapse steps that don't earn their
# latency. v0's two passes become one, and every lever below operates on that single surviving
# call.
#
# ## Lever 1 — Prompt caching: stop re-buying the playbook
#
# One call per contract now. Make it stop re-buying the playbook.
#
# Caching is a **prefix match**: tools → system → messages, and any byte change invalidates
# everything after it. Our playbook is a frozen prefix by design. Mark it with `cache_control`
# and the API stores the processed prefix: the first call pays a **1.25×** write premium;
# every call inside the TTL (5 min) reads it back at **0.1×** — and skips reprocessing it,
# which also cuts TTFT.
#
# Field notes for client work: minimum cacheable prefix is **4096 tokens on Opus/Haiku, 2048
# on Sonnet** (shorter prefixes silently don't cache); keep volatile content — timestamps,
# request IDs, the contract itself — *after* the cached block; and verify with
# `usage.cache_read_input_tokens`, not vibes.

# %%
CACHED_SYSTEM = [{"type": "text", "text": PLAYBOOK, "cache_control": {"type": "ephemeral"}}]


def cached_extract(contract, model=MODEL_SONNET):
    t0 = time.perf_counter()
    resp = client.messages.create(
        model=model, max_tokens=1200, system=CACHED_SYSTEM,
        messages=[{"role": "user", "content": EXTRACT_INSTRUCTION + contract["text"]}],
    )
    return resp, time.perf_counter() - t0


for label in ("COLD (writes cache)", "WARM (reads cache)"):
    resp, secs = cached_extract(CONTRACTS[0])
    u = resp.usage
    print(f"{label:20s} {secs*1000:6.0f}ms · uncached_in={u.input_tokens:>5} · "
          f"cache_write={u.cache_creation_input_tokens or 0:>5} · "
          f"cache_read={u.cache_read_input_tokens or 0:>5} · "
          f"cost=${calculate_cost(MODEL_SONNET, u):.5f}")

print("\nWatch cache_read jump from 0 to ~the playbook size, and cost drop with it.")

# %% [markdown]
# ## Lever 2 — Model routing: a portfolio, not a model
#
# On a 248K-contract estate, maybe 15–25% genuinely need senior attention — amendments that
# rewrite terms, conflicting clauses, unusual indemnities. The rest is boilerplate. So run a
# **triage pass on Haiku** (cheap, fast, tiny output) and route: ROUTINE → Haiku or Sonnet,
# COMPLEX → Sonnet or Opus. This is staffing leverage, the thing your firm already understands:
# you don't put the senior partner on every NDA.

# %%
TRIAGE_SYSTEM = (
    "You triage supplier contracts for a diligence pipeline. Classify the contract as "
    "COMPLEX if it contains any of: an amendment that modifies earlier terms, clauses that "
    "conflict with each other, unusual or uncapped indemnities, or liability terms that are "
    "ambiguous or implied rather than stated. Otherwise classify it as ROUTINE."
)

TRIAGE_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "complexity": {"type": "string", "enum": ["ROUTINE", "COMPLEX"]},
            "reason": {"type": "string", "description": "One short sentence."},
        },
        "required": ["complexity", "reason"],
        "additionalProperties": False,
    },
}


def triage(contract):
    resp = client.messages.create(
        model=MODEL_HAIKU, max_tokens=150, system=TRIAGE_SYSTEM,
        messages=[{"role": "user", "content": contract["text"]}],
        output_config={"format": TRIAGE_SCHEMA},
    )
    verdict = extract_json(text_of(resp)) or {}
    return verdict.get("complexity", "COMPLEX"), resp  # fail safe: unknown → COMPLEX


rows = []
for c in CONTRACTS:
    verdict, resp = triage(c)
    rows.append([c["id"], c["vendor"][:28], verdict,
                 f"${calculate_cost(MODEL_HAIKU, resp.usage):.5f}"])
print(tabulate(rows, headers=["ID", "Vendor", "Triage", "Triage cost"], tablefmt="simple"))
print("\nA few tenths of a cent buys the routing decision. The savings come from what it "
      "routes AWAY from Opus.")

# %% [markdown]
# ## Lever 3 — Output discipline: schemas, not essays
#
# Output tokens cost **5× input tokens** and each one costs generation time (TTC ≈ TTFT +
# output_tokens ÷ OTPS). v0 asks for step-by-step prose *plus* JSON. The fix is **structured
# outputs**: `output_config.format` with a JSON schema. The response *is* the deliverable —
# valid JSON, no parsing regex, no preamble — and the risk rubric lives in the field
# descriptions, so the schema doubles as the spec your QA partner signs off on.
#
# Two dials that live in the same neighborhood:
# - `max_tokens` — a hard ceiling; right-size it to the artifact (our JSON needs ~300, not 8000).
# - `output_config.effort` — Sonnet/Opus accept `low`–`max` to trade depth for tokens.
#   **It errors on Haiku 4.5** — Haiku is already the low-latency tier.

# %%
EXTRACTION_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "auto_renewal": {"type": "boolean",
                             "description": "True only if the contract renews automatically absent notice."},
            "change_of_control": {"type": "boolean",
                                  "description": "True if assignment/change of control requires consent or grants a termination right."},
            "liability_cap_usd": {"anyOf": [{"type": "number"}, {"type": "null"}],
                                  "description": "Aggregate cap in USD. null if no cap is stated or an amendment removed it."},
            "governing_law": {"type": "string",
                              "description": "Jurisdiction, e.g. 'Delaware' or 'England and Wales'."},
            "risk_tier": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"],
                          "description": "HIGH = change-of-control restriction AND no cap. MEDIUM = exactly one red flag. LOW = neither."},
            "evidence": {"type": "string",
                         "description": "One sentence citing the section numbers relied on."},
        },
        "required": ["auto_renewal", "change_of_control", "liability_cap_usd",
                     "governing_law", "risk_tier", "evidence"],
        "additionalProperties": False,
    },
}


def extract_structured(contract, model=MODEL_SONNET, cached=True, effort=None):
    """One call, schema-constrained output, optional cached playbook and effort dial."""
    t0 = time.perf_counter()
    output_config = {"format": EXTRACTION_SCHEMA}
    if effort and model != MODEL_HAIKU:   # effort errors on Haiku 4.5
        output_config["effort"] = effort
    resp = client.messages.create(
        model=model, max_tokens=1000,
        system=CACHED_SYSTEM if cached else PLAYBOOK,
        messages=[{"role": "user", "content": EXTRACT_INSTRUCTION + contract["text"]}],
        output_config=output_config,
    )
    return {"fields": extract_json(text_of(resp)), "calls": [(model, resp.usage)],
            "elapsed": time.perf_counter() - t0}


demo = extract_structured(CONTRACTS[0], model=MODEL_SONNET, effort="low")
model_used, u = demo["calls"][0]
v0_row = BASELINE["rows"][0]
print(f"Structured single pass: {demo['elapsed']:.1f}s · {u.output_tokens} output tokens · "
      f"${calculate_cost(model_used, u):.5f}")
print(f"v0 on the same contract: {v0_row['elapsed']:.1f}s · ${v0_row['cost']:.4f} across "
      f"{v0_row['calls']} calls — most of it prose nobody reads.")
print(json.dumps(demo["fields"], indent=2))

# %% [markdown]
# ## Lever 4 — Streaming: TTFT is the UX number
#
# Stream the one surviving call. TTC is an economics number; **TTFT is a UX number** — it's the
# difference between an analyst who watches the answer assemble and one who alt-tabs to email.

# %%
t0 = time.perf_counter()
ttft, total, sresp = _stream_request(
    [{"role": "user", "content": EXTRACT_INSTRUCTION + CONTRACTS[0]["text"]}],
    model=MODEL_SONNET, max_tokens=1000, system=CACHED_SYSTEM,
    output_config={"format": EXTRACTION_SCHEMA},
)
print(f"Streamed single pass:  TTFT {ttft*1000:.0f}ms · TTC {total*1000:.0f}ms")
print(f"v0 two-pass TTC on this contract was {BASELINE['rows'][0]['elapsed']:.1f}s — "
      f"and its TTFT *was* its TTC, because nothing streamed.")

# %% [markdown]
# ## Lever 5 — Parallelize the portfolio (and warm the cache first)
#
# Contracts are independent; review them concurrently. One subtlety the pros get right: a
# cache entry only becomes readable once the first response **begins streaming** — N identical
# requests fired simultaneously all pay the cold price. So: **send one contract first to warm
# the cache, then fan out.** (`run_portfolio` has done this for you all along: `warm_first=True`.)
#
# Field notes: respect your rate-limit tier; the SDK retries 429s with backoff automatically,
# but a fan-out sized to your TPM limit is cheaper than a fan-out that thrashes retries.

# %%
seq = run_portfolio(lambda c: extract_structured(c, model=MODEL_SONNET), workers=0)
par = run_portfolio(lambda c: extract_structured(c, model=MODEL_SONNET), workers=4)
print(f"Sequential portfolio wall-clock: {seq['wall_s']:.0f}s")
print(f"Parallel (warm-first, 4 workers): {par['wall_s']:.0f}s")
print(f"Accuracy held at {par['accuracy']*100:.0f}% — speed that costs accuracy is not speed.")

# %% [markdown]
# ## Lever 6 — Two-speed architecture: the Batch API lane
#
# Not every contract needs an analyst watching. Split the workload like an engagement team
# would:
#
# - **Interactive lane** — working sessions, streamed, p50 ≤ 5s, everything you just built.
# - **Backfill lane** — the other ~235K documents run overnight through the **Batch API** at
#   **50% off all token charges** (most batches finish within an hour; results persist 29 days).
#
# Same models, same prompts, same schema — half the price, in exchange for latency you weren't
# going to spend anyway. This split — *what the client touches* vs *what runs in the dark* —
# is the single highest-leverage architecture question on volume engagements.

# %%
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request


def build_batch_requests(contracts):
    return [
        Request(
            custom_id=c["id"],
            params=MessageCreateParamsNonStreaming(
                model=MODEL_SONNET, max_tokens=1000,
                system=CACHED_SYSTEM,  # caching works in batches too (best-effort hits)
                messages=[{"role": "user", "content": EXTRACT_INSTRUCTION + c["text"]}],
                output_config={"format": EXTRACTION_SCHEMA},
            ),
        )
        for c in contracts
    ]


batch_requests = build_batch_requests(CONTRACTS)
print(f"Built {len(batch_requests)} batch requests "
      f"(limits: 100K requests / 256 MB per batch)")

interactive_cpc = par["cost_per_contract"]
print(f"\nInteractive lane:  ${interactive_cpc:.4f}/contract")
print(f"Batch lane (50%):  ${interactive_cpc * BATCH_DISCOUNT:.4f}/contract")

RUN_BATCH = False  # flip to True to actually submit; poll with client.messages.batches.retrieve()
if RUN_BATCH:
    batch = client.messages.batches.create(requests=batch_requests)
    print(f"Submitted batch {batch.id} — status: {batch.processing_status}")
    print("Poll: client.messages.batches.retrieve(batch.id); "
          "results: client.messages.batches.results(batch.id)")

# %% [markdown]
# # Part 5 · The optimization sprint 🏁
#
# Now it's yours. `clausescan_v1` below starts as a faithful copy of v0 — it will score
# **≈ 100** (that's the baseline index). Pull levers by editing `CONFIG`, then re-run the
# scorecard. When `CONFIG` stops being enough, edit the function itself — that's encouraged.
#
# **Scoring** (the SLA, condensed into one number):
#
# ```
# accuracy < 90%  →  SCORE = 0 (gate — no partial credit for fast, wrong answers)
# otherwise       →  SCORE = 50 × (baseline_$ / your_$) + 50 × (baseline_p50 / your_p50)
# ```
#
# v0 = 100. Cut cost 4× and latency 2× → 300. A strong configuration clears 400.
#
# **Rules of engagement:**
# 1. Accuracy ≥ 90% on the sample — and your pipeline must *read the contracts*. Hardcoding
#    answers scores zero with the holdout set (and your code gets read out loud).
# 2. Any model, any caching, any routing, any concurrency. Creativity within the API is the point.
# 3. Post your leaderboard line in the session chat after each run. Beat the table.

# %% [markdown]
# ### ✏️ YOUR TURN — this CONFIG is your steering wheel
#
# Edit it HERE, re-run, watch the score.

# %%
# ✏️ YOUR TURN: edit this CONFIG
CONFIG = {
    # Lever 2 — routing. Try: triage_routing=True, routine_model=MODEL_HAIKU,
    #                         complex_model=MODEL_SONNET
    "triage_routing": False,
    "routine_model": MODEL_OPUS,
    "complex_model": MODEL_OPUS,

    # Lever 1 — cache the playbook prefix
    "cache_playbook": False,

    # Lever 3 + the round-trip collapse — one schema pass instead of briefing → essay → JSON
    "structured_single_pass": False,
    "max_tokens": 8000,           # right-size once output is disciplined (~1000)
    "effort": None,               # "low" | "medium" | "high" — Sonnet/Opus only

    # Lever 5 — portfolio concurrency (0 = sequential; warm-first is automatic)
    "parallel_workers": 0,
}


def clausescan_v1(contract: dict) -> dict:
    """Your pipeline. Starts as v0; ends wherever you take it."""
    t0 = time.perf_counter()
    calls = []

    # Routing (Lever 2)
    model = CONFIG["routine_model"]
    if CONFIG["triage_routing"]:
        verdict, tri_resp = triage(contract)
        calls.append((MODEL_HAIKU, tri_resp.usage))
        model = CONFIG["complex_model"] if verdict == "COMPLEX" else CONFIG["routine_model"]

    # Cached vs raw playbook (Lever 1)
    system = CACHED_SYSTEM if CONFIG["cache_playbook"] else PLAYBOOK

    if CONFIG["structured_single_pass"]:
        # Levers 3 + 4 — one pass, schema output, optional effort dial
        output_config = {"format": EXTRACTION_SCHEMA}
        if CONFIG["effort"] and model != MODEL_HAIKU:
            output_config["effort"] = CONFIG["effort"]
        resp = client.messages.create(
            model=model, max_tokens=CONFIG["max_tokens"], system=system,
            messages=[{"role": "user", "content": EXTRACT_INSTRUCTION + contract["text"]}],
            output_config=output_config,
        )
        calls.append((model, resp.usage))
        fields = extract_json(text_of(resp))
    else:
        # v0's two-pass flow, verbatim
        r1 = client.messages.create(
            model=model, max_tokens=CONFIG["max_tokens"], system=system,
            messages=[{"role": "user", "content":
                       "Write a detailed clause-by-clause briefing of this contract, with "
                       "commentary on anything unusual, before any extraction is attempted.\n\n"
                       + contract["text"]}],
        )
        calls.append((model, r1.usage))
        r2 = client.messages.create(
            model=model, max_tokens=CONFIG["max_tokens"], system=system,
            messages=[{"role": "user", "content":
                       "Here is an internal briefing of a contract:\n\n" + text_of(r1)
                       + "\n\nNow, explain your reasoning step by step in detail, and then "
                       + "output a JSON object with keys auto_renewal, change_of_control, "
                       + "liability_cap_usd, governing_law, risk_tier, evidence.\n\nCONTRACT:\n"
                       + contract["text"]}],
        )
        calls.append((model, r2.usage))
        fields = extract_json(text_of(r2))

    return {"fields": fields, "calls": calls, "elapsed": time.perf_counter() - t0}


def engagement_score(report: dict, baseline: dict) -> int:
    if report["accuracy"] < 0.90:
        return 0
    return round(50 * baseline["cost_per_contract"] / max(report["cost_per_contract"], 1e-9)
                 + 50 * baseline["p50_s"] / max(report["p50_s"], 1e-9))


def run_scorecard(pipeline, label="clausescan_v1", contracts=CONTRACTS, gold=GOLD):
    report = run_portfolio(pipeline, contracts=contracts, gold=gold,
                           workers=CONFIG.get("parallel_workers", 0))
    print_report(report, label)
    score = engagement_score(report, BASELINE)
    levers = []
    if CONFIG.get("triage_routing"):
        levers.append("routing")
    if CONFIG.get("cache_playbook"):
        levers.append("cache")
    if CONFIG.get("structured_single_pass"):
        levers.append("schema-1pass")
    if CONFIG.get("effort"):
        levers.append(f"effort-{CONFIG['effort']}")
    if CONFIG.get("parallel_workers"):
        levers.append(f"parallel-x{CONFIG['parallel_workers']}")
    gate = "" if report["accuracy"] >= 0.90 else "  ⛔ accuracy gate failed — score zeroed"
    print(f"\n  ENGAGEMENT SCORE: {score}  (v0 baseline = 100){gate}")
    print(f"  📋 leaderboard line →  SCORE {score} · acc {report['accuracy']*100:.0f}% · "
          f"p50 {report['p50_s']:.1f}s · ${report['cost_per_contract']:.4f}/contract · "
          f"levers: {'+'.join(levers) if levers else 'none'}")
    return report


print("Sprint harness ready. Edit CONFIG above, then run the next cell. Repeat until proud.")

# %%
my_report = run_scorecard(clausescan_v1)

# %% [markdown]
# **Iterate.** Suggested path — but find your own; the leaderboard rewards imagination:
#
# 1. `structured_single_pass=True, max_tokens=1000` — watch output tokens and TTC collapse.
# 2. `cache_playbook=True` — run twice; the second pass shows the warm-cache economics.
# 3. `triage_routing=True, routine_model=MODEL_HAIKU, complex_model=MODEL_SONNET` — the
#    portfolio play.
# 4. `parallel_workers=4` — wall-clock for the working session.
# 5. Then go off-script: trim `EXTRACT_INSTRUCTION`, try `effort="low"` on Sonnet, route
#    HIGH-risk contracts to Opus for a second opinion, drop the playbook for routine contracts
#    and keep it for complex ones (what does that do to cache hits?), pre-warm the cache with a
#    `max_tokens=0` request at session start...
#
# When you think you're done: the holdout. Two contracts your pipeline has never seen — because
# an optimization that only works on the sample is called overfitting in our line of work, and
# a finding in the client's.

# %%
HOLDOUT_CONTRACTS = [
    {
        "id": "C-201", "vendor": "Vanta Marketing Collective",
        "text": """MARKETING SERVICES AGREEMENT — Vanta Marketing Collective ("Agency") and Volta Industrial Group ("Client").

1. SERVICES. Brand, digital, and trade-show marketing services per approved statements of work.
2. TERM. Eighteen (18) months from the Effective Date, expiring automatically at the end of the term. Any renewal requires a new agreement executed by both parties.
3. FEES. Monthly retainer of $22,000 plus pre-approved pass-through costs.
4. LIMITATION OF LIABILITY. EACH PARTY'S TOTAL AGGREGATE LIABILITY UNDER THIS AGREEMENT IS LIMITED TO SEVENTY-FIVE THOUSAND U.S. DOLLARS ($75,000), EXCLUDING ONLY AMOUNTS PAYABLE UNDER SECTION 5 (INDEMNIFICATION FOR IP CLAIMS).
5. INDEMNIFICATION. Agency indemnifies Client against third-party IP claims arising from Agency-created materials.
6. ASSIGNMENT. Either party may assign this Agreement without consent upon written notice, including in connection with a change of control.
7. GOVERNING LAW. This Agreement is governed by the laws of the Province of Ontario, Canada.""",
    },
    {
        "id": "C-202", "vendor": "Quarry Industrial Supply Pte. Ltd.",
        "text": """INDUSTRIAL SUPPLY AGREEMENT — Quarry Industrial Supply Pte. Ltd. ("Quarry") and Volta Industrial Group ("Purchaser").

1. SUPPLY. Quarry supplies abrasives, fasteners, and consumables per released purchase orders.
2. TERM AND RENEWAL. Two (2) year initial term, automatically renewing for successive one-year terms unless either party gives ninety (90) days' written notice of non-renewal.
3. PRICING. Per the Annex A price file; freight prepaid for orders over S$5,000.
4. LIMITATION OF LIABILITY. QUARRY'S AND PURCHASER'S RESPECTIVE AGGREGATE LIABILITY ARISING OUT OF OR RELATING TO THIS AGREEMENT SHALL NOT EXCEED TWO MILLION U.S. DOLLARS ($2,000,000) IN THE AGGREGATE.
5. ASSIGNMENT AND CHANGE OF CONTROL. Neither party may assign or transfer this Agreement, including by merger, acquisition, or change of control, without the prior written consent of the other party. Any purported assignment without consent is void.
6. COMPLIANCE. Each party complies with applicable export-control and anti-corruption laws.
7. GOVERNING LAW. This Agreement is governed by the laws of Singapore.""",
    },
]

HOLDOUT_GOLD = {
    "C-201": {"auto_renewal": False, "change_of_control": False, "liability_cap_usd": 75000,
              "governing_law": "Ontario",   "risk_tier": "LOW"},
    "C-202": {"auto_renewal": True,  "change_of_control": True,  "liability_cap_usd": 2000000,
              "governing_law": "Singapore", "risk_tier": "MEDIUM"},
}

RUN_HOLDOUT = False  # flip to True when your CONFIG is final
if RUN_HOLDOUT:
    run_scorecard(clausescan_v1, label="clausescan_v1 — HOLDOUT",
                  contracts=HOLDOUT_CONTRACTS, gold=HOLDOUT_GOLD)
else:
    print("Holdout armed. Set RUN_HOLDOUT = True when your CONFIG is final — "
          "no tuning against the holdout; that's the rule.")

# %% [markdown]
# # Part 6 · The steering-committee slide
#
# Optimization that stays in a notebook is a hobby. This cell turns your measured numbers into
# the before/after economics a steering committee actually reads — with the assumptions printed,
# because a benefits case without stated assumptions is the first thing a client audit
# committee throws out.

# %%
ASSUMPTIONS = {
    "contracts_in_estate": 248_000,
    "production_scale_factor": 8,   # production contracts ~8× lab-sample tokens; input-dominated
                                    # cost scales ~linearly with document length
    "interactive_share": 0.15,      # analyst working sessions (full price, streamed)
    "batch_share": 0.85,            # overnight Batch API backfill (50% off)
    "fee_per_contract": 0.75,       # what HELVETICA bills per reviewed contract
}


def steering_committee_slide(baseline: dict, optimized: dict, a=ASSUMPTIONS):
    n, scale = a["contracts_in_estate"], a["production_scale_factor"]

    def estate_cogs(cpc, two_speed: bool):
        per = cpc * scale
        if two_speed:
            per = per * a["interactive_share"] + per * a["batch_share"] * BATCH_DISCOUNT
        return per * n

    before = estate_cogs(baseline["cost_per_contract"], two_speed=False)
    after = estate_cogs(optimized["cost_per_contract"], two_speed=True)
    revenue = n * a["fee_per_contract"]

    rows = [
        ["Accuracy (audited fields)", f"{baseline['accuracy']*100:.0f}%",
         f"{optimized['accuracy']*100:.0f}%", "gate held"],
        ["p50 latency / contract", f"{baseline['p50_s']:.1f}s", f"{optimized['p50_s']:.1f}s",
         f"{baseline['p50_s']/max(optimized['p50_s'],1e-9):.1f}× faster"],
        ["Lab cost / contract", f"${baseline['cost_per_contract']:.4f}",
         f"${optimized['cost_per_contract']:.4f}",
         f"{baseline['cost_per_contract']/max(optimized['cost_per_contract'],1e-9):.1f}× cheaper"],
        ["Estate COGS (248K docs)", f"${before:,.0f}", f"${after:,.0f}",
         f"${before-after:,.0f} saved"],
        ["Engagement margin", f"{(revenue-before)/revenue*100:.0f}%",
         f"{(revenue-after)/revenue*100:.0f}%", "on $0.75/contract fee"],
        ["Interactive SLA (p50 ≤ 5s)",
         "PASS" if baseline["p50_s"] <= 5 else "FAIL",
         "PASS" if optimized["p50_s"] <= 5 else "FAIL", ""],
    ]
    print("PROJECT HELVETICA — Inference optimization: before / after")
    print(tabulate(rows, headers=["Metric", "v0 (inherited)", "Optimized", "Delta"],
                   tablefmt="grid"))
    print("\nAssumptions: " + ", ".join(f"{k}={v}" for k, v in a.items()))
    print("Production COGS modeled as lab $/contract × scale factor; optimized lane split "
          f"{a['interactive_share']:.0%} interactive / {a['batch_share']:.0%} batch at 50% off.")


steering_committee_slide(BASELINE, my_report)

# %% [markdown]
# # Wrap-up — the levers, as a client checklist
#
# Walk into any inference-cost conversation with this list and you will earn your rate:
#
# 1. **Measure first** — TTFT, TTC, OTPS, cache-aware $/unit. No baseline, no benefits case.
# 2. **Model portfolio + routing** — cheap models for volume, expensive models for judgment, a
#    triage pass deciding which is which.
# 3. **Cache the frozen prefix** — playbooks, tool definitions, system prompts. Verify with
#    `cache_read_input_tokens`, mind the per-model minimums, keep volatile bytes out of the prefix.
# 4. **Discipline the output** — structured outputs as the deliverable spec, right-sized
#    `max_tokens`, `effort` dialed to the task (never on Haiku).
# 5. **Collapse round trips, stream the rest** — every serial call is latency and re-billed
#    context; TTFT is the UX number.
# 6. **Parallelize with care** — warm the cache, then fan out inside your rate limits.
# 7. **Two-speed architecture** — interactive lane for humans, Batch API (50% off) for the dark
#    backlog. Decide per workload, not per project.
# 8. **Gate everything on accuracy** — a quality eval runs *before* the optimization victory lap.
#    (Yesterday's evals session is the other half of this lab.)
#
# **Docs to bookmark:** platform.claude.com/docs → Prompt caching · Batch processing ·
# Structured outputs · Effort · Streaming · Pricing.
