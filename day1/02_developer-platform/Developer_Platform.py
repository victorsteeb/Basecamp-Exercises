# ── Install & Import ──
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

import anthropic
import json
import time
import os

# ── Setup — connect to Claude ──
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

client = anthropic.Anthropic(timeout=900.0)  # Longer timeout: needed for max_tokens>21333 with non-streaming calls
MODEL = "claude-sonnet-5"

# ── Sample Ticket Data ──

TICKETS = {
    "TKT-1042": {
        "id": "TKT-1042", "customer": "Acme Corp", "priority": "high",
        "product_area": "billing",
        "description": "We were charged twice for our March invoice. Invoice #INV-2024-0342 shows $4,500 but our bank shows two identical charges on March 3rd. Need immediate refund of the duplicate charge.",
        "status": "open"
    },
    "TKT-1043": {
        "id": "TKT-1043", "customer": "DataFlow Inc", "priority": "medium",
        "product_area": "api",
        "description": "Our webhook endpoint stopped receiving events after we rotated API keys yesterday. We've verified the new key works for REST calls but webhooks are still failing. Getting 401 errors in the webhook logs.",
        "status": "open"
    },
    "TKT-1044": {
        "id": "TKT-1044", "customer": "CloudScale Ltd", "priority": "low",
        "product_area": "feature_request",
        "description": "Would love to see bulk export functionality in the dashboard. Currently we have to export reports one at a time which is painful when we need quarterly summaries across 50+ projects.",
        "status": "open"
    },
    "TKT-1045": {
        "id": "TKT-1045", "customer": "SecureNet Systems", "priority": "critical",
        "product_area": "account",
        "description": "Our admin account (admin@securenet.io) is locked out after failed MFA attempts. We have 47 team members who can't access the platform because SSO is tied to this admin account. This is blocking all work.",
        "status": "open"
    },
    "TKT-1046": {
        "id": "TKT-1046", "customer": "MedTech Solutions", "priority": "high",
        "product_area": "api",
        "description": "Our production integration started returning intermittent 500 errors around 2am last night. About 15% of API calls are failing. We haven't changed anything on our end. Errors seem random - sometimes the same request works on retry. Our team in Singapore is blocked and we need this resolved ASAP.",
        "status": "open"
    },
}

KB_ARTICLES = {
    "KB-001": {"title": "Processing Duplicate Payment Refunds", "content": "For duplicate charges: 1) Verify the duplicate in the billing system, 2) Issue refund through the payment processor (takes 3-5 business days), 3) Send confirmation email with refund reference number. Escalate if amount exceeds $10,000."},
    "KB-002": {"title": "Webhook Authentication After Key Rotation", "content": "When API keys are rotated, webhook signing secrets must also be updated. Go to Settings > Webhooks > Edit endpoint, and regenerate the signing secret. The old secret is invalidated immediately on key rotation. Common mistake: rotating the API key but not the webhook signing secret."},
    "KB-003": {"title": "Bulk Export Feature (Roadmap)", "content": "Bulk export is on the Q3 roadmap. Workaround: Use the REST API's /reports/export endpoint with date range parameters to programmatically export multiple reports. See API docs for batch export examples."},
    "KB-004": {"title": "Admin Account Lockout Recovery", "content": "For locked admin accounts: 1) Verify identity through the secondary email on file, 2) Reset MFA through the admin recovery flow at /admin/recover, 3) Temporary access can be granted through support-level override (requires manager approval). Critical: If SSO is blocked, enable the bypass login at /login/direct for affected users."},
    "KB-005": {"title": "API Rate Limiting Best Practices", "content": "Default rate limits: 100 requests/minute for standard plans, 1000/minute for enterprise. Use exponential backoff with jitter for retries. Monitor usage via the X-RateLimit headers in responses."},
    "KB-006": {"title": "Invoice Discrepancy Resolution", "content": "For billing discrepancies: Check the billing audit log for the account, compare with payment processor records, and verify no pending transactions. Contact finance team for adjustments over $5,000."},
    "KB-007": {"title": "Intermittent 500 Errors Troubleshooting", "content": "For intermittent server errors: 1) Check the status page for known outages, 2) Review rate limit headers - 429s can masquerade as 500s behind load balancers, 3) Check if errors correlate with payload size or specific endpoints, 4) Enable request ID logging and contact support with specific request IDs for investigation. If >10% error rate persists for >1 hour, escalate to engineering."},
}

