"""The LLM reasoning layer — the part that makes Ballmer an actual agent.

The math model (recommend.py) optimises dwell-time in the target band. This
module adds the layer the math can't: qualitative judgment. Claude sees the
current BAC state, the drink menu with vibe scores, and the math model's top
pick, then reasons about which drink best balances the physics AND the vibe of
the evening.

Called once per user request from the dashboard ("Ask Claude" button), NOT
during the batch simulation — so latency is spent when the user wants insight,
not at startup.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict

import anthropic

from .drinks import Drink

SYSTEM = """\
You are Sully, a gruff Boston bartendah who's seen it all at his dive bah in Southie. \
You talk like a true Bostonian — drop your R's ("bah", "cah", "wicked", "pahk"), \
use local slang ("wicked pissa", "no suh", "that's retahded", "kid", "chief"), \
and you've got strong opinions about drinks. \
You're also running this XKCD #323 Ballmer Peak experiment — you know the science \
because you Googled it — but you deliver it with pure Southie attitude. \
The physics model handles the math. Your job is the judgment call: \
given the BAC trajectory and the bah menu, tell the customer what to ordah (or HOLD) \
in 2–3 sentences of authentic Boston bartendah wisdom. \
Each drink has a vibe score (1–10) — factah it in. Don't break charactah."""


def _find_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    # Walk up the directory tree looking for a .env file.
    d = Path(__file__).resolve().parent
    for _ in range(7):
        env_file = d / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("ANTHROPIC_API_KEY="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val
        d = d.parent
    raise RuntimeError(
        "ANTHROPIC_API_KEY not found in environment or any .env file up to the repo root."
    )


class LLMRecommendation(TypedDict):
    drink_name: str    # exact library name, or "HOLD"
    reasoning: str     # 2-3 sentence explanation
    vibe_score: int    # vibe score of the chosen drink (0 if HOLD)


def llm_reason(frame: dict, library: list[Drink]) -> LLMRecommendation:
    """Ask Claude which drink to order (or hold) given the current state frame.

    frame   — the JSON frame dict from build_frames() for the current tick
    library — the full drink library (with vibe_score populated)

    Returns a typed dict: {drink_name, reasoning, vibe_score}.
    """
    key = _find_api_key()
    client = anthropic.Anthropic(api_key=key)

    current_bac = frame["current_bac"]
    status      = frame["status_label"]
    low, high   = frame["band"]
    ceiling     = frame["ceiling"]
    now_h       = frame["now_hours"]
    math_action = frame.get("action", "?")
    math_drink  = frame.get("drink")      # name of drink the math picked, or None

    # Describe recent drinks consumed (last 3)
    recent = frame.get("events", [])[-3:]
    recent_str = (
        ", ".join(e["label"] for e in recent) if recent else "none yet"
    )

    # Build the menu summary, alcoholic drinks only, sorted by vibe descending
    alcoholic = [d for d in library if d.is_alcoholic]
    alcoholic.sort(key=lambda d: d.vibe_score, reverse=True)
    menu_lines = [
        f"  • {d.name} [{d.category}] — {d.total_ethanol_g:.1f}g ethanol "
        f"({d.standard_drinks:.1f} std), vibe {d.vibe_score}/10"
        + (f" — {d.notes}" if d.notes else "")
        for d in alcoholic
    ]
    menu = "\n".join(menu_lines)

    math_line = (
        f"Physics model says: {math_action}"
        + (f" → {math_drink}" if math_drink else " (no drink)")
    )

    user_msg = f"""\
=== Current state ===
BAC: {current_bac:.3f}%  ({status})
Target band: {low:.3f}–{high:.3f}%  |  Safety ceiling: {ceiling:.3f}%
Session time: +{now_h:.1f} h
Recent drinks: {recent_str}

{math_line}

=== Bar menu ===
{menu}

Pick the next drink (exact name from the menu above) or say HOLD. \
Tell 'em what to do in 2–3 sentences — Boston bartendah voice, no suh."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=350,
        system=SYSTEM,
        tools=[{
            "name": "pick_drink",
            "description": "Record the drink recommendation and reasoning.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "drink_name": {
                        "type": "string",
                        "description": (
                            "Exact drink name from the menu (copy it verbatim), "
                            "or the string 'HOLD' to recommend waiting."
                        )
                    },
                    "reasoning": {
                        "type": "string",
                        "description": (
                            "2–3 punchy sentences explaining the pick, "
                            "referencing both the BAC position and the drink's vibe."
                        )
                    }
                },
                "required": ["drink_name", "reasoning"]
            }
        }],
        tool_choice={"type": "tool", "name": "pick_drink"},
        messages=[{"role": "user", "content": user_msg}]
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "pick_drink":
            inp = block.input
            drink_name = inp.get("drink_name", "HOLD")
            reasoning  = inp.get("reasoning", "")
            # Look up vibe score of the chosen drink
            vibe = 0
            for d in library:
                if d.name.lower() == drink_name.lower():
                    vibe = d.vibe_score
                    break
            return LLMRecommendation(
                drink_name=drink_name,
                reasoning=reasoning,
                vibe_score=vibe,
            )

    raise RuntimeError("Claude did not call the pick_drink tool.")
