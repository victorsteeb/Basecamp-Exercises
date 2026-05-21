import subprocess
import sys
subprocess.run([sys.executable, "-m", "pip", "install", "anthropic", "tabulate", "--quiet"], check=True)

import importlib
import tabulate
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.environ.get("ANTHROPIC_API_KEY", "")

import anthropic

client = anthropic.Anthropic(api_key=api_key)

MODEL_SONNET = "claude-sonnet-4-5-20250929"
MODEL_HAIKU = "claude-haiku-4-5-20251001"
MODEL_OPUS = "claude-opus-4-5-20251101"

DEFAULT_MODEL = MODEL_SONNET

try:
    response = client.messages.create(model=DEFAULT_MODEL, max_tokens=5, messages=[{"role": "user", "content": "Ping"}])
    print(f"Health check passed: {response.content[0].text}")
    print(f"Using model: {DEFAULT_MODEL}")
except anthropic.APIError as e:
    print(f"Health check failed: {e}")
    raise

from dataclasses import dataclass, field
from typing import List, Optional
from tabulate import tabulate
import statistics

@dataclass
class BenchmarkResult:
    """Timing, tokens, and cost for a single API call."""
    ttft: float
    total_time: float
    tokens_per_second: float
    input_tokens: int
    output_tokens: int
    endpoint: str
    model: str
    test_name: str
    otps: Optional[float] = None
    cost: Optional[float] = None
    cache_creation_input_tokens: Optional[int] = None
    cache_read_input_tokens: Optional[int] = None


@dataclass
class BenchmarkSuite:
    """Collects results across multiple runs."""
    results: List[BenchmarkResult] = field(default_factory=list)

    def add_result(self, result: BenchmarkResult):
        self.results.append(result)

    def clear(self):
        self.results = []

    def summary(self, group_by: str = "test_name") -> str:
        if not self.results:
            return "No results."

        groups = {}
        for r in self.results:
            key = getattr(r, group_by)
            if key not in groups:
                groups[key] = []
            groups[key].append(r)

        rows = []
        for name, group in groups.items():
            ttfts = [r.ttft * 1000 for r in group]
            ttcs = [r.total_time * 1000 for r in group]
            throughputs = [r.otps or r.tokens_per_second for r in group]
            costs = [r.cost for r in group if r.cost is not None]

            row = [
                name,
                len(group),
                f"{statistics.mean(ttfts):.0f}",
                f"{statistics.mean(ttcs):.0f}",
                f"{statistics.mean(throughputs):.1f}",
            ]
            if costs:
                row.append(f"${sum(costs)*1000:.4f}")
            rows.append(row)

        headers = ["Test", "Runs", "TTFT(ms)", "TTC(ms)", "OTPS"]
        if any(r.cost for r in self.results):
            headers.append("$/1K calls")
        return tabulate(rows, headers=headers, tablefmt="grid")


suite = BenchmarkSuite()
print("✓ BenchmarkSuite ready (with cost tracking)")

# ─── Part 1: Metrics ──────────────────────────────────────────────────────────

import time

