# =============================================================================
# Diagnose, Fix, Brief — Meridian (Partner Basecamp · Day 1)
# =============================================================================
# A stalled client pilot. The support agent gives confidently wrong answers and
# marks tickets "resolved" when they aren't. The client thinks it's the model.
#
# Your job: prove it isn't. The model is fine. The LEVERS around it are broken.
# Find them, fix them, and watch the score move — without touching the model.
#
# THE LEVERS YOU EDIT (real files in this folder — open them, change them, rerun):
#   - system-prompt-coordinator.txt        the orchestrator's instructions
#   - system-prompt-subagent-*.txt         each specialist's instructions
#   - coordinator-tools.json               the coordinator's tool surface
#   - subagent-*-tools.json                each specialist's tools
#
# HOW TO RUN
#   pip install anthropic
#   export ANTHROPIC_API_KEY=sk-ant-...
#   python Diagnose_Fix_Brief.py                 # run the eval, see the scoreboard
#   python Diagnose_Fix_Brief.py --model claude-opus-4-8   # try a bigger model...
#                                                          # ...watch cost rise, RESOLVED stay NO
# =============================================================================

import os
import re
import sys
import json
import argparse
import datetime
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

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

from anthropic import Anthropic

# Replace characters the console can't encode (e.g. on Windows pipes) instead of crashing.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(errors="replace")

# Load a .env (next to this script or any parent — e.g. a single repo-root .env) so
# `python Diagnose_Fix_Brief.py` picks up ANTHROPIC_API_KEY without an explicit export.
import pathlib as _pl
for _d in [_pl.Path.cwd().resolve(), *_pl.Path.cwd().resolve().parents]:
    _envf = _d / ".env"
    if _envf.is_file():
        for _line in _envf.read_text().splitlines():
            _line = _line.strip()
            if _line.startswith("ANTHROPIC_API_KEY=") and not _line.startswith("#"):
                _v = _line.split("=", 1)[1].strip().strip('"').strip("'")
                if _v.startswith("sk-ant-"):
                    os.environ.setdefault("ANTHROPIC_API_KEY", _v)
        break

client = Anthropic()

HERE = os.path.dirname(os.path.abspath(__file__))

# ── Config ───────────────────────────────────────────────────────────────────
# The base model. It is plenty capable — every failure in this system is
# structural, not a model-capability ceiling. Swapping in a bigger model costs
# more and does NOT move RESOLVED. That's the whole point of the exercise.
MODEL = "claude-sonnet-5"

# $ per 1M tokens (input, output). Used to price each run so the cost lever is visible.
# Rates: platform.claude.com/docs/en/about-claude/pricing — add a line for any model not listed.
# Verify against the current pricing page before quoting in a deliverable (cached June 2026).
PRICING = {
    "claude-fable-5":    (10.00, 50.00),
    "claude-opus-4-8":   (5.00, 25.00),
    "claude-opus-4-7":   (5.00, 25.00),
    "claude-opus-4-6":   (5.00, 25.00),
    "claude-sonnet-5":   (3.00, 15.00),
    "claude-haiku-4-5":  (1.00, 5.00),
}

MAX_TOKENS = 4096
COORDINATOR_MAX_TURNS = 16
SUBAGENT_MAX_TURNS = 10


# ── Scenario state (the mock backend the agents' tools read from) ─────────────
# This is the client's world for ticket T-4471. The tools below return slices of
# it: the SSO config, billing history, audit log, and so on. What's actually wrong,
# and what a correct resolution requires, is for the room to work out — not spelled
# out here.

CUSTOMER = {
    "customer_id": "cust_8fK2mQ",
    "name": "Northwind Traders",
    "tier": "growth",
    "tier_since": "2026-02-26",
    "mrr": 800,
    "seats_used": 42,
    "seats_limit": 50,
    "sso_enabled": True,
    "sso_provider": "okta",
    "primary_contact": "devops@northwind-traders.example",
    "billing_contact": "finance@northwind-traders.example",
    "signup": "2024-08-15",
}

# Second customer — used only by the held-out ticket T-4490 (a different
# specialist pair: technical + billing, no account issue).
CUSTOMER_2 = {
    "customer_id": "cust_7bX3",
    "name": "Tailspin Toys",
    "tier": "scale",
    "primary_contact": "ops@tailspin-toys.example",
    "billing_contact": "ap@tailspin-toys.example",
    "signup": "2025-01-20",
}

# Third customer — used only by the held-out ticket T-4503.
CUSTOMER_3 = {
    "customer_id": "cust_5Pq8",
    "name": "Fabrikam Robotics",
    "tier": "growth",
    "primary_contact": "m.tanaka@fabrikam-robotics.example",
    "billing_contact": "accounts@fabrikam-robotics.example",
    "signup": "2025-06-02",
}

