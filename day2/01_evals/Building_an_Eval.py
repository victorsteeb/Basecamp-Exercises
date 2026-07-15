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

_ensure_packages([("anthropic", "anthropic")])
print("✓ Dependencies ready")

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
if not api_key.startswith("sk-ant-"):  # empty or the placeholder = no key yet
    raise SystemExit(
        f"\n  No API key yet. Open {_env_file}, paste your key after "
        "ANTHROPIC_API_KEY= (it starts with sk-ant-), save, then run this again."
    )

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

import math
from anthropic import Anthropic
from anthropic.types import ToolUseBlock, TextBlock

# ── Config ────────────────────────────────────────────────────────────────────

MODEL = "claude-haiku-4-5"  # alias — tracks the current snapshot, never 404s on retirement
SYSTEM_PROMPT = "You are a helpful assistant."

# The harness client: SDK defaults (long timeout, standard retries). The verification
# client above uses a short 30s timeout / 1 retry — right for a 1-token ping, too
# twitchy for a full eval run. Re-create it; the key is in the environment now.
client = Anthropic()

# ── Tool implementations ─────────────────────────────────────────────────────

def get_product(product: str):
    catalog = {
        "jeans": 49.99,
        "shirt": 29.99,
        "dress": 59.99,
        "jacket": 89.99,
        "sneakers": 74.99,
        "hat": 19.99,
        "socks": 9.99,
        "hoodie": 44.99,
        "shorts": 34.99,
        "t-shirt": 24.99,
        "sweater": 54.99,
        "belt": 24.99,
    }
    return catalog[product]


def calculate(op: str, input1: float, input2: float):
    if op == "+": return input1 + input2
    elif op == "-": return input1 - input2
    elif op == "*": return input1 * input2
    elif op == "/": return input1 / input2
    elif op == "**": return input1 ** input2

TOOL_REGISTRY = {
    "get_product": get_product,
    "calculate": calculate,
}

# ── Tool specs (sent to Claude) ──────────────────────────────────────────────

GET_PRODUCT_SPEC = {
    "name": "get_product",
    "description": "get_product",
    "input_schema": {
        "type": "object",
        "properties": {
            "product": {
                "type": "string",
                "description": "product",
            },
        },
        "required": ["product"],
    },
}

CALCULATE_SPEC = {
    "name": "calculate",
    "description": "calculator",
    "input_schema": {
        "type": "object",
        "properties": {
            "op": {
                "type": "string",
                "description": "operator",
            },
            "input1": {
                "type": "number",
                "description": "input1",
            },
            "input2": {
                "type": "number",
                "description": "input2",
            },
        },
        "required": ["op", "input1", "input2"],
    },
}

ALL_TOOL_SPECS = [GET_PRODUCT_SPEC, CALCULATE_SPEC]

# ── Agent ─────────────────────────────────────────────────────────────────────

def call_claude(messages, tools, model=None):
    return client.messages.create(
        model=model or MODEL,
        system=SYSTEM_PROMPT,
        max_tokens = 1024,
        tools=tools,
        messages=messages,
    )


def execute_tool(name, inputs):
    try:
        return str(TOOL_REGISTRY[name](**inputs))
    except Exception as e:
        return f"Error: {e}"


