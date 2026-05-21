import sys
import anthropic
import json
import os

sys.stdout.reconfigure(encoding='utf-8')

# Set ANTHROPIC_API_KEY in your environment before running this script
client = anthropic.Anthropic(timeout=900.0)
MODEL = "claude-sonnet-4-6"

# ── Mock data ──
TICKETS = {
    "TKT-1042": {"id": "TKT-1042", "customer": "Acme Corp", "priority": "high", "product_area": "billing", "description": "We were charged twice for our March invoice. Invoice #INV-2024-0342 shows $4,500 but our bank shows two identical charges on March 3rd. Need immediate refund of the duplicate charge.", "status": "open"},
    "TKT-1043": {"id": "TKT-1043", "customer": "DataFlow Inc", "priority": "medium", "product_area": "api", "description": "Our webhook endpoint stopped receiving events after we rotated API keys yesterday. We've verified the new key works for REST calls but webhooks are still failing. Getting 401 errors in the webhook logs.", "status": "open"},
    "TKT-1044": {"id": "TKT-1044", "customer": "CloudScale Ltd", "priority": "low", "product_area": "feature_request", "description": "Would love to see bulk export functionality in the dashboard. Currently we have to export reports one at a time which is painful when we need quarterly summaries across 50+ projects.", "status": "open"},
    "TKT-1045": {"id": "TKT-1045", "customer": "SecureNet Systems", "priority": "critical", "product_area": "account", "description": "Our admin account (admin@securenet.io) is locked out after failed MFA attempts. We have 47 team members who can't access the platform because SSO is tied to this admin account. This is blocking all work.", "status": "open"},
    "TKT-1046": {"id": "TKT-1046", "customer": "MedTech Solutions", "priority": "high", "product_area": "api", "description": "Our production integration started returning intermittent 500 errors around 2am last night. About 15% of API calls are failing. We haven't changed anything on our end. Errors seem random - sometimes the same request works on retry. Our team in Singapore is blocked and we need this resolved ASAP.", "status": "open"},
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
    return json.dumps(ticket) if ticket else json.dumps({"error": f"Ticket {ticket_id} not found"})

def search_kb(query: str) -> str:
    query_lower = query.lower()
    results = []
    for article_id, article in KB_ARTICLES.items():
        if any(word in article["title"].lower() or word in article["content"].lower()
               for word in query_lower.split() if len(word) > 2):
            results.append({"id": article_id, **article})
    if not results:
        results = [{"id": "KB-000", "title": "No matches found", "content": "No relevant articles found."}]
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
    return func(**input_data) if func else json.dumps({"error": f"Unknown tool: {name}"})

# ── Tool schemas ──
tools = [
    {
        "name": "get_ticket",
        "description": "Retrieve full details for a support ticket by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {"ticket_id": {"type": "string", "description": "The ticket ID, e.g. TKT-1045"}},
            "required": ["ticket_id"]
        }
    },
    {
        "name": "search_kb",
        "description": "Search the knowledge base for articles related to a support issue. Always search before resolving.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Keywords describing the issue"}},
            "required": ["query"]
        }
    },
    {
        "name": "resolve_ticket",
        "description": "Mark a support ticket as resolved, escalated, or pending with a detailed resolution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "resolution": {"type": "string"},
                "status": {"type": "string", "enum": ["resolved", "escalated", "pending"]}
            },
            "required": ["ticket_id", "resolution", "status"]
        }
    }
]

SYSTEM_PROMPT = """You are a Tier 1 support agent for TechFlow. Handle incoming tickets by: 1) looking up the ticket, 2) searching the KB, 3) resolving with specific steps. Escalate security issues and anything requiring privileged access."""

RESOLUTION_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "diagnosis": {"type": "string"},
            "solution_steps": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "escalation_needed": {"type": "boolean"},
            "category": {"type": "string", "enum": ["billing", "technical", "account", "feature_request"]}
        },
        "required": ["diagnosis", "solution_steps", "confidence", "escalation_needed", "category"],
        "additionalProperties": False
    }
}

def get_structured_result(response) -> dict:
    text_blocks = [b for b in response.content if b.type == "text" and b.text.strip()]
    if text_blocks:
        return json.loads(text_blocks[-1].text)
    return None

def run_agent_streaming(user_message: str, effort: str = "high") -> dict:
    messages = [{"role": "user", "content": user_message}]
    response = None

    while True:
        current_block_type = None

        with client.messages.stream(
            model=MODEL,
            max_tokens=32000,
            system=SYSTEM_PROMPT,
            tools=tools,
            thinking={"type": "adaptive"},
            output_config={"effort": effort},
            messages=messages
        ) as stream:
            for event in stream:
                if event.type == "content_block_start":
                    block = event.content_block
                    current_block_type = block.type
                    if block.type == "thinking":
                        print("\n[Thinking] ", end="", flush=True)
                    elif block.type == "tool_use":
                        print(f"\n[Tool call] {block.name}(", end="", flush=True)
                    elif block.type == "text":
                        print("\n[Response] ", end="", flush=True)

                elif event.type == "content_block_delta":
                    delta = event.delta
                    if delta.type == "thinking_delta":
                        print(delta.thinking, end="", flush=True)
                    elif delta.type == "text_delta":
                        print(delta.text, end="", flush=True)
                    elif delta.type == "input_json_delta":
                        print(delta.partial_json, end="", flush=True)

                elif event.type == "content_block_stop":
                    if current_block_type == "tool_use":
                        print(")", flush=True)

            response = stream.get_final_message()

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                print(f"\n[Tool result] {result}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
                })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    # Final structured output call
    messages.append({"role": "assistant", "content": response.content})
    messages.append({"role": "user", "content": "Provide your structured resolution as JSON."})
    print("\n\n[Structured resolution] ", end="", flush=True)

    with client.messages.stream(
        model=MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        output_config={"effort": effort, "format": RESOLUTION_SCHEMA},
        tool_choice={"type": "none"},
        thinking={"type": "adaptive"},
        messages=messages
    ) as stream:
        for event in stream:
            if event.type == "content_block_delta" and event.delta.type == "text_delta":
                print(event.delta.text, end="", flush=True)
        final_response = stream.get_final_message()

    print()
    return get_structured_result(final_response)


if __name__ == "__main__":
    import time
    all_results = []
    for ticket_id, ticket in TICKETS.items():
        print(f"\n{'=' * 60}")
        print(f"Ticket: {ticket_id} | {ticket['customer']} | {ticket['priority'].upper()}")
        print(f"{'=' * 60}")
        start = time.time()
        result = run_agent_streaming(f"Resolve ticket {ticket_id}")
        elapsed = time.time() - start
        all_results.append({"ticket_id": ticket_id, "elapsed": elapsed, "result": result})
        print(f"\n[{ticket_id}] Done in {elapsed:.1f}s — category={result['category']}, escalation={result['escalation_needed']}, confidence={result['confidence']}")

    print(f"\n\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    for r in all_results:
        res = r["result"]
        print(f"  {r['ticket_id']}  {res['category']:<16} escalate={str(res['escalation_needed']):<6} confidence={res['confidence']:<6} time={r['elapsed']:.1f}s")