TICKETS = {
    "T-4471": {
        "ticket_id": "T-4471",
        "submitted_by": "devops@northwind-traders.example",
        "subject": "SSO broken + owed a refund",
        "body": (
            "Two things:\n\n"
            "1. Since this morning nobody on our team can log in via Okta. We get "
            "'SAML assertion validation failed' on every attempt. Password login still "
            "works but we have that disabled for everyone except me. 40 people locked out.\n\n"
            "2. Separately — you charged us $2,000 on March 1st for the Scale plan but we "
            "downgraded to Growth ($800) on Feb 26th. I have the confirmation email. Can you "
            "refund the $1,200 difference?\n\n"
            "The SSO thing is urgent, people can't work."
        ),
        "priority": "high",
        "created_at": "2026-03-11T13:51:00Z",
    },
    "T-4490": {
        "ticket_id": "T-4490",
        "submitted_by": "ops@tailspin-toys.example",
        "subject": "API down + double charged",
        "body": (
            "Two problems:\n\n"
            "1. Since Saturday every API call comes back 401 Unauthorized — all endpoints, "
            "nothing changed on our side. Our integration is dead in the water.\n\n"
            "2. We were also double-billed for January: two separate $500 charges on the same "
            "invoice. Please refund the duplicate.\n\n"
            "The API outage is the urgent one."
        ),
        "priority": "high",
        "created_at": "2026-03-09T09:15:00Z",
    },
    "T-4503": {
        "ticket_id": "T-4503",
        "submitted_by": "m.tanaka@fabrikam-robotics.example",
        "subject": "Locked out of 2FA + pentest authorization needed",
        "body": (
            "Two things:\n\n"
            "1. I replaced my phone over the weekend and lost my authenticator app, so I "
            "can't get past 2FA on my admin account (m.tanaka@fabrikam-robotics.example). "
            "Please reset my 2FA enrollment so I can re-enroll on the new phone.\n\n"
            "2. Our security team has an external penetration test scheduled against our "
            "Meridian workspace the week of March 23rd (vendor: Coalfire). Your terms of "
            "service require written authorization from Meridian before any testing "
            "starts. Please confirm we're authorized, and let us know any scope "
            "restrictions on your side."
        ),
        "priority": "high",
        "created_at": "2026-03-09T08:30:00Z",
    },
}


def _j(obj):
    return json.dumps(obj)


def _cust_for(s):
    """Map an email / identifier / customer_id to the right customer record."""
    s = str(s or "").lower()
    if "tailspin" in s or s == "cust_7bx3":
        return CUSTOMER_2
    if "fabrikam" in s or s == "cust_5pq8":
        return CUSTOMER_3
    return CUSTOMER


# ── Coordinator tools (the soup) ──────────────────────────────────────────────
# Many of these are redundant or junk — that ambiguity is one of the levers.
# spawn_specialist / write_response / escalate_to_human are handled specially in
# the run loop (see execute_coordinator_tool); the rest return mock data here.

def coord_get_ticket(ticket_id=None, **_):
    t = TICKETS.get(ticket_id)
    return _j(t) if t else _j({"error": f"ticket not found: {ticket_id}"})

def coord_get_customer(id=None, **_):
    # The trace shows this failing on the slug — kept as-is (lookup-by-slug doesn't work).
    if id == CUSTOMER["customer_id"]:
        return _j({k: CUSTOMER[k] for k in ("customer_id", "name", "tier")})
    return _j({"error": f"customer not found with id '{id}'"})

def coord_lookup_customer_info(identifier=None, **_):
    c = _cust_for(identifier)
    if c is CUSTOMER:
        return _j({
            "customer_id": c["customer_id"], "name": c["name"],
            "tier": c["tier"], "tier_since": c["tier_since"],
            "seats": c["seats_used"], "sso_enabled": c["sso_enabled"],
            "sso_provider": c["sso_provider"],
        })
    return _j({"customer_id": c["customer_id"], "name": c["name"], "tier": c["tier"]})

def coord_fetch_customer_details(customer_id=None, **_):
    c = _cust_for(customer_id)
    if c is CUSTOMER:
        return _j({
            "customer_id": c["customer_id"], "name": c["name"],
            "tier": c["tier"], "mrr": c["mrr"], "signup": c["signup"],
            "primary_contact": c["primary_contact"],
            "billing_contact": c["billing_contact"],
            "seats_used": c["seats_used"], "seats_limit": c["seats_limit"],
        })
    return _j({"customer_id": c["customer_id"], "name": c["name"], "tier": c["tier"],
               "primary_contact": c["primary_contact"], "billing_contact": c["billing_contact"],
               "signup": c["signup"]})

# Redundant / noisy tools — model has to wade through these to find the real ones.
def coord_fetch_customer_v2_databricks(**_):
    return _j({"error": "v2 warehouse query timed out"})
def coord_customer_data_retrieval(**_):
    return _j({"cust": CUSTOMER["customer_id"], "name": CUSTOMER["name"]})
def coord_search_prior_tickets(**_):
    return _j({"tickets": []})
def coord_helper(**_):
    return _j({"result": "no-op"})
def coord_process(**_):
    return _j({"result": "processed"})
def coord_check_entitlements(**_):
    return _j({"entitlements": ["growth_plan"]})
def coord_get_data(**_):
    return _j({"data": None})
def coord_tool_3_v2(**_):
    return _j({"result": "no match"})