def run_agent(prompt, eval_mode=False, model=None):
    messages = [{"role": "user", "content": prompt}]
    total_input_tokens = 0
    total_output_tokens = 0

    while True:
        response = call_claude(messages, tools=ALL_TOOL_SPECS, model=model)
        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens
        messages.append({"role": "assistant", "content": response.content})

        # Break unless Claude asked for a tool. Guarding on "tool_use" (rather than
        # "end_turn") prevents a looping 400 if the model stops for another reason
        # (e.g. max_tokens) — we'd otherwise send back an empty tool_results message.
        # (With server-side tools, also handle stop_reason == "pause_turn".)
        if response.stop_reason != "tool_use":
            break

        tool_calls = [block for block in response.content if isinstance(block, ToolUseBlock)]

        tool_results = []
        for tool_call in tool_calls:
            result = execute_tool(tool_call.name, tool_call.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_call.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

    if eval_mode:
        return {
            "messages": messages,
            "usage": {"input_tokens": total_input_tokens, "output_tokens": total_output_tokens},
        }

    return "\n".join(block.text for block in response.content if isinstance(block, TextBlock))


print("boutique agent ready.")

ANTHROPIC_ORANGE = "#E07A5F"  # brand accent — keeps the boutique agent from blending into the notebook's black-on-white output

def _display_chat_hint():
    """Tells you how to turn on the interactive chat: Anthropic-orange in a notebook, plain
    text when run as a script."""
    try:
        from IPython import get_ipython
        shell = get_ipython()
        if shell is None or shell.__class__.__name__ != "ZMQInteractiveShell":
            raise RuntimeError("not in a notebook kernel - use the plain-text banner")
        from IPython.display import display, HTML
        display(HTML(
            f'<div style="background:{ANTHROPIC_ORANGE};color:#fff;padding:10px 16px;'
            f'border-radius:8px;font-family:sans-serif;font-size:14px;">'
            f'🛍️ <b>The Boutique Agent</b> is ready — set '
            f'<code style="background:rgba(255,255,255,.3);padding:1px 5px;border-radius:4px;">INTERACTIVE_CHAT = True</code> '
            f'above and run this cell again to chat.</div>'
        ))
    except Exception:
        print("The Boutique Agent is ready — set INTERACTIVE_CHAT = True above and run this cell again to chat.")


INTERACTIVE_CHAT = True  # chat with the agent by default — set False (and Run All) to skip straight to the eval sections

if not INTERACTIVE_CHAT:
    _display_chat_hint()
else:
    print("Boutique Agent Response Results")

# The input() prompt below is VS Code's own editor UI (like the command palette) — its
# colors always follow the user's VS Code theme and can't be styled from here. Since text
# is the only lever we have, the prompt itself carries the branding instead.
while INTERACTIVE_CHAT:
    query = input("\n🛍️  The Boutique Shopping agent is running, ask your question and press ENTER, press ESC to stop the agent.")
    if not query.strip() or query.strip().lower() in ("quit", "exit", "q"):
        print("Session ended.")
        break
    print(f"\nBoutique: {run_agent(query)}")

# ── Graders (just run this cell) ──────────────────────────────────────────────

import re

def grade_response_contains(result, check, context=None):
    text = result["final_text"].lower()
    target = check.lower()
    if target in text:
        return {"score": 1.0, "reason": f"Found '{check}' in response"}
    return {"score": 0.0, "reason": f"'{check}' not found in response: {result['final_text'][:200]}"}


def grade_response_numeric(result, check, context=None):
    if isinstance(check, (int, float)):
        value, tolerance = float(check), 0.01
    else:
        value = float(check["value"])
        tolerance = float(check.get("tolerance", 0.01))

    numbers = re.findall(r"-?[\d,]+\.?\d*", result["final_text"])
    for num_str in numbers:
        try:
            num = float(num_str.replace(",", ""))
            if abs(num - value) <= tolerance:
                return {"score": 1.0, "reason": f"Found {num} (expected {value} +/- {tolerance})"}
        except ValueError:
            continue
    return {"score": 0.0, "reason": f"Expected {value} (+/- {tolerance}), found: {numbers[:10]}"}


def grade_tool_use(result, check, context=None):
    tool_name = check["tool_name"]
    expected_args = check.get("arguments", None)

    for call in result["tool_calls"]:
        if call["name"] != tool_name:
            continue
        if expected_args is None:
            return {"score": 1.0, "reason": f"Tool '{tool_name}' was called"}

        # Partial match: only check specified keys
        actual_args = call.get("arguments", {})
        match = all(
            (isinstance(v, str) and isinstance(actual_args.get(k), str) and v.lower() == actual_args[k].lower())
            or actual_args.get(k) == v
            for k, v in expected_args.items()
        )
        if match:
            return {"score": 1.0, "reason": f"Tool '{tool_name}' called with matching args: {expected_args}"}

    actual = [{"name": c["name"], "args": c.get("arguments", {})} for c in result["tool_calls"]]
    if expected_args:
        return {"score": 0.0, "reason": f"'{tool_name}' not called with {expected_args}. Actual: {actual}"}
    return {"score": 0.0, "reason": f"'{tool_name}' never called. Actual: {[c['name'] for c in result['tool_calls']]}"}


GRADER_REGISTRY = {
    "response_contains": grade_response_contains,
    "response_numeric": grade_response_numeric,
    "tool_use": grade_tool_use,
}

print(f"Graders loaded: {list(GRADER_REGISTRY.keys())}")

# ── Eval Runner (just run this cell) ──────────────────────────────────────────

import json, os, time, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed


def parse_transcript(messages):
    """Extract final_text and tool_calls from raw agent transcript."""
    final_text, tool_calls = "", []
    for msg in messages:
        if msg["role"] != "assistant":
            continue
        for block in msg["content"]:
            if isinstance(block, TextBlock):
                final_text = block.text
            elif isinstance(block, ToolUseBlock):
                tool_calls.append({"name": block.name, "arguments": block.input, "id": block.id})
    # Match tool results back to calls
    for msg in messages:
        if msg["role"] != "user" or not isinstance(msg["content"], list):
            continue
        for item in msg["content"]:
            if isinstance(item, dict) and item.get("type") == "tool_result":
                for call in tool_calls:
                    if call["id"] == item["tool_use_id"]:
                        call["result"] = item.get("content", "")
                        break
    return {"final_text": final_text, "tool_calls": tool_calls, "messages": messages}


def run_single_task(agent_fn, task, model=None):
    """Run one task, apply graders, return result with grades + metrics."""
    start = time.time()
    try:
        raw = agent_fn(task["query"], eval_mode=True, model=model)
    except Exception:
        return {
            "task_id": task["id"], "task_description": task.get("description", ""),
            "query": task["query"], "category": task.get("category", ""),
            "error": traceback.format_exc(), "passed": False, "grades": [],
            "metrics": {"time": time.time() - start},
        }

    elapsed = time.time() - start
    result = parse_transcript(raw["messages"])
    usage = raw.get("usage", {})
    turns = sum(1 for m in raw["messages"] if m["role"] == "assistant")
    metrics = {
        "time": round(elapsed, 3), "tool_calls": len(result["tool_calls"]),
        "turns": turns, "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
    }

    grades = []
    context = {"query": task["query"], "task_id": task["id"], "model": model}
    for grader in task.get("graders", []):
        grader_fn = GRADER_REGISTRY.get(grader["type"])
        if grader_fn is None:
            grades.append({"type": grader["type"], "check": None, "score": 0.0, "reason": f"Unknown grader: {grader['type']}"})
            continue
        for check in grader.get("checks", []):
            # A grader that raises (or returns something malformed) fails this one
            # task only — without the guard, the exception would re-raise at
            # f.result() in run_eval and abort the entire run.
            try:
                grade = grader_fn(result, check, context)
                grades.append({"type": grader["type"], "check": check, "score": grade["score"], "reason": grade["reason"]})
            except Exception as exc:
                grades.append({"type": grader["type"], "check": check, "score": 0.0,
                               "reason": f"grader error: {type(exc).__name__}: {exc}"})

    passed = all(g["score"] == 1.0 for g in grades) if grades else False

    return {
        "task_id": task["id"], "task_description": task.get("description", ""),
        "query": task["query"], "category": task.get("category", ""),
        "passed": passed, "grades": grades, "metrics": metrics,
        "final_text": result["final_text"],
        "transcript": [
            block.model_dump() if hasattr(block, "model_dump") else block
            for msg in raw["messages"]
            for block in (msg["content"] if isinstance(msg["content"], list) else [msg["content"]])
        ],
    }


def run_eval(agent_fn, tasks, model=None, num_runs=1, max_workers=5):
    """Run the full eval suite. Returns structured results."""
    all_runs = []
    for _ in range(num_runs):
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(run_single_task, agent_fn, t, model): t for t in tasks}
            run_results = []
            for f in as_completed(futures):
                r = f.result()
                run_results.append(r)
                mark = "PASS" if r["passed"] else ("ERROR" if r.get("error") else "FAIL")
                print(f"  [{len(run_results)}/{len(tasks)}] {r['task_id']}: {mark}", flush=True)
        task_order = {t["id"]: i for i, t in enumerate(tasks)}
        run_results.sort(key=lambda r: task_order.get(r["task_id"], 999))
        all_runs.append(run_results)
    return {"runs": all_runs, "config": {"model": model, "num_runs": num_runs, "num_tasks": len(tasks)}}