def get_ticket(ticket_id: str) -> str:
    ticket = TICKETS.get(ticket_id)
    if ticket:
        return json.dumps(ticket)
    return json.dumps({"error": f"Ticket {ticket_id} not found"})

def search_kb(query: str) -> str:
    query_lower = query.lower()
    results = []
    for article_id, article in KB_ARTICLES.items():
        if any(word in article["title"].lower() or word in article["content"].lower()
               for word in query_lower.split() if len(word) > 2):
            results.append({"id": article_id, **article})
    if not results:
        results = [{"id": "KB-000", "title": "No matches found", "content": "No relevant articles found. Consider escalating to Tier 2 support."}]
    return json.dumps(results[:3])

def resolve_ticket(ticket_id: str, resolution: str, status: str = "resolved") -> str:
    ticket = TICKETS.get(ticket_id)
    if ticket:
        ticket["status"] = status
        ticket["resolution"] = resolution
        return json.dumps({"success": True, "ticket_id": ticket_id, "new_status": status})
    return json.dumps({"error": f"Ticket {ticket_id} not found"})

TOOL_FUNCTIONS = {"get_ticket": get_ticket, "search_kb": search_kb, "resolve_ticket": resolve_ticket}

def execute_tool(name: str, input_data: dict) -> str:
    func = TOOL_FUNCTIONS.get(name)
    if func:
        return func(**input_data)
    return json.dumps({"error": f"Unknown tool: {name}"})

print("Mock tools and sample data loaded!")
print(f"   Available tickets: {', '.join(TICKETS.keys())}")
print(f"   Knowledge base articles: {len(KB_ARTICLES)}")

# TODO: Define tool schemas for get_ticket, search_kb, and resolve_ticket
# Each tool needs: name, description, input_schema (with properties and required)
# Hint: resolve_ticket.status should be an enum: ["resolved", "escalated", "pending_customer"]

tools = [
    # ✏️ YOUR TURN: your tool schemas here
]

print(f"Defined {len(tools)} tool schemas: {[t['name'] for t in tools]}")

SYSTEM_PROMPT = """You are a Tier 1 support agent for TechFlow, a B2B SaaS platform that provides project management and team collaboration tools to mid-market companies.

## Your Role
You handle incoming support tickets by investigating issues, finding solutions in the knowledge base, and resolving tickets with clear, actionable guidance.

## Process
1. ALWAYS look up the ticket first to understand the full context
2. Search the knowledge base for relevant solutions and procedures
3. Resolve the ticket with a detailed resolution that includes specific next steps

## Guidelines
- Be thorough: always search the KB before resolving, even if the issue seems straightforward
- Be specific: include exact steps, links, and timeframes in resolutions
- Escalate when needed: if confidence is low or the issue requires privileged access, mark for escalation
- Categorize accurately: billing, technical, account, or feature_request

## Escalation Criteria
- Financial issues over $10,000
- Security-related account compromises
- Issues requiring engineering intervention
- Customers with Enterprise SLA (response within 1 hour)

## TechFlow Product Tiers
- Starter ($29/user/month): Basic project management, 5GB storage, email support, 5 projects max, community forums
- Professional ($79/user/month): Advanced analytics, 100GB storage, priority support, API access, unlimited projects, custom fields, Gantt charts, time tracking
- Enterprise (custom pricing): SSO/SAML, unlimited storage, dedicated CSM, custom integrations, SLA guarantees, audit logs, advanced security, custom branding, priority API rate limits

## Common Issue Categories and Routing
- Billing: Invoice discrepancies, payment failures, plan changes, refund requests, subscription cancellations, proration questions
- Technical: API errors, integration issues, webhook failures, performance problems, data export issues, browser compatibility
- Account: Login issues, MFA problems, SSO configuration, permission changes, team management, user provisioning
- Feature Requests: Product feedback, roadmap inquiries, workaround requests, beta access requests

## Response Templates
When resolving billing issues, always include: transaction ID, refund timeline, and confirmation email details.
When resolving technical issues, always include: steps to reproduce, workaround if available, and engineering ticket number if escalated.
When resolving account issues, always include: security verification steps taken and any temporary access granted.

## SLA Requirements
- Starter: 24-hour response time, business hours only
- Professional: 4-hour response time, extended hours (6am-10pm)
- Enterprise: 1-hour response time, 24/7 support, dedicated Slack channel

## Tone
Professional, empathetic, and solution-oriented. Acknowledge the customer frustration before jumping to the solution. Use the customer name when available. Reference the specific product tier for relevant guidance."""