def _stream_request(prompt, model=DEFAULT_MODEL, max_tokens=256):
    """Low-level helper: stream a request, return raw timing + response."""
    ttft = None
    start_time = time.perf_counter()
    with client.messages.stream(
        model=model, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for event in stream:
            if ttft is None and event.type == "content_block_start":
                ttft = time.perf_counter() - start_time
        response = stream.get_final_message()

    total_time = time.perf_counter() - start_time
    return ttft, total_time, response

print("✓ _stream_request helper ready")

ttft, total_time, response = _stream_request("What is 2 + 2? Answer in one word.")
print(f"Response: {response.content[0].text}")
print(f"TTFT: {ttft * 1000:.0f}ms")
print(f"TTC:  {total_time * 1000:.0f}ms")


def compute_otps(ttft, total_time, output_tokens):
    gen_time = total_time - ttft
    if gen_time <= 0:
        gen_time = 0.001
    otps = output_tokens / gen_time
    return otps, gen_time


ttft, total_time, response = _stream_request("What is 2 + 2? Answer in one word.")

tokens = response.usage.output_tokens
otps, gen_time = compute_otps(ttft, total_time, tokens)

print(f"Response: {response.content[0].text}")
print(f"TTFT: {ttft * 1000:.0f}ms")
print(f"TTC:  {total_time * 1000:.0f}ms")
print(f"OTPS: {otps:.1f} tokens/sec ({tokens} tokens / {gen_time:.3f}s)")


PRICING = {
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001":  {"input": 0.25, "output": 1.25},
    "claude-opus-4-5-20251101":   {"input": 15.00, "output": 75.00},
}

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> tuple[float, float, float]:
    prices = PRICING.get(model, {"input": 3.00, "output": 15.00})
    input_cost  = (input_tokens  / 1_000_000) * prices["input"]
    output_cost = (output_tokens / 1_000_000) * prices["output"]
    total = input_cost + output_cost
    return input_cost, output_cost, total


ttft, total_time, response = _stream_request("What is 2 + 2? Answer in one word.")

usage = response.usage
input_cost, output_cost, cost = calculate_cost(DEFAULT_MODEL, usage.input_tokens, usage.output_tokens)

print(f"Response: {response.content[0].text}")
print(f"Tokens: {usage.input_tokens} in / {usage.output_tokens} out")
print(f"Cost:   ${cost:.6f} (input: ${input_cost:.6f}, output: ${output_cost:.6f})")


def measure_streaming_latency(
    prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 256,
    test_name: str = "streaming"
) -> BenchmarkResult:
    ttft, total_time, response = _stream_request(prompt, model, max_tokens)
    usage = response.usage
    _, _, cost = calculate_cost(model, usage.input_tokens, usage.output_tokens)
    otps, _ = compute_otps(ttft, total_time, usage.output_tokens)

    return BenchmarkResult(
        ttft=ttft,
        total_time=total_time,
        tokens_per_second=otps,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        endpoint="1p",
        model=model,
        test_name=test_name,
        otps=otps,
        cost=cost,
    )

# ─── Part 2: Compare Models ───────────────────────────────────────────────────

def percentile(data, p):
    sorted_data = sorted(data)
    idx = (len(sorted_data) - 1) * p / 100
    low = int(idx)
    high = min(low + 1, len(sorted_data) - 1)
    fraction = idx - low
    return sorted_data[low] + fraction * (sorted_data[high] - sorted_data[low])

suite.clear()
PROMPT = "What is machine learning? Answer in 2 sentences."

models = [
    (MODEL_HAIKU,  "haiku"),
    (MODEL_SONNET, "sonnet"),
    (MODEL_OPUS,   "opus"),
]

for model_id, model_name in models:
    print(f"\nBenchmarking {model_name}...")

    for i in range(5):
        result = measure_streaming_latency(PROMPT, model=model_id, test_name=model_name)
        suite.add_result(result)

        ttft_ms = result.ttft * 1000
        ttc_ms  = result.total_time * 1000
        print(f"  Run {i+1}: TTFT={ttft_ms:.0f}ms, TTC={ttc_ms:.0f}ms, OTPS={result.otps:.1f}, Cost=${result.cost:.6f}")

print("\n" + suite.summary())

# ─── Part 3: Tool Use ─────────────────────────────────────────────────────────

import json

CALCULATOR_TOOL = {
    "name": "calculator",
    "description": "Performs basic arithmetic operations.",
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["add", "subtract", "multiply", "divide"],
                "description": "The arithmetic operation to perform."
            },
            "operands": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Exactly two numbers to operate on.",
                "minItems": 2,
                "maxItems": 2
            }
        },
        "required": ["operation", "operands"]
    }
}

print("Calculator tool:")
print(json.dumps(CALCULATOR_TOOL, indent=2))


def execute_calculator(operation: str, operands: list) -> float:
    a, b = operands[0], operands[1]
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        return a / b
    else:
        raise ValueError(f"Unknown: {operation}")

print(f"Test: 42 * 17 = {execute_calculator('multiply', [42, 17])}")


def measure_tool_use_latency(prompt: str, model: str = DEFAULT_MODEL, max_tokens: int = 256):
    """Measure full round-trip latency for a tool use request."""
    start_time = time.perf_counter()

    first_response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        tools=[CALCULATOR_TOOL],
        messages=[{"role": "user", "content": prompt}]
    )

    ttft = time.perf_counter() - start_time

    tool_use_block = None
    for block in first_response.content:
        if block.type == "tool_use":
            tool_use_block = block
            break

    if tool_use_block is None:
        total_time = time.perf_counter() - start_time
        return ttft, total_time, "No tool used", first_response.usage.input_tokens, first_response.usage.output_tokens

    result = execute_calculator(
        tool_use_block.input["operation"],
        tool_use_block.input["operands"]
    )

    second_response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        tools=[CALCULATOR_TOOL],
        messages=[
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": first_response.content},
            {"role": "user", "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_block.id,
                    "content": str(result)
                }
            ]}
        ]
    )

    total_time = time.perf_counter() - start_time

    final_text = ""
    for block in second_response.content:
        if hasattr(block, "text"):
            final_text += block.text

    total_input  = first_response.usage.input_tokens  + second_response.usage.input_tokens
    total_output = first_response.usage.output_tokens + second_response.usage.output_tokens

    return ttft, total_time, final_text, total_input, total_output