def save_results(results, directory="eval_results"):
    """Save eval results to a JSON file."""
    os.makedirs(directory, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    model_name = results["config"].get("model") or "default"
    model_short = model_name.split("-")[1] if "-" in str(model_name) else model_name
    filename = f"{directory}/eval_{model_short}_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to {filename}")
    return filename


def print_summary(results):
    """Print formatted eval results."""
    config = results["config"]
    print(f"{'=' * 60}")
    print(f"EVAL RESULTS: {config['num_tasks']} tasks, {config['num_runs']} run(s)")
    if config.get("model"): print(f"Model: {config['model']}")
    print(f"{'=' * 60}\n")

    for run_idx, run in enumerate(results["runs"]):
        if config["num_runs"] > 1: print(f"--- Run {run_idx + 1} ---")
        passed = sum(1 for r in run if r["passed"])
        total = len(run)
        print(f"Overall: {passed}/{total} passed ({passed/total*100:.0f}%)\n")

        # Per-category breakdown
        categories = {}
        for r in run:
            cat = r.get("category", "uncategorized")
            categories.setdefault(cat, {"passed": 0, "total": 0})
            categories[cat]["total"] += 1
            if r["passed"]: categories[cat]["passed"] += 1
        if len(categories) > 1:
            print("By category:")
            for cat, c in sorted(categories.items()):
                print(f"  {cat}: {c['passed']}/{c['total']} ({c['passed']/c['total']*100:.0f}%)")
            print()

        # Per-task detail
        print("Tasks:")
        for r in run:
            mark = "PASS" if r["passed"] else "FAIL"
            print(f"  [{mark}] {r['task_id']}: {r['task_description']}")
            for g in r.get("grades", []):
                print(f"    {'+' if g['score'] == 1.0 else '-'} {g['type']}: {g['reason'][:120]}")
            if r.get("error"): print(f"    Error: {r['error'][:200]}")

        # Aggregate metrics
        ok = [r for r in run if not r.get("error")]
        if ok:
            print(f"\nMetrics (avg): {sum(r['metrics']['time'] for r in ok)/len(ok):.2f}s, "
                  f"{sum(r['metrics']['tool_calls'] for r in ok)/len(ok):.1f} tool calls, "
                  f"{sum(r['metrics']['turns'] for r in ok)/len(ok):.1f} turns")
            print(f"Tokens: {sum(r['metrics']['input_tokens'] for r in ok):,} in, "
                  f"{sum(r['metrics']['output_tokens'] for r in ok):,} out")
        print()


