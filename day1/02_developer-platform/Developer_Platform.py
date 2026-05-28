# ── Install & Import ──
%pip install -q anthropic

import anthropic
import json
import time
import os
from IPython.display import display, Markdown

# ── API Key Configuration ──
# Option 1: Colab Secrets (recommended — click the 🔑 icon in the left sidebar)
try:
    from google.colab import userdata
    os.environ["ANTHROPIC_API_KEY"] = userdata.get("ANTHROPIC_API_KEY")
    print("✅ API key loaded from Colab Secrets")
except Exception:
    pass

# Option 2: Paste directly (uncomment and replace)
# os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."

client = anthropic.Anthropic(timeout=900.0)  # Longer timeout: needed for max_tokens>21333 with non-streaming calls
MODEL = "claude-sonnet-4-6"

# ── Pre-flight Check ──
errors = []
if not os.environ.get("ANTHROPIC_API_KEY"):
    errors.append("❌ ANTHROPIC_API_KEY not set. Use Colab Secrets (🔑 sidebar) or paste it above.")

sdk_version = anthropic.__version__
print(f"SDK version: {sdk_version}")

if not errors:
    try:
        test = client.messages.create(
            model=MODEL, max_tokens=1024,
            messages=[{"role": "user", "content": "Reply with only: ready"}],
            thinking={"type": "adaptive"},
        )
        text = "".join(b.text for b in test.content if b.type == "text").strip()
        print(f"✅ Model: {MODEL}")
        print(f"✅ API connected — test response: {text}")
    except anthropic.AuthenticationError:
        errors.append("❌ API key is invalid. Check your key and try again.")
    except anthropic.BadRequestError as e:
        errors.append(f"❌ API error: {e}. Your SDK may need updating: %pip install -q --upgrade anthropic")
    except Exception as e:
        errors.append(f"❌ Connection error: {e}")

if errors:
    print("\n⚠️  Setup issues detected:")
    for err in errors:
        print(f"   {err}")
    print("\nFix the issues above and re-run this cell.")
else:
    print("\n🚀 Ready to build!")

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
    # Your tool schemas here
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
    pass  # Your implementation here


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
    pass  # Your implementation here


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
    pass  # Your implementation here

# Run the ambiguous ticket at high effort — observe the thinking traces
print("=== TKT-1046: Intermittent API Errors (ambiguous) ===\n")
result = run_agent_thinking("Resolve ticket TKT-1046", effort="high")
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
    pass  # Your implementation here

print("Full Agent Demo: Resolving TKT-1045 (account lockout)")
print("   Streaming + Adaptive Thinking + Tools + Structured Output")
print("=" * 60)

start = time.time()
result = run_agent_streaming("Resolve ticket TKT-1045")
elapsed = time.time() - start

print(f"\n\n{'=' * 60}")
print(f"Total time: {elapsed:.1f}s")
print(f"\nStructured Resolution:")
print(json.dumps(result, indent=2))