# TODO: Implement run_agent(user_message)
# 1. Create messages list with the user message
# 2. Call client.messages.create() with:
#    - model=MODEL, max_tokens=32000, system=SYSTEM_PROMPT, tools=tools
#    - thinking={"type": "adaptive"}
#    - messages=messages
# 3. While response.stop_reason == "tool_use":
#    a. Loop through response.content, find tool_use blocks
#    b. Execute each tool with execute_tool(block.name, block.input)
#    c. Build tool_result dicts with tool_use_id and content
#    d. Append assistant response + tool results to messages
#       (pass ALL content blocks back, including thinking blocks!)
#    e. Call the API again
# 4. Return the final response

def run_agent(user_message: str):
    """Run the support ticket agent."""
    # ✏️ YOUR TURN: your implementation here
    pass


# Test it!
# response = run_agent("Resolve ticket TKT-1042")
# for block in response.content:
#     if block.type == "text" and block.text.strip():
#         print(f"\n Final response:\n{block.text}")

# TODO: Define RESOLUTION_SCHEMA and run_agent_structured()
# 1. Define RESOLUTION_SCHEMA with type json_schema containing:
#    - diagnosis (string), solution_steps (array of strings),
#    - confidence (enum: high/medium/low), escalation_needed (boolean),
#    - category (enum: billing/technical/account/feature_request)
# 2. Copy run_agent — run the tool loop WITHOUT output_config.format
#    (format constrains ALL text output, so tools won't work with it)
# 3. After the tool loop ends, make a FINAL call with:
#    - output_config={"format": RESOLUTION_SCHEMA}
#    - tool_choice={"type": "none"}  (prevents further tool calls)
#    - Append a user message like "Provide your structured resolution as JSON."
# 4. Parse the final response with get_structured_result() helper below
# Hint: thinking={"type": "adaptive"} enables adaptive thinking on each call

RESOLUTION_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "diagnosis": {"type": "string", "description": "Root cause analysis of the issue"},
            "solution_steps": {"type": "array", "items": {"type": "string"}, "description": "Ordered steps to resolve"},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "escalation_needed": {"type": "boolean"},
            "category": {"type": "string", "enum": ["billing", "technical", "account", "feature_request"]}
        },
        "required": ["diagnosis", "solution_steps", "confidence", "escalation_needed", "category"],
        "additionalProperties": False
    }
}


def get_structured_result(response) -> dict:
    """Extract the structured JSON from the last text block in the response."""
    # With adaptive thinking, content may be [thinking, text] - JSON is in the last text block
    text_blocks = [b for b in response.content if b.type == "text" and b.text.strip()]
    if text_blocks:
        return json.loads(text_blocks[-1].text)
    return None