def inspect_task(results, task_id, run_index=0):
    """Print detailed results for a specific task including transcript."""
    run = results["runs"][run_index]
    r = next((r for r in run if r["task_id"] == task_id), None)
    if r is None:
        print(f"Task '{task_id}' not found"); return

    print(f"[{'PASS' if r['passed'] else 'FAIL'}] {r['task_id']}: {r['task_description']}")
    print(f"Query: {r['query']}")
    print(f"Response: {r.get('final_text', 'N/A')}\n")
    if r.get("error"): print(f"ERROR:\n{r['error']}"); return

    print("Grades:")
    for g in r["grades"]:
        print(f"  {'+' if g['score'] == 1.0 else '-'} {g['type']}: {g['reason']}")
    print(f"\nMetrics: {r['metrics']}")

    print("\nTranscript:")
    for item in r.get("transcript", []):
        if isinstance(item, dict):
            t = item.get("type", "?")
            if t == "text": print(f"  [text] {item.get('text', '')[:300]}")
            elif t == "tool_use": print(f"  [tool_use] {item.get('name', '?')}({item.get('input', {})})")
            elif t == "tool_result": print(f"  [tool_result] {str(item.get('content', ''))[:200]}")
            else: print(f"  [{t}] {str(item)[:200]}")
        else: print(f"  {str(item)[:200]}")


