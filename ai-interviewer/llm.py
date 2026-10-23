"""Claude client, per-agent model config and one structured-call helper."""

import os
import pathlib

import anthropic

# Load ANTHROPIC_API_KEY from a .env here or in any parent (same idiom as the
# other exercises); a real value already in the environment wins.
for _d in [pathlib.Path(__file__).resolve().parent, *pathlib.Path(__file__).resolve().parents]:
    _envf = _d / ".env"
    if _envf.is_file():
        for _line in _envf.read_text().splitlines():
            _line = _line.strip()
            if _line.startswith("#") or "=" not in _line:
                continue
            _k, _v = _line.split("=", 1)
            _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
            if _k == "ANTHROPIC_API_KEY" and _v.startswith("sk-ant-"):
                os.environ.setdefault(_k, _v)
        break

if not os.environ.get("ANTHROPIC_API_KEY", "").startswith("sk-ant-"):
    raise SystemExit("❌ ANTHROPIC_API_KEY is not set. Export it or put it in a .env file.")

client = anthropic.Anthropic(timeout=300.0, max_retries=3)

# Model + effort per role. Override any model with e.g. INTERVIEWER_MODEL=claude-sonnet-5-5.
# The live interviewer runs at lower effort for turn latency; scoring and audit think harder.
AGENTS = {
    "planner":     (os.environ.get("PLANNER_MODEL", "claude-opus-5-5"), "high"),
    "interviewer": (os.environ.get("INTERVIEWER_MODEL", "claude-opus-5-5"), "low"),
    "scorer":      (os.environ.get("SCORER_MODEL", "claude-opus-5-5"), "high"),
    "auditor":     (os.environ.get("AUDITOR_MODEL", "claude-opus-5-5"), "high"),
    "candidate":   (os.environ.get("CANDIDATE_MODEL", "claude-opus-5-5"), "low"),
}

USAGE = {"input_tokens": 0, "output_tokens": 0, "calls": 0}


class AgentRefused(RuntimeError):
    pass


def call(agent: str, system: str, messages: list, schema):
    """One structured call. Returns (parsed_output, response.content).

    Callers that keep a multi-turn history must append response.content as-is
    (thinking blocks included) so the history stays append-only.
    """
    model, effort = AGENTS[agent]
    resp = client.beta.messages.parse(
        model=model,
        max_tokens=32000,
        system=system,
        messages=messages,
        output_format=schema,
        output_config={"effort": effort},
        # Server-side fallback: if a safety classifier declines, the API retries on
        # a suitable fallback model inside the same call.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    USAGE["calls"] += 1
    USAGE["input_tokens"] += resp.usage.input_tokens
    USAGE["output_tokens"] += resp.usage.output_tokens
    if resp.stop_reason == "refusal":
        raise AgentRefused(f"{agent} refused: {resp.stop_details}")
    if resp.stop_reason == "max_tokens" or resp.parsed_output is None:
        raise RuntimeError(f"{agent} returned no parsable output (stop_reason={resp.stop_reason})")
    return resp.parsed_output, resp.content