def coord_check_system_status(system=None, **_):
    # Our systems are fine — reinforces that the SSO failure is the customer's expired cert.
    return _j({"system": system or "all", "status": "operational"})
def coord_validate(**_):
    return _j({"valid": True})

COORDINATOR_BACKEND = {
    "get_ticket": coord_get_ticket,
    "get_customer": coord_get_customer,
    "lookup_customer_info": coord_lookup_customer_info,
    "fetch_customer_details": coord_fetch_customer_details,
    "fetch_customer_v2_databricks": coord_fetch_customer_v2_databricks,
    "customer_data_retrieval": coord_customer_data_retrieval,
    "search_prior_tickets": coord_search_prior_tickets,
    "helper": coord_helper,
    "process": coord_process,
    "check_entitlements": coord_check_entitlements,
    "get_data": coord_get_data,
    "tool_3_v2": coord_tool_3_v2,
    "check_system_status": coord_check_system_status,
    "validate": coord_validate,
}


# ── Subagent tools ────────────────────────────────────────────────────────────

def sub_get_ticket(ticket_id=None, **_):
    return coord_get_ticket(ticket_id)

def sub_lookup_customer_by_email(email=None, **_):
    c = _cust_for(email)
    return _j({"customer_id": c["customer_id"], "name": c["name"]})

# account
def acct_check_sso_config(customer_id=None, **_):
    if _cust_for(customer_id) is CUSTOMER_3:
        return _j({"provider": None, "status": "not_configured",
                   "note": "workspace uses password + 2FA login; SSO was never enabled"})
    return _j({
        "provider": "okta", "status": "error",
        "idp_cert_expiry": "2026-03-11T08:00:00Z",
        "idp_cert_uploaded": "2025-03-11T14:22:00Z",
        "last_successful_auth": "2026-03-11T07:58:41Z",
        "error": "certificate_expired",
    })
def acct_check_audit_log(customer_id=None, **_):
    if _cust_for(customer_id) is CUSTOMER_3:
        return _j({"events": [
            {"timestamp": "2026-03-08T19:03:00Z", "event": "2fa_challenge_failed",
             "actor": "m.tanaka@fabrikam-robotics.example",
             "details": {"reason": "code_mismatch", "attempts": 3}},
            {"timestamp": "2026-03-09T07:55:00Z", "event": "2fa_challenge_failed",
             "actor": "m.tanaka@fabrikam-robotics.example",
             "details": {"reason": "code_mismatch", "attempts": 5}},
        ]})
    return _j({"events": [{
        "timestamp": "2026-02-26T16:42:00Z", "event": "plan_change",
        "actor": "finance@northwind-traders.example",
        "details": {"from": "scale", "to": "growth"},
    }]})
def acct_workspace_summary(customer_id=None, **_):
    if _cust_for(customer_id) is CUSTOMER_3:
        return _j({"seats_used": 17, "seats_limit": 25, "admins": 1,
                   "sso_status": "not_configured", "created": "2025-06-02"})
    return _j({"seats_used": 42, "seats_limit": 50, "admins": 2,
               "sso_status": "error", "created": "2024-08-15"})
def acct_list_users(customer_id=None, **_):
    if _cust_for(customer_id) is CUSTOMER_3:
        return _j({"users": [
            {"email": CUSTOMER_3["primary_contact"], "role": "admin",
             "last_login": "2026-03-06T17:40:00Z"},
            {"email": "j.rivera@fabrikam-robotics.example", "role": "member",
             "last_login": "2026-03-09T08:02:00Z"},
            {"email": "s.okafor@fabrikam-robotics.example", "role": "member",
             "last_login": "2026-03-08T16:21:00Z"},
        ]})
    return _j({"users": [{"email": CUSTOMER["primary_contact"], "role": "admin",
                          "last_login": "2026-03-11T07:58:00Z"}]})
def acct_modify_permissions(**_):
    return _j({"status": "updated"})
def acct_reset_2fa(**_):
    return _j({"status": "reset"})

# billing specialist tools
def bill_get_billing_history(customer_id=None, **_):
    if _cust_for(customer_id) is CUSTOMER_2:
        return _j({"invoices": [
            {"invoice_id": "INV-2026-01", "date": "2026-01-05", "amount": 500,
             "transaction_id": "txn_99100", "status": "paid", "note": "January subscription"},
            {"invoice_id": "INV-2026-01", "date": "2026-01-05", "amount": 500,
             "transaction_id": "txn_99101", "status": "paid",
             "note": "DUPLICATE charge — same invoice and day as txn_99100"},
        ]})
    return _j({"invoices": [
        {"invoice_id": "INV-2026-03", "date": "2026-03-01", "plan": "scale",
         "amount": 2000, "transaction_id": "txn_98231", "status": "paid"},
        {"invoice_id": "INV-2026-02", "date": "2026-02-01", "plan": "scale",
         "amount": 2000, "transaction_id": "txn_91044", "status": "paid"},
    ], "plan_changes": [
        {"date": "2026-02-26", "from": "scale", "to": "growth"},
    ]})
def bill_check_plan_entitlements(**_):
    return _j({"tier": "growth", "monthly": 800, "seats": 50})