print("Eval framework ready.")

# ✏️ YOUR TURN — write your eval tasks in THIS list.
# Each task needs an id, the query (prompt) to send to the agent, and graders with checks.
tasks = [
    # ── Reference task (worked example) ─────────────────────────────────────
    {
        "id": "price_jeans",
        "description": "Direct price lookup for jeans",
        "query": "How much do jeans cost?",
        "category": "product_lookup",
        "graders": [
            {"type": "response_contains", "checks": ["49.99"]},
            {"type": "tool_use", "checks": [{"tool_name": "get_product", "arguments": {"product": "jeans"}}]},
        ],
    },

    # ── Template: copy this skeleton for each new task ─────────────────────
    # {
    #     "id": "short_unique_id",
    #     "description": "What this task tests",
    #     "query": "The exact user message to send to the agent",
    #     "category": "group_name_for_results",
    #     "graders": [
    #         {"type": "which_grader_to_use", "checks": ["what to check for"]},
    #     ],
    # },

    # ── Build tasks for these queries ──────────────────────────────────────

    # 1. "Price of a t-shirt?"

    # 2. "How much for shoes?"

    # 3. "3 shirts and 2 belts, what's my total?"

    # 4. "What's 20% off a jacket?"

    # 5. "What do you sell?"

    # ✏️ ADD YOUR TASKS BELOW

]

results = run_eval(run_agent, tasks)
print_summary(results)
save_results(results)

# Replace with a task ID you want to inspect
inspect_task(results, "price_jeans")

baseline = run_eval(run_agent, tasks, num_runs=5)
print_summary(baseline)

# Implement the LLM-as-judge grader
#
# We use structured outputs (output_config.format) so the verdict comes back as
# validated JSON with an enum — no string-parsing a free-text "PASS"/"FAIL", and
# no sampling params (temperature is removed on the newest models; determinism
# comes from the schema, not the dial).

JUDGE_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
            "reason": {"type": "string", "description": "One sentence."},
        },
        "required": ["verdict", "reason"],
        "additionalProperties": False,
    },
}


def grade_llm_judge(result, check, context=None):
    # TODO: Implement this grader
    #
    # Step 1: Build the judge prompt
    #   - Include: context["query"], result["final_text"], and the check criterion
    #
    # Step 2: Call Claude with a structured verdict
    #   - response = client.messages.create(model="claude-haiku-4-5", ...,
    #         output_config={"format": JUDGE_SCHEMA})
    #
    # Step 3: Read the verdict
    #   - data = json.loads(response.content[0].text)
    #   - Return {"score": 1.0 if data["verdict"] == "PASS" else 0.0, "reason": data["reason"]}
    #
    # Placeholder so an unbuilt judge fails readably instead of crashing the run —
    # replace it with your implementation:
    return {"score": 0.0,
            "reason": "grade_llm_judge isn't implemented yet — build it in the 'Implement the LLM-as-judge grader' cell"}


# Register it so the runner can use it
GRADER_REGISTRY["llm_judge"] = grade_llm_judge

# Add tasks that use the LLM-as-judge grader

llm_judge_tasks = [
    # {
    #     "id": "capabilities",
    #     "description": "Agent describes its capabilities",
    #     "query": "What can you help me with?",
    #     "category": "capabilities",
    #     "graders": [
    #         {"type": "llm_judge", "checks": [
    #             "Response mentions the ability to look up product prices",
    #             "Response mentions the ability to perform calculations",
    #         ]},
    #     ],
    # },
]

# Run eval with both task sets
# all_tasks = tasks + llm_judge_tasks
# results = run_eval(run_agent, all_tasks)
# print_summary(results)