ttft, total, text, in_tok, out_tok = measure_tool_use_latency("What is 42 * 17? Use the calculator.")
print(f"TTFT: {ttft*1000:.0f}ms")
print(f"Result: {text}")
print("\n✓ Tool use working!")

suite.clear()

print("Without tool:")
for i in range(5):
    result = measure_streaming_latency(
        "What is forty-two times seventeen? Show your work.",
        test_name="no_tool"
    )
    suite.add_result(result)
    print(f"  Run {i+1}: TTFT={result.ttft*1000:.0f}ms, TTC={result.total_time*1000:.0f}ms, Cost=${result.cost:.6f}")

print("\nWith tool:")
for i in range(5):
    ttft, total_time, text, in_tok, out_tok = measure_tool_use_latency(
        "What is 42 * 17? Use the calculator."
    )
    _, _, cost = calculate_cost(DEFAULT_MODEL, in_tok, out_tok)
    otps, gen_time = compute_otps(ttft, total_time, out_tok)

    result = BenchmarkResult(
        ttft=ttft,
        total_time=total_time,
        tokens_per_second=otps,
        input_tokens=in_tok,
        output_tokens=out_tok,
        endpoint="1p",
        model=DEFAULT_MODEL,
        test_name="with_tool",
        otps=otps,
        cost=cost,
    )
    suite.add_result(result)
    print(f"  Run {i+1}: TTFT={ttft*1000:.0f}ms, TTC={total_time*1000:.0f}ms, Cost=${cost:.6f}")

print("\n" + suite.summary())

# ─── Part 4: Prompt Caching ───────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert API documentation assistant.
You help developers understand REST API design, authentication patterns,
security best practices, rate limiting, pagination, error handling,
versioning strategies, webhook design, and performance optimization.
Always provide concrete examples with HTTP methods and status codes.
""" * 20

system_block = [{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}]

def cached_request(question):
    start = time.perf_counter()
    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=256,
        system=system_block,
        messages=[{"role": "user", "content": question}]
    )
    elapsed = time.perf_counter() - start
    return response, elapsed


r1, time1 = cached_request("What is REST?")
print(f"Cold call: {time1 * 1000:.0f}ms")
print(f"  Cache created: {r1.usage.cache_creation_input_tokens or 0} tokens")
print(f"  Cache read:    {r1.usage.cache_read_input_tokens or 0} tokens")
print(f"  Input tokens:  {r1.usage.input_tokens}")

r2, time2 = cached_request("What is OAuth?")
print(f"\nWarm call: {time2 * 1000:.0f}ms")
print(f"  Cache created: {r2.usage.cache_creation_input_tokens or 0} tokens")
print(f"  Cache read:    {r2.usage.cache_read_input_tokens or 0} tokens")
print(f"  Input tokens:  {r2.usage.input_tokens}")


SYSTEM_PROMPT = """You are a helpful API design consultant. You specialize in REST API design,
authentication patterns, rate limiting, pagination, error handling, versioning strategies,
webhook design, and performance optimization. Always provide concrete examples with HTTP
methods, status codes, request/response schemas, and curl commands.
""" * 20

SYSTEM = [{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}]

def chat(messages, new_question):
    for msg in messages:
        if msg["role"] == "assistant" and isinstance(msg["content"], list):
            msg["content"] = msg["content"][0]["text"]

    if messages and messages[-1]["role"] == "assistant":
        last_text = messages[-1]["content"]
        messages[-1]["content"] = [{"type": "text", "text": last_text, "cache_control": {"type": "ephemeral"}}]

    messages.append({"role": "user", "content": new_question})

    start = time.perf_counter()
    response = client.messages.create(
        model=MODEL_SONNET,
        max_tokens=300,
        system=SYSTEM,
        messages=messages,
    )
    elapsed = time.perf_counter() - start

    answer = response.content[0].text
    messages.append({"role": "assistant", "content": answer})

    return answer, elapsed, response.usage


conversation = []
questions = [
    "Design a REST API for a todo app. Include all endpoints.",
    "Now add authentication. What changes?",
    "Add rate limiting. How should the headers look?",
    "Now add team support — users can share todo lists.",
    "Summarize the full API design so far.",
]

for i, question in enumerate(questions):
    answer, elapsed, usage = chat(conversation, question)

    cached = usage.cache_read_input_tokens or 0
    created = usage.cache_creation_input_tokens or 0

    print(f"Turn {i+1}: {elapsed * 1000:.0f}ms | cached: {cached} | created: {created}")