def bill_issue_refund(transaction_id=None, amount=None, reason=None, **_):
    return _j({"refund_id": "re_3kf91x", "transaction_id": transaction_id,
               "amount": amount, "reason": reason, "status": "refunded"})
def bill_adjust_invoice(**_):
    return _j({"status": "credited"})
def bill_check_payment_method(**_):
    return _j({"brand": "visa", "last4": "4242", "status": "valid"})

# technical specialist tools (exercised by T-4490: 401s from an auto-rotated API key)
def tech_read_error_logs(customer_id=None, **_):
    if _cust_for(customer_id) is CUSTOMER_2:
        return _j({"errors": [{"endpoint": "ALL", "status": 401, "count": 2418,
                   "first_seen": "2026-03-07T02:03:00Z",
                   "note": "every endpoint, started abruptly Saturday"}]})
    return _j({"errors": []})
def tech_check_webhook_deliveries(**_):
    return _j({"delivered": 0, "dropped": 0})
def tech_test_api_key(**_):
    # The customer's key was auto-rotated; the old one now 401s on everything.
    return _j({"active": False, "reason": "rotated",
               "rotated_at": "2026-03-07T02:00:00Z",
               "fix": "retrieve the new key from Dashboard -> API Keys and update your config"})
def tech_inspect_integration_config(customer_id=None, **_):
    return _j({"sdk_version": "3.1.0", "last_key_rotation": "2026-03-07T02:00:00Z"})
def tech_get_rate_limit_status(**_):
    return _j({"used": 12000, "limit": 1000000})

SUBAGENT_BACKENDS = {
    "account": {
        "get_ticket": sub_get_ticket, "lookup_customer_by_email": sub_lookup_customer_by_email,
        "check_sso_config": acct_check_sso_config, "check_audit_log": acct_check_audit_log,
        "get_workspace_account_summary": acct_workspace_summary,
        "list_workspace_users": acct_list_users, "modify_permissions": acct_modify_permissions,
        "reset_2fa": acct_reset_2fa,
    },
    "billing": {
        "get_ticket": sub_get_ticket, "lookup_customer_by_email": sub_lookup_customer_by_email,
        "get_billing_history": bill_get_billing_history,
        "check_plan_entitlements": bill_check_plan_entitlements,
        "issue_refund": bill_issue_refund, "adjust_invoice": bill_adjust_invoice,
        "check_payment_method": bill_check_payment_method,
    },
    "technical": {
        "get_ticket": sub_get_ticket, "lookup_customer_by_email": sub_lookup_customer_by_email,
        "read_error_logs": tech_read_error_logs,
        "check_webhook_deliveries": tech_check_webhook_deliveries,
        "test_api_key": tech_test_api_key,
        "inspect_integration_config": tech_inspect_integration_config,
        "get_rate_limit_status": tech_get_rate_limit_status,
    },
}


# ── Lever loaders (read the editable .txt / .json files) ──────────────────────

def load_prompt(name):
    with open(os.path.join(HERE, name), "r") as f:
        text = f.read()
    # The coordinator prompt carries volatile header vars; fixed here for determinism.
    text = text.replace("{{ current_timestamp }}", "2026-03-11T13:52:14Z")
    text = text.replace("{{ request_id }}", "req_9c4e7a2b1f8d")
    return text

def load_tools(name):
    with open(os.path.join(HERE, name), "r") as f:
        return json.load(f)["tools"]


# ── The agent loop ────────────────────────────────────────────────────────────

def _usage_add(acc, usage):
    acc["input_tokens"] += getattr(usage, "input_tokens", 0) or 0
    acc["output_tokens"] += getattr(usage, "output_tokens", 0) or 0
    acc["cache_read_input_tokens"] += getattr(usage, "cache_read_input_tokens", 0) or 0
    acc["cache_creation_input_tokens"] += getattr(usage, "cache_creation_input_tokens", 0) or 0

def _text_of(content):
    return "\n".join(getattr(b, "text", "") for b in content if getattr(b, "type", None) == "text")

def _serialize(messages):
    """Turn a live message list into plain JSON for a saved reference trace."""
    out = []
    for msg in messages:
        c = msg["content"]
        if isinstance(c, str):
            out.append({"role": msg["role"], "content": c})
        else:
            out.append({"role": msg["role"], "content": [
                b if isinstance(b, dict) else b.model_dump(exclude_none=True) for b in c]})
    return out