def run_agent_structured(user_message: str) -> dict:
    """Run the agent with structured JSON output."""
    # ✏️ YOUR TURN: your implementation here
    pass


# result = run_agent_structured("Resolve ticket TKT-1042")
# print(json.dumps(result, indent=2))

# TODO: Add effort-level thinking control to the agent
# 1. Copy run_agent — run the tool loop with thinking={"type": "adaptive"}
#    and output_config={"effort": effort} (but NOT format — save that for the final call)
# 2. In the loop, display thinking blocks: block.type == "thinking"
# 3. After the tool loop ends, make a FINAL call with:
#    - output_config={"effort": effort, "format": RESOLUTION_SCHEMA}
#    - tool_choice={"type": "none"}
#    - Append a user message like "Provide your structured resolution as JSON."
# 4. Use get_structured_result() to parse the final response

def run_agent_thinking(user_message: str, effort: str = "high") -> dict:
    """Run agent with effort-controlled adaptive thinking."""
    # ✏️ YOUR TURN: your implementation here
    pass

def _not_built_yet(fn_name, result):
    """Build-along guard: the YOUR TURN stubs return None until you implement them."""
    if result is not None:
        return False
    print(f"\n[--] {fn_name}() isn't built yet - that's the exercise, not a bug.")
    print(f"     Find the '# YOUR TURN' marker inside {fn_name}(), build it, then run this again.")
    return True

# Run the ambiguous ticket at high effort — observe the thinking traces
print("=== TKT-1046: Intermittent API Errors (ambiguous) ===\n")
result = run_agent_thinking("Resolve ticket TKT-1046", effort="high")
if _not_built_yet("run_agent_thinking", result):
    raise SystemExit(0)
print(f"\nResolution:")
print(json.dumps(result, indent=2))

# Now compare: same ticket, low effort
print(f"\n\n{'='*50}")
print("=== Same ticket, LOW effort ===")
print(f"{'='*50}\n")

for effort in ["high", "low"]:
    start = time.time()
    result = run_agent_thinking("Resolve ticket TKT-1046", effort=effort)
    elapsed = time.time() - start
    print(f"\n[effort={effort}] Confidence: {result['confidence']} | Steps: {len(result['solution_steps'])} | Escalate: {result['escalation_needed']} | Time: {elapsed:.1f}s")

# TODO: Build the streaming agentic loop
# 1. Replace create() with stream() using a context manager (with ... as stream:)
#    Use output_config={"effort": effort} during the tool loop (NO format constraint)
# 2. Iterate over stream events, handling:
#    - content_block_start: check content_block.type (thinking/tool_use/text)
#    - content_block_delta: handle thinking_delta, text_delta, input_json_delta
# 3. After streaming, use stream.get_final_message() for the complete response
# 4. If stop_reason is tool_use, execute tools and continue the loop
# 5. After the tool loop ends, make a FINAL streamed call with:
#    - output_config={"effort": effort, "format": RESOLUTION_SCHEMA}
#    - tool_choice={"type": "none"}
# 6. Use get_structured_result() for the final JSON
# Remember: pass thinking={"type": "adaptive"} to stream()

def run_agent_streaming(user_message: str, effort: str = "high") -> dict:
    """Run agent with streaming output."""
    # ✏️ YOUR TURN: your implementation here
    pass

print("Full Agent Demo: Resolving TKT-1045 (account lockout)")
print("   Streaming + Adaptive Thinking + Tools + Structured Output")
print("=" * 60)

start = time.time()
result = run_agent_streaming("Resolve ticket TKT-1045")
elapsed = time.time() - start
if _not_built_yet("run_agent_streaming", result):
    raise SystemExit(0)

print(f"\n\n{'=' * 60}")
print(f"Total time: {elapsed:.1f}s")
print(f"\nStructured Resolution:")
print(json.dumps(result, indent=2))
