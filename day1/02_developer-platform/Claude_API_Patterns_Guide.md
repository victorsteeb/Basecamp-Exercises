# Building Production AI Agents with Claude API
## A Comprehensive Guide to Agentic Patterns

**Author:** Based on Anthropic Basecamp Developer Platform Workshop  
**Last Updated:** November 2026  
**Difficulty:** Intermediate (300-level)

---

## 📋 Table of Contents

1. [Overview: Why These Patterns Matter](#overview)
2. [Pattern 1: Multi-Tool Agentic Loop](#pattern-1-agentic-loop)
3. [Pattern 2: Structured Outputs (JSON Mode)](#pattern-2-structured-outputs)
4. [Pattern 3: Adaptive Thinking](#pattern-3-adaptive-thinking)
5. [Pattern 4: Real-Time Streaming](#pattern-4-streaming)
6. [Complete Implementation](#complete-implementation)
7. [Production Considerations](#production-considerations)
8. [Use Cases & Applications](#use-cases)
9. [Troubleshooting Guide](#troubleshooting)
10. [Further Resources](#resources)

---

## 🎯 Overview: Why These Patterns Matter {#overview}

### The Problem with Single-Shot LLM Calls

Most developers start with Claude like this:

```python
response = client.messages.create(
    model="claude-sonnet-5",
    messages=[{"role": "user", "content": "Solve this problem"}]
)
```

**This works for simple tasks, but fails at:**
- Complex multi-step workflows (need to gather data, reason, act)
- Integration with external systems (databases, APIs, knowledge bases)
- Production requirements (structured output, auditability, real-time feedback)

### The Solution: Four Composable Patterns

These patterns transform Claude from a "smart text generator" into a **production-ready autonomous agent**:

| Pattern | What It Does | When You Need It |
|---------|-------------|------------------|
| **Agentic Loop** | Lets Claude call tools repeatedly until task complete | Multi-step workflows, API integrations, data gathering |
| **Structured Outputs** | Guarantees JSON responses matching your schema | Database writes, downstream systems, API responses |
| **Adaptive Thinking** | Shows reasoning traces, controls depth | Debugging decisions, auditing, complex reasoning |
| **Streaming** | Real-time token delivery | UX, dashboards, long-running tasks |

**The power:** These patterns **compose**. You can use them together in one agent to get autonomous execution + structured output + visible reasoning + real-time feedback.

---

## 🔄 Pattern 1: Multi-Tool Agentic Loop {#pattern-1-agentic-loop}

### The Core Concept

An **agentic loop** is a pattern where Claude:
1. Decides which tool to call based on current context
2. Receives tool results
3. Decides the next action (call another tool or finish)
4. Repeats until task is complete

**Key insight:** You don't hard-code the workflow. Claude orchestrates the sequence dynamically.

### The Pattern

```python
def agentic_loop(user_message: str):
    messages = [{"role": "user", "content": user_message}]
    
    # Initial API call
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=4096,
        tools=tools,  # Tool definitions
        messages=messages
    )
    
    # Loop while Claude wants to use tools
    while response.stop_reason == "tool_use":
        # Extract and execute tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
                })
        
        # Append assistant message + tool results
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
        
        # Continue the loop
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )
    
    return response
```

### Tool Schema Design

Tools are JSON schemas that tell Claude **what's available** and **how to call it**:

```python
tools = [
    {
        "name": "search_database",
        "description": "Search customer records by email, ID, or name. Returns full customer profile including tier, history, and preferences.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Email, customer ID, or full name"},
                "include_history": {"type": "boolean", "description": "Include purchase history"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "send_email",
        "description": "Send an email to a customer. Use for notifications, confirmations, or follow-ups.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string"},
                "body": {"type": "string", "description": "Email content in plain text"}
            },
            "required": ["to", "subject", "body"]
        }
    }
]
```

**Critical:** The `description` field is how Claude decides **which tool to use**. Vague descriptions = wrong tool selection.

### When to Use This Pattern

✅ **Perfect for:**
- Customer support automation (lookup → search KB → resolve)
- Data analysis workflows (fetch → transform → analyze → visualize)
- Research agents (search → summarize → cross-reference → report)
- Integration orchestration (read API → process → write to database)

❌ **Not ideal for:**
- Simple Q&A (no tools needed)
- Tasks requiring human judgment at each step
- Real-time latency-critical applications (<500ms response)

### Real-World Example: E-commerce Order Agent

```python
# Claude autonomously:
# 1. Searches order by ID
# 2. Checks inventory for replacement
# 3. Creates refund
# 4. Sends confirmation email
# All without human intervention

response = agentic_loop("Customer order #12345 was damaged. Process replacement.")

# Claude decides the sequence:
# → get_order("12345")
# → check_inventory(product_id="ABC")
# → create_refund(amount=49.99)
# → send_email(to="customer@example.com", subject="Refund processed")
```

---

## 📊 Pattern 2: Structured Outputs (JSON Mode) {#pattern-2-structured-outputs}

### The Problem: Free Text Breaks Integrations

Your agent produces great answers, but downstream systems need **structured data**:

```
❌ Free text: "The customer should receive a refund in 3-5 days..."
✅ Structured: {"action": "refund", "amount": 49.99, "timeline_days": 5}
```

Without structure, you resort to:
- Fragile regex parsing (12% failure rate in production)
- Secondary LLM extraction (costs 2x, still unreliable)
- Manual human review (defeats automation purpose)

### The Solution: JSON Schema Constraints

Claude's `output_config.format` **guarantees** valid JSON matching your schema:

```python
RESPONSE_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["refund", "replace", "escalate"]},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "reasoning": {"type": "string"},
            "next_steps": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["action", "confidence", "reasoning", "next_steps"],
        "additionalProperties": False
    }
}

response = client.messages.create(
    model="claude-sonnet-5",
    output_config={"format": RESPONSE_SCHEMA},
    messages=[...]
)

# Response is GUARANTEED to be valid JSON matching schema
result = json.loads(response.content[0].text)
print(result['action'])  # Always present, always one of the enum values
```

### Critical Constraint: Two-Phase Pattern

**You cannot use `output_config.format` during tool use.** The format constraint applies to ALL text output, so tools stop working.

**Solution: Two phases**

```python
# Phase 1: Tool loop (NO format constraint)
while response.stop_reason == "tool_use":
    # Execute tools, gather data
    ...

# Phase 2: Structured output (WITH format constraint)
messages.append({"role": "user", "content": "Provide your final answer as JSON."})
final = client.messages.create(
    model="claude-sonnet-5",
    output_config={"format": RESPONSE_SCHEMA},
    tool_choice={"type": "none"},  # Disable tools
    messages=messages
)
```

### Schema Design Best Practices

#### 1. Use Enums for Categories

```python
"status": {"type": "string", "enum": ["open", "closed", "pending"]}
```

✅ No typos, no variations ("Open", "OPEN", "opened")  
✅ Perfect for database writes, analytics aggregation

#### 2. Arrays for Sequential Data

```python
"steps": {"type": "array", "items": {"type": "string"}}
```

✅ Easy to render in UI as numbered lists  
✅ Analytics: measure complexity by step count

#### 3. Required Fields = No Null Checks

```python
"required": ["action", "confidence", "reasoning"]
```

✅ Claude **must** provide all fields  
✅ Your code never needs `if result.get('action'):`

#### 4. Descriptions Guide Output Quality

```python
"reasoning": {"type": "string", "description": "Explain why this action was chosen and what evidence supports it"}
```

✅ More detailed, accurate responses  
✅ Claude understands field intent

### When to Use This Pattern

✅ **Perfect for:**
- Database writes (structured records)
- API responses (JSON endpoints)
- Workflow automation (next-step routing)
- Analytics pipelines (structured event logging)
- Multi-system integration (consistent format)

❌ **Not ideal for:**
- Chat interfaces (users prefer natural text)
- Exploratory analysis (structure limits flexibility)
- Creative content generation (poems, stories)

### Real-World Impact

| System | Without Structure | With Structure |
|--------|------------------|----------------|
| **Database** | Regex parsing → 12% failures | Direct field access → 0% failures |
| **Analytics** | Manual categorization | Automated aggregation by enum values |
| **API** | Inconsistent response format | OpenAPI-compliant JSON always |
| **Testing** | Can't assert on format | Schema validation in CI/CD |

---

## 🧠 Pattern 3: Adaptive Thinking {#pattern-3-adaptive-thinking}

### The Concept: Visible, Controllable Reasoning

Claude Sonnet 5 can **show its reasoning** in dedicated `thinking` blocks:

```python
response = client.messages.create(
    model="claude-sonnet-5",
    thinking={"type": "adaptive"},
    messages=[...]
)

# Response contains:
# [ThinkingBlock("Let me analyze this step by step..."),
#  TextBlock("Based on my analysis, the answer is...")]
```

**Adaptive** = Claude decides reasoning depth based on task complexity automatically.

### Controlling Reasoning Depth

Use `output_config.effort` to control how deeply Claude reasons:

```python
# Simple task: quick reasoning
response = client.messages.create(
    model="claude-sonnet-5",
    thinking={"type": "adaptive"},
    output_config={"effort": "low"},
    messages=[{"role": "user", "content": "What's 2+2?"}]
)

# Complex task: deep reasoning
response = client.messages.create(
    model="claude-sonnet-5",
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},
    messages=[{"role": "user", "content": "Debug this intermittent race condition..."}]
)
```

| Effort Level | Reasoning Depth | Use Case | Typical Latency |
|--------------|----------------|----------|-----------------|
| `low` | Minimal | Simple lookups, known patterns | 1-3 seconds |
| `medium` | Moderate | Standard problem-solving | 3-10 seconds |
| `high` | Deep | Ambiguous, complex, high-stakes | 10-60 seconds |

### Displaying Thinking Traces

```python
for block in response.content:
    if block.type == "thinking":
        print(f"[Reasoning] {block.thinking}")
    elif block.type == "text":
        print(f"[Answer] {block.text}")
```

**Output:**
```
[Reasoning] I need to first verify the customer tier to determine SLA requirements...
[Reasoning] This looks like a duplicate charge scenario based on the timestamps...
[Answer] I recommend issuing a refund through the payment processor...
```

### Why This Matters

#### 1. Debugging Agent Decisions

**Without thinking:**
```
Agent: "Escalate to engineering."
You: "Why?! It's just a password reset!"
```

**With thinking:**
```
[Thinking] The user mentioned SSO is affected, which suggests an IdP configuration 
issue rather than a simple password reset. This requires engineering access to the 
identity provider settings. Escalating.

Agent: "Escalate to engineering."
You: "Ah, makes sense. The SSO detail is key."
```

#### 2. Auditing High-Stakes Decisions

For compliance, legal, or safety-critical applications:

```python
# Log thinking traces for audit trail
if result['action'] == 'deny_claim':
    audit_log.append({
        "decision": "deny",
        "reasoning": thinking_trace,
        "timestamp": datetime.now(),
        "confidence": result['confidence']
    })
```

#### 3. Improving Prompts

Seeing how Claude reasons reveals where your prompt is unclear:

```
[Thinking] The user wants me to "process" the request, but I'm not sure if that 
means approve, deny, or just log it. I'll assume approve...
```

→ **Fix:** Make "process" more specific in your system prompt.

### Combining Thinking with Structured Output

**They work together seamlessly:**

```python
response = client.messages.create(
    model="claude-sonnet-5",
    thinking={"type": "adaptive"},
    output_config={"effort": "high", "format": SCHEMA},
    messages=[...]
)

# Response:
# [ThinkingBlock("Analyzing the customer's tier..."),
#  ThinkingBlock("Checking KB for similar cases..."),
#  TextBlock('{"action": "refund", "confidence": "high", ...}')]
```

**Thinking is unrestricted** (natural reasoning), **text is pure JSON** (structured).

### When to Use This Pattern

✅ **Perfect for:**
- High-stakes decisions (legal, medical, financial)
- Debugging agent behavior
- Compliance/audit requirements
- Complex reasoning tasks (multi-step analysis)
- Building trust in AI decisions

❌ **Not ideal for:**
- Simple lookup tasks (reasoning overhead not needed)
- Latency-critical applications (thinking adds time)
- Public-facing chat (users don't care about reasoning)

---

## 📡 Pattern 4: Real-Time Streaming {#pattern-4-streaming}

### The Problem: Users Hate Spinners

Traditional API call flow:

```
User: "Analyze this data..."
[15 second spinner]
Response: [Wall of text appears instantly]
```

**Issues:**
- No feedback during processing
- User doesn't know if it's working
- Can't cancel if it's going wrong
- Feels slow even if it's fast

### The Solution: Token-by-Token Streaming

```python
with client.messages.stream(
    model="claude-sonnet-5",
    messages=[...]
) as stream:
    for event in stream:
        if event.type == "content_block_delta":
            if hasattr(event.delta, "text"):
                print(event.delta.text, end="", flush=True)
```

**User sees:**
```
User: "Analyze this data..."
Response: "Let me analyze" [appearing] "this step" [appearing] "by step..." [appearing]
```

### Streaming the Agentic Loop

```python
def streaming_agent(user_message: str):
    messages = [{"role": "user", "content": user_message}]
    
    # Stream initial response
    with client.messages.stream(
        model="claude-sonnet-5",
        tools=tools,
        thinking={"type": "adaptive"},
        messages=messages
    ) as stream:
        # Handle events
        for event in stream:
            if event.type == "content_block_start":
                if event.content_block.type == "thinking":
                    print("\n🤔 [Thinking] ", end="", flush=True)
                elif event.content_block.type == "tool_use":
                    print(f"\n🔧 [Using tool: {event.content_block.name}] ", end="", flush=True)
            
            elif event.type == "content_block_delta":
                if hasattr(event.delta, "thinking"):
                    print(event.delta.thinking, end="", flush=True)
                elif hasattr(event.delta, "text"):
                    print(event.delta.text, end="", flush=True)
        
        # Get complete response
        response = stream.get_final_message()
    
    # Continue agentic loop with streaming
    while response.stop_reason == "tool_use":
        # Execute tools
        tool_results = [...]
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
        
        # Stream next iteration
        with client.messages.stream(...) as stream:
            # Same event handling
            ...
            response = stream.get_final_message()
    
    return response
```

### Streaming Event Types

| Event | When It Fires | What to Display |
|-------|--------------|-----------------|
| `content_block_start` | New block begins | Block type indicator (`[Thinking]`, `[Tool]`) |
| `content_block_delta` | Tokens arrive | The actual text/thinking content |
| `content_block_stop` | Block complete | (optional) newline or separator |

### User Experience Transformation

**Before streaming:**
```
[15s spinner] "Here's the complete analysis: [3000 words]"
```

**After streaming:**
```
🤔 [Thinking] First, I'll check the customer database...
🔧 [Using tool: search_customer] 
   → Found: John Doe, Premium tier
🤔 [Thinking] Now searching for similar cases...
🔧 [Using tool: search_kb]
   → Found: KB-042 "Premium Support SLA"
💬 [Response] Based on the customer's Premium tier and our KB...
```

**Benefits:**
- User sees progress in real-time
- Can cancel if it's going wrong
- Feels faster (time flies when you see progress)
- Builds trust (transparency)

### When to Use This Pattern

✅ **Perfect for:**
- User-facing chat interfaces
- Long-running analyses (>5 seconds)
- Multi-step workflows (show each step)
- Dashboards (live agent monitoring)
- Building user trust

❌ **Not ideal for:**
- Batch processing (no user watching)
- API integrations (systems don't care about streaming)
- Very fast responses (<1 second)

---

## 🚀 Complete Implementation {#complete-implementation}

Here's how all four patterns compose into a production agent:

```python
def production_agent(
    user_message: str,
    effort: str = "high",
    stream: bool = True
) -> dict:
    """
    Complete agent with:
    - Agentic tool loop
    - Structured output
    - Adaptive thinking
    - Optional streaming
    """
    messages = [{"role": "user", "content": user_message}]
    
    # ========== PHASE 1: Tool Loop (No format constraint) ==========
    if stream:
        with client.messages.stream(
            model="claude-sonnet-5",
            max_tokens=32000,
            system=SYSTEM_PROMPT,
            tools=tools,
            thinking={"type": "adaptive"},
            output_config={"effort": effort},
            messages=messages
        ) as stream_obj:
            for event in stream_obj:
                # Handle streaming events
                display_stream_event(event)
            response = stream_obj.get_final_message()
    else:
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=32000,
            system=SYSTEM_PROMPT,
            tools=tools,
            thinking={"type": "adaptive"},
            output_config={"effort": effort},
            messages=messages
        )
    
    # Continue tool loop
    while response.stop_reason == "tool_use":
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
                })
        
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
        
        # Stream next iteration
        if stream:
            with client.messages.stream(...) as stream_obj:
                for event in stream_obj:
                    display_stream_event(event)
                response = stream_obj.get_final_message()
        else:
            response = client.messages.create(...)
    
    # ========== PHASE 2: Structured Output ==========
    messages.append({"role": "user", "content": "Provide your final answer as JSON."})
    
    if stream:
        with client.messages.stream(
            model="claude-sonnet-5",
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            output_config={"effort": effort, "format": RESPONSE_SCHEMA},
            tool_choice={"type": "none"},
            thinking={"type": "adaptive"},
            messages=messages
        ) as stream_obj:
            for event in stream_obj:
                if event.type == "content_block_delta" and hasattr(event.delta, "text"):
                    print(event.delta.text, end="", flush=True)
            final = stream_obj.get_final_message()
    else:
        final = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            output_config={"effort": effort, "format": RESPONSE_SCHEMA},
            tool_choice={"type": "none"},
            thinking={"type": "adaptive"},
            messages=messages
        )
    
    # Extract JSON from last text block
    text_blocks = [b for b in final.content if b.type == "text"]
    return json.loads(text_blocks[-1].text)


# Usage
result = production_agent(
    "Customer #12345 says their order was damaged",
    effort="high",
    stream=True
)

print(result['action'])      # "replace"
print(result['confidence'])  # "high"
print(result['next_steps'])  # ["Verify order details", "Check inventory", ...]
```

---

## 🏭 Production Considerations {#production-considerations}

### 1. Error Handling

```python
def safe_tool_execution(tool_name: str, tool_input: dict) -> str:
    """Execute tool with retry and error handling."""
    try:
        return execute_tool(tool_name, tool_input)
    except DatabaseError as e:
        # Log and return error to Claude
        logger.error(f"Database error in {tool_name}: {e}")
        return json.dumps({
            "error": "Database temporarily unavailable. Please retry.",
            "error_type": "transient"
        })
    except ValueError as e:
        # Validation error - Claude needs to know
        return json.dumps({
            "error": f"Invalid input: {str(e)}",
            "error_type": "validation"
        })
```

### 2. Cost Tracking

```python
def track_usage(response):
    """Log token usage for cost analysis."""
    usage = response.usage
    cost = (usage.input_tokens * INPUT_PRICE_PER_1K / 1000 + 
            usage.output_tokens * OUTPUT_PRICE_PER_1K / 1000)
    
    metrics.log({
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cost_usd": cost,
        "model": response.model,
        "timestamp": datetime.now()
    })
```

### 3. Rate Limiting

```python
import time
from functools import wraps

def rate_limit(max_calls_per_minute=50):
    """Simple rate limiter decorator."""
    calls = []
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            # Remove calls older than 1 minute
            calls[:] = [t for t in calls if now - t < 60]
            
            if len(calls) >= max_calls_per_minute:
                sleep_time = 60 - (now - calls[0])
                time.sleep(sleep_time)
            
            calls.append(time.time())
            return func(*args, **kwargs)
        return wrapper
    return decorator

@rate_limit(max_calls_per_minute=50)
def call_claude(messages):
    return client.messages.create(...)
```

### 4. Caching Responses

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_kb_search(query: str) -> str:
    """Cache knowledge base searches."""
    return search_knowledge_base(query)
```

### 5. Timeout Handling

```python
import signal

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Agent execution exceeded time limit")

def run_with_timeout(func, timeout_seconds=60):
    """Run agent with timeout."""
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    try:
        return func()
    finally:
        signal.alarm(0)  # Cancel alarm
```

### 6. Logging & Observability

```python
import structlog

logger = structlog.get_logger()

def log_agent_run(user_message, response, duration):
    """Structured logging for agent runs."""
    logger.info(
        "agent_run_complete",
        message_preview=user_message[:100],
        stop_reason=response.stop_reason,
        tool_calls=[b.name for b in response.content if b.type == "tool_use"],
        duration_seconds=duration,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens
    )
```

---

## 🎪 Use Cases & Applications {#use-cases}

### 1. Customer Support Automation

**Pattern:** Agentic Loop + Structured Output + Streaming

```python
# Agent autonomously:
# 1. Looks up customer
# 2. Searches knowledge base
# 3. Checks order history
# 4. Resolves ticket with structured output

result = support_agent("Customer #12345 wants refund for order #67890")
# → {"action": "refund", "amount": 49.99, "status": "approved"}
```

### 2. Data Analysis Workflows

**Pattern:** Agentic Loop + Adaptive Thinking (high effort)

```python
# Agent:
# 1. Queries database
# 2. Identifies anomalies
# 3. Correlates with external data
# 4. Generates report with visualizations

result = analysis_agent("Analyze sales trends for Q3 2024")
```

### 3. Code Review Assistant

**Pattern:** Structured Output + Adaptive Thinking

```python
# Returns structured findings
result = code_review_agent(pull_request_diff)
# → {
#     "security_issues": [...],
#     "performance_concerns": [...],
#     "suggestions": [...],
#     "overall_assessment": "approve_with_comments"
# }
```

### 4. Research & Synthesis

**Pattern:** Agentic Loop + Streaming + Thinking

```python
# Agent:
# 1. Searches multiple sources
# 2. Streams findings as they're discovered
# 3. Shows reasoning for credibility assessment
# 4. Synthesizes final report

research_agent("What are the latest developments in quantum computing?")
```

### 5. Workflow Automation

**Pattern:** Agentic Loop + Structured Output

```python
# Automates multi-step business processes
result = workflow_agent("Process expense report #123")
# Agent:
# 1. Validates receipts
# 2. Checks against policy
# 3. Routes for approval
# 4. Updates accounting system
```

---

## 🔧 Troubleshooting Guide {#troubleshooting}

### Problem: Agent Gets Stuck in Tool Loop

**Symptom:** `while stop_reason == "tool_use"` never ends

**Causes:**
1. Tool returns error but Claude doesn't realize it
2. Tool output format is ambiguous
3. Missing data Claude needs to proceed

**Solutions:**

```python
# Add loop counter
max_iterations = 10
iteration = 0

while response.stop_reason == "tool_use" and iteration < max_iterations:
    iteration += 1
    # ... tool execution ...
    
if iteration >= max_iterations:
    # Force exit with context
    messages.append({
        "role": "user",
        "content": "You've used all available iterations. Provide your best answer based on what you've learned so far."
    })
```

### Problem: Structured Output Fails Validation

**Symptom:** `JSONDecodeError` or malformed JSON

**Cause:** Schema is too complex or Claude misinterprets requirements

**Solutions:**

```python
# 1. Simplify schema (start minimal)
SIMPLE_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "answer": {"type": "string"}
        },
        "required": ["answer"]
    }
}

# 2. Add schema examples in system prompt
system_prompt += """
Example output:
{
    "action": "refund",
    "confidence": "high",
    "reasoning": "Duplicate charge confirmed"
}
"""

# 3. Validate response
try:
    result = json.loads(response.content[0].text)
    jsonschema.validate(result, SCHEMA)
except json.JSONDecodeError:
    logger.error("Failed to parse JSON response")
    # Retry with more explicit instructions
```

### Problem: Thinking Blocks Too Verbose

**Symptom:** 2000+ tokens of thinking, slowing response

**Solution:**

```python
# Use medium/low effort for simpler tasks
response = client.messages.create(
    thinking={"type": "adaptive"},
    output_config={"effort": "low"},  # Less verbose thinking
    ...
)

# Or summarize thinking
response = client.messages.create(
    thinking={"type": "adaptive", "display": "summarized"},
    ...
)
```

### Problem: Streaming Breaks on Network Issues

**Symptom:** Stream stops mid-response

**Solution:**

```python
def resilient_stream(messages):
    """Stream with automatic retry."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with client.messages.stream(...) as stream:
                for event in stream:
                    yield event
                return
        except ConnectionError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```

### Problem: Tool Results Too Large

**Symptom:** Exceeding context window

**Solution:**

```python
def truncate_tool_result(result: str, max_length: int = 5000) -> str:
    """Truncate large tool results intelligently."""
    if len(result) <= max_length:
        return result
    
    # Try to truncate at paragraph boundary
    truncated = result[:max_length]
    last_newline = truncated.rfind('\n')
    if last_newline > max_length * 0.8:
        truncated = truncated[:last_newline]
    
    return truncated + "\n\n[... truncated ...]"
```

---

## 📚 Further Resources {#resources}

### Official Documentation
- [Claude API Docs](https://docs.anthropic.com/en/docs)
- [Tool Use Guide](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [Structured Outputs](https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs)
- [Adaptive Thinking](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking)
- [Streaming](https://docs.anthropic.com/en/docs/build-with-claude/streaming)

### Best Practices
- [Prompt Engineering Guide](https://docs.anthropic.com/en/docs/prompt-engineering)
- [System Prompt Library](https://docs.anthropic.com/en/docs/prompt-library)
- [Model Context Window Limits](https://docs.anthropic.com/en/docs/models-overview)

### Community Resources
- [Anthropic Cookbook](https://github.com/anthropics/anthropic-cookbook) - Code examples
- [Discord Community](https://discord.gg/anthropic) - Get help from other developers
- [Reddit r/ClaudeAI](https://reddit.com/r/ClaudeAI) - Discussions and tips

### Advanced Topics
- **Multi-Agent Systems**: Orchestrating multiple Claude agents
- **Batch API**: Process thousands of requests with 50% cost reduction
- **Fine-tuning**: Custom models for domain-specific tasks
- **RAG (Retrieval-Augmented Generation)**: Integrate with vector databases

---

## 🎓 Summary: What You Learned

### The Four Patterns

1. **Agentic Loop** → Autonomous multi-step execution
2. **Structured Outputs** → Reliable machine-readable responses
3. **Adaptive Thinking** → Visible, controllable reasoning
4. **Streaming** → Real-time user feedback

### Key Insights

✅ **Don't hard-code workflows** → Let Claude orchestrate with tools  
✅ **Structure enables automation** → JSON schemas power integrations  
✅ **Thinking builds trust** → Transparency > black box decisions  
✅ **Streaming improves UX** → Progress > spinners

### From Here

**Start simple:** Pick one pattern, implement it for your use case

**Compose gradually:** Add patterns as needs grow (agentic → structured → thinking → streaming)

**Measure impact:** Track latency, cost, accuracy, user satisfaction

**Iterate:** Use thinking traces to identify where your prompts need improvement

---

## 💡 Final Thoughts

These patterns are **building blocks**, not rigid recipes. Mix and match based on your requirements:

- **Need speed?** Skip streaming, use low effort thinking
- **Need auditability?** High effort thinking + structured output
- **Need user trust?** All four patterns together

The key is understanding **when and why** to use each pattern. Now you have the tools to build production-ready AI agents that are:

✅ Autonomous (agentic loop)  
✅ Reliable (structured output)  
✅ Explainable (adaptive thinking)  
✅ User-friendly (streaming)

**Go build something amazing.** 🚀

---

**Questions?** Open an issue or reach out to the community. Happy building!