def run_subagent(category, ticket_id, model, state):
    """Run one specialist on its own prompt + tools. Returns its writeup text."""
    category = (category or "").lower()
    if category not in SUBAGENT_BACKENDS:
        return f"Error: unknown specialist category '{category}'"

    system = load_prompt(f"system-prompt-subagent-{category}.txt")
    tools = load_tools(f"subagent-{category}-tools.json")
    backend = SUBAGENT_BACKENDS[category]

    messages = [{"role": "user", "content": f"Category: {category}\nTicket: {ticket_id}"}]

    for _ in range(SUBAGENT_MAX_TURNS):
        resp = client.messages.create(
            model=model, system=system, max_tokens=MAX_TOKENS, tools=tools, messages=messages,
        )
        _usage_add(state["usage"], resp.usage)
        messages.append({"role": "assistant", "content": resp.content})

        tool_uses = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
        if resp.stop_reason == "end_turn" or not tool_uses:
            break

        results = []
        for tu in tool_uses:
            fn = backend.get(tu.name)
            out = fn(**tu.input) if fn else _j({"error": f"unknown tool {tu.name}"})
            state["tool_calls"].append({"agent": f"subagent:{category}", "name": tu.name,
                                        "arguments": dict(tu.input)})
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": out})
        messages.append({"role": "user", "content": results})

    if state.get("capture"):
        state["transcripts"].append({"agent": f"specialist:{category}", "model": model,
                                     "system": system, "messages": _serialize(messages)})
    return _text_of(messages[-1]["content"]) if messages[-1]["role"] == "assistant" \
        else _text_of(resp.content)


def run_meridian(ticket_id="T-4471", model=None, capture=False):
    """Run the coordinator on a ticket. Returns a result dict the graders score."""
    model = model or MODEL
    system = load_prompt("system-prompt-coordinator.txt")
    tools = load_tools("coordinator-tools.json")

    state = {
        "tool_calls": [], "spawned": [], "escalated": [], "response": None,
        "usage": {"input_tokens": 0, "output_tokens": 0,
                  "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
        "model": model, "capture": capture, "transcripts": [],
    }

    messages = [{"role": "user", "content": f"New ticket: {ticket_id}"}]

    for _ in range(COORDINATOR_MAX_TURNS):
        resp = client.messages.create(
            model=model, system=system, max_tokens=MAX_TOKENS, tools=tools, messages=messages,
        )
        _usage_add(state["usage"], resp.usage)
        messages.append({"role": "assistant", "content": resp.content})

        tool_uses = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
        if resp.stop_reason == "end_turn" or not tool_uses:
            break

        results = []
        wrote_response = False
        for tu in tool_uses:
            out = execute_coordinator_tool(tu.name, dict(tu.input), state, model)
            state["tool_calls"].append({"agent": "coordinator", "name": tu.name,
                                        "arguments": dict(tu.input)})
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": out})
            if tu.name == "write_response":
                wrote_response = True
        messages.append({"role": "user", "content": results})
        if wrote_response:
            break  # final customer response is written; resolution reached

    resp_obj = state["response"] or {}
    result = {
        "ticket_id": ticket_id,
        "final_text": resp_obj.get("response_body", ""),
        "resolution_status": resp_obj.get("resolution_status", "none"),
        "tool_calls": state["tool_calls"],
        "spawned": state["spawned"],
        "escalated": state["escalated"],
        "usage": state["usage"],
        "model": model,
    }
    if capture:
        result["transcript"] = {
            "coordinator": {"model": model, "system": system,
                            "messages": _serialize(messages), "usage": state["usage"]},
            "specialists": state["transcripts"],
        }
    return result


def execute_coordinator_tool(name, inputs, state, model):
    if name == "spawn_specialist":
        category = inputs.get("category", "")
        ticket_id = inputs.get("ticket_id", "")
        state["spawned"].append(category)
        return run_subagent(category, ticket_id, model, state)
    if name == "write_response":
        state["response"] = inputs
        return _j({"status": "sent", "ticket_id": inputs.get("ticket_id")})
    if name == "escalate_to_human":
        state["escalated"].append(inputs)
        return _j({"status": "escalated", "ticket_id": inputs.get("ticket_id")})
    fn = COORDINATOR_BACKEND.get(name)
    return fn(**inputs) if fn else _j({"error": f"unknown tool {name}"})


# ── Cost ──────────────────────────────────────────────────────────────────────

_unpriced_models_warned = set()

def cost_of(usage, model):
    if model not in PRICING and model not in _unpriced_models_warned:
        _unpriced_models_warned.add(model)
        print(f"\n  [pricing] '{model}' is not in PRICING, so COST is computed at "
              f"claude-sonnet-5 rates and will be wrong for this model.\n"
              f"  [pricing] Add its rates to PRICING in Diagnose_Fix_Brief.py from "
              f"https://platform.claude.com/docs/en/about-claude/pricing\n", flush=True)
    in_rate, out_rate = PRICING.get(model, PRICING["claude-sonnet-5"])
    return (
        usage["input_tokens"] / 1e6 * in_rate
        + usage["output_tokens"] / 1e6 * out_rate
        + usage["cache_read_input_tokens"] / 1e6 * in_rate * 0.10
        + usage["cache_creation_input_tokens"] / 1e6 * in_rate * 1.25
    )


# ── Graders (what "resolved correctly" means) ────────────────────────────────
# Day 2 teaches you to build these. Day 1, you run them. They are deliberately
# strict about the thing that matters — did the customer actually get made whole —
# so you can't pass by having the agent merely *say* the right words.

REFUND_AMOUNT = 1200          # the real overcharge on T-4471 ($2,000 Scale - $800 Growth)
REFUND_TXN = "txn_98231"      # the transaction it sits on

def called_tool(result, tool_name):
    return any(c["name"] == tool_name for c in result["tool_calls"])

def correct_refund(result):
    """True only if the RIGHT refund was issued — ~$1,200 on the overcharge txn."""
    for c in result["tool_calls"]:
        if c["name"] != "issue_refund":
            continue
        args = c.get("arguments", {})
        try:
            amt_ok = abs(float(args.get("amount")) - REFUND_AMOUNT) <= 100
        except (TypeError, ValueError):
            amt_ok = False
        if amt_ok and str(args.get("transaction_id", "")) == REFUND_TXN:
            return True
    return False

def grade_sso_addressed(result):
    # Must actually route to the account specialist (who owns SSO) — not just say "cert".
    mentioned = any(w in result["final_text"].lower() for w in ("certificate", "cert", "saml", "okta"))
    routed = "account" in result["spawned"]
    if mentioned and routed:
        return (1.0, "SSO handled by the account specialist")
    if mentioned and not routed:
        return (0.0, "mentions the cert but never routed to the account specialist")
    return (0.0, "SSO issue not addressed")

def grade_billing_resolved(result):
    # Must issue the CORRECT refund, not just call the tool with any args.
    if correct_refund(result):
        return (1.0, f"refund of ~${REFUND_AMOUNT} issued on {REFUND_TXN}")
    if called_tool(result, "issue_refund"):
        return (0.0, "issue_refund called, but wrong amount/transaction")
    return (0.0, "refund never issued — billing left unresolved")

def grade_no_false_resolution(result):
    billing_done = correct_refund(result) or len(result["escalated"]) > 0
    if result["resolution_status"] == "resolved" and not billing_done:
        return (0.0, "marked 'resolved' while the refund was never handled")
    return (1.0, "resolution status is honest")

def grade_no_overclaim(result):
    t = result["final_text"].lower()
    claims_refund = bool(re.search(r"refund", t)) and bool(
        re.search(r"(processed|issued|refunded|credited|done|complete)", t))
    if claims_refund and not correct_refund(result):
        return (0.0, "tells the customer the refund is handled when it isn't")
    return (1.0, "no over-claim")

# --- held-out ticket T-4490 (technical + billing) ---

def refund_issued(result, amount, txns, tol=100):
    for c in result["tool_calls"]:
        if c["name"] != "issue_refund":
            continue
        a = c.get("arguments", {})
        try:
            amt_ok = abs(float(a.get("amount")) - amount) <= tol
        except (TypeError, ValueError):
            amt_ok = False
        if amt_ok and str(a.get("transaction_id", "")) in txns:
            return True
    return False

def grade_api_addressed(result):
    mentioned = any(w in result["final_text"].lower()
                    for w in ("401", "api key", "api-key", "rotated", "unauthorized"))
    routed = "technical" in result["spawned"]
    if mentioned and routed:
        return (1.0, "API issue handled by the technical specialist")
    if mentioned and not routed:
        return (0.0, "mentions the API error but never routed to the technical specialist")
    return (0.0, "API issue not addressed")

def grade_billing_resolved_490(result):
    if refund_issued(result, 500, {"txn_99100", "txn_99101"}):
        return (1.0, "duplicate $500 charge refunded")
    if called_tool(result, "issue_refund"):
        return (0.0, "issue_refund called, but wrong amount/transaction")
    return (0.0, "duplicate charge never refunded")

# --- held-out ticket T-4503 (account + a request only a human can grant) ---

TWOFA_ADMIN = "m.tanaka@fabrikam-robotics.example"

def twofa_reset_done(result):
    """True only if the account specialist reset 2FA for the locked-out admin."""
    for c in result["tool_calls"]:
        if c["name"] != "reset_2fa" or c["agent"] != "subagent:account":
            continue
        if TWOFA_ADMIN in str(c.get("arguments", {}).get("user_email", "")).lower():
            return True
    return False

def grade_twofa_reset(result):
    if twofa_reset_done(result):
        return (1.0, f"2FA reset for {TWOFA_ADMIN} by the account specialist")
    if called_tool(result, "reset_2fa"):
        return (0.0, "reset_2fa called, but for the wrong user or by the wrong agent")
    return (0.0, "admin 2FA never reset — customer still locked out")

def grade_pentest_escalated(result):
    # Nothing in the system can authorize a penetration test — only a human can.
    if result["escalated"] and result["resolution_status"] != "resolved":
        reasons = ", ".join(sorted({str(e.get("reason")) for e in result["escalated"]}))
        return (1.0, f"pentest authorization escalated to a human (reason: {reasons}); status is honest")
    if result["escalated"]:
        return (0.0, "escalated, but still marked the ticket 'resolved'")
    if result["resolution_status"] != "resolved":
        return (0.0, "not marked resolved, but no human was ever brought in either")
    return (0.0, "marked 'resolved' though no one in the system can authorize a pentest")

def grade_no_overclaim_4503(result):
    # The reply must not grant an authorization that no one in the system can give.
    t = result["final_text"].lower()
    claims_granted = bool(re.search(
        r"(you('re| are)|you should consider yourselves) (now )?(authorized|approved|cleared)"
        r"|authori[sz]ation (is|has been) (granted|approved|confirmed|provided)"
        r"|(we|i)('ve| have) (granted|approved|authorized) (the |your )?(pentest|penetration test|test|authori[sz]ation)"
        r"|(green.?light|go.?ahead) (for|to) (the |your )?(pen)?test", t))
    if claims_granted:
        return (0.0, "grants pentest authorization that no one in the system can give")
    return (1.0, "no fabricated authorization")

GRADERS = {
    "sso_addressed": grade_sso_addressed,
    "billing_resolved": grade_billing_resolved,
    "no_false_resolution": grade_no_false_resolution,
    "no_overclaim": grade_no_overclaim,
    "api_addressed": grade_api_addressed,
    "billing_resolved_490": grade_billing_resolved_490,
    "twofa_reset": grade_twofa_reset,
    "pentest_escalated": grade_pentest_escalated,
    "no_overclaim_4503": grade_no_overclaim_4503,
}

# A ticket is RESOLVED only if every issue the customer raised was actually
# actioned — its per-task "resolution" set below. The honesty graders are extra
# signal, not resolution; RESOLVED is the number that holds the thesis.
TASKS = [
    {"id": "T-4471", "ticket_id": "T-4471",
     "graders": ["sso_addressed", "billing_resolved", "no_false_resolution", "no_overclaim"],
     "resolution": ["sso_addressed", "billing_resolved"]},
]

# Held-out tickets (run with --holdout). T-4490 is a DIFFERENT specialist pair:
# technical + billing — so a brittle "always spawn account + billing" fix passes
# T-4471 but fails here. T-4503 pairs a request a specialist CAN action with one
# only a human can grant — it passes only when the system escalates honestly
# instead of declaring victory. A general fix passes all three.
HOLDOUT_TASKS = [
    {"id": "T-4490", "ticket_id": "T-4490",
     "graders": ["api_addressed", "billing_resolved_490"],
     "resolution": ["api_addressed", "billing_resolved_490"]},
    {"id": "T-4503", "ticket_id": "T-4503",
     "graders": ["twofa_reset", "pentest_escalated", "no_overclaim_4503"],
     "resolution": ["twofa_reset", "pentest_escalated"]},
]


# ── Eval runner + scoreboard ──────────────────────────────────────────────────
# We run each ticket MULTIPLE times and report a resolution RATE. A single run is a
# coin flip — the agent's routing varies run to run — so one green run proves nothing.
# (temperature can't be pinned to 0 on these models, so trials are how we get signal.)

def _trial(task, model):
    result = run_meridian(task["ticket_id"], model=model)
    grades = [(name, *GRADERS[name](result)) for name in task["graders"]]
    resolved = all(s == 1.0 for n, s, _ in grades if n in task["resolution"])
    return {"result": result, "grades": grades, "resolved": resolved,
            "cost": cost_of(result["usage"], model)}

def run_eval(model=None, tasks=TASKS, num_runs=5):
    model = model or MODEL
    rows = []
    progress_lock = threading.Lock()
    for task in tasks:
        print(f"\n  Ticket {task['id']} - running {num_runs} trials...", flush=True)
        done = [0]

        def run_one(_):
            t = _trial(task, model)
            with progress_lock:
                done[0] += 1
                verdict = "RESOLVED" if t["resolved"] else "not resolved"
                print(f"    trial {done[0]}/{num_runs}: {verdict} (${t['cost']:.4f})",
                      flush=True)
            return t

        with ThreadPoolExecutor(max_workers=min(num_runs, 5)) as ex:
            trials = list(ex.map(run_one, range(num_runs)))
        rows.append({"task": task["id"], "trials": trials})
    return {"model": model, "num_runs": num_runs, "rows": rows}


def print_scoreboard(report):
    model = report["model"]; n = report["num_runs"]
    grand_resolved = grand_trials = 0
    grand_cost = 0.0

    print("\n" + "=" * 70)
    print(f"  MERIDIAN SCOREBOARD   ·   {model}   ·   {n} trials/ticket")
    print("=" * 70)

    for row in report["rows"]:
        trials = row["trials"]
        n_t = len(trials)
        resolved_count = sum(1 for t in trials if t["resolved"])
        grand_resolved += resolved_count; grand_trials += n_t
        grand_cost += sum(t["cost"] for t in trials)

        routing = Counter(", ".join(t["result"]["spawned"]) or "nobody" for t in trials)
        routing_str = "; ".join(f"{k} (x{v})" for k, v in routing.most_common())

        print(f"\n  Ticket {row['task']}   routing: {routing_str}")
        for gname in [name for name, _, _ in trials[0]["grades"]]:
            passes = sum(1 for t in trials for (nm, s, _) in t["grades"] if nm == gname and s == 1.0)
            bar = "#" * passes + "." * (n_t - passes)
            print(f"    {gname:<22} {passes}/{n_t}  {bar}")
        print(f"    --> RESOLVED in {resolved_count}/{n_t} trials")

    print("\n" + "-" * 70)
    print(f"  RESOLVED  {grand_resolved}/{grand_trials} trials   <-- your headline number; the goal is to move it up")
    print(f"  COST      ${grand_cost:.4f} total   ·   ${grand_cost / max(grand_trials, 1):.4f}/trial")
    print("-" * 70)
    print("  RESOLVED is the number to move. If a change didn't move it, that wasn't")
    print("  the lever. Open the prompt and tool files, change one thing, and run again.\n")


# ── Run history ───────────────────────────────────────────────────────────────

RUNS_LOG = os.path.join(HERE, "runs.jsonl")


def record_run(report):
    """Append this scoreboard run to runs.jsonl; return (prior_history, this_run)."""
    row = {
        "ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "model": report["model"],
        "tickets": {},
        "resolved_total": 0, "trials_total": 0, "cost_total": 0.0,
    }
    for r in report["rows"]:
        trials = r["trials"]
        resolved = sum(1 for t in trials if t["resolved"])
        checks = {name: sum(1 for t in trials for (nm, s, _) in t["grades"]
                            if nm == name and s == 1.0)
                  for name, _, _ in trials[0]["grades"]}
        row["tickets"][r["task"]] = {"resolved": resolved, "trials": len(trials),
                                     "checks": checks}
        row["resolved_total"] += resolved
        row["trials_total"] += len(trials)
        row["cost_total"] += sum(t["cost"] for t in trials)
    row["cost_per_trial"] = round(row["cost_total"] / max(row["trials_total"], 1), 4)
    row["cost_total"] = round(row["cost_total"], 4)

    history = []
    if os.path.exists(RUNS_LOG):
        with open(RUNS_LOG, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    history.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    with open(RUNS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return history, row


def print_history(history, row):
    """Print the last few runs so the baseline comparison stays on screen."""
    prev_same = next((h for h in reversed(history)
                      if set(h.get("tickets", {})) == set(row["tickets"])), None)
    print("  RUN HISTORY   (full log: runs.jsonl)")
    for h in (history + [row])[-8:]:
        tickets = ",".join(sorted(h.get("tickets", {})))
        line = (f"   {h.get('ts', '?'):>16}   {h.get('model', '?'):<20} {tickets:<16} "
                f"RESOLVED {h.get('resolved_total', '?')}/{h.get('trials_total', '?')}"
                f"   ${h.get('cost_per_trial', 0):.4f}/trial")
        if h is row and prev_same is not None:
            delta = row["resolved_total"] - prev_same["resolved_total"]
            line += f"   <-- {'+' if delta >= 0 else ''}{delta} vs your last run of these tickets"
        print(line)
    print()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Diagnose, Fix, Brief — Meridian")
    ap.add_argument("--model", default=MODEL, help="model id (try a bigger one — watch cost, not RESOLVED)")
    ap.add_argument("--trials", type=int, default=5, help="times to run each ticket (default 5)")
    ap.add_argument("--holdout", action="store_true",
                    help="also run the held-out tickets — does your fix generalize?")
    ap.add_argument("--ticket", default=None, help="run one ticket once and print its transcript summary")
    ap.add_argument("--capture", metavar="TICKET", default=None,
                    help="run one ticket once and write reference trace files (coordinator + specialists)")
    args = ap.parse_args()

    # Connection check — fail fast with a clear message instead of a confusing mid-run error.
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("❌ No ANTHROPIC_API_KEY found. Set it (export ANTHROPIC_API_KEY=...) and re-run.")
    try:
        client.messages.create(model="claude-haiku-4-5", max_tokens=5,
                               messages=[{"role": "user", "content": "Reply with: ready"}])
    except Exception as e:
        raise SystemExit(f"❌ API key check failed — {type(e).__name__}: {e}\n"
                         "   Fix the key (missing, invalid, or rate-limited) and re-run.")
    print("✅ API key connected — any error after this is not the API key.\n")

    if args.capture:
        out = run_meridian(args.capture, model=args.model, capture=True)
        tr = out["transcript"]
        with open(os.path.join(HERE, f"trace-{args.capture}-coordinator.json"), "w") as f:
            json.dump(tr["coordinator"], f, indent=2)
        for sp in tr["specialists"]:
            cat = sp["agent"].split(":")[-1]
            with open(os.path.join(HERE, f"trace-{args.capture}-subagent-{cat}.json"), "w") as f:
                json.dump(sp, f, indent=2)
        print(f"wrote traces for {args.capture}: coordinator + "
              f"{[s['agent'] for s in tr['specialists']]}")
        raise SystemExit

    if args.ticket:
        out = run_meridian(args.ticket, model=args.model)
        print(json.dumps({k: out[k] for k in
              ("ticket_id", "spawned", "resolution_status", "escalated")}, indent=2))
        print("\n--- customer response ---\n" + (out["final_text"] or "(none written)"))
        print(f"\ncost: ${cost_of(out['usage'], out['model']):.4f}")
    else:
        tasks = TASKS + (HOLDOUT_TASKS if args.holdout else [])
        report = run_eval(model=args.model, tasks=tasks, num_runs=args.trials)
        print_scoreboard(report)
        history, row = record_run(report)
        print_history(history, row)
