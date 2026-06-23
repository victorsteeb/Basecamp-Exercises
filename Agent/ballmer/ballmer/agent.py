"""The always-on agent: tick -> read state -> recompute BAC -> recommend -> log.

This mirrors the Always-On Ops exercise's construct (a routine wakes the agent,
it reads repo state, reasons against its runbook/policy, and writes an action).
Here the "tick" runs over FAST-FORWARDED simulated time so a whole bar night
plays out in one hands-free run.

State repo:
    state/profile.json      body metrics            (read)
    state/tab.json          drinks consumed so far  (read; live state)
    state/target.json       window + ceiling        (read)
    drink-library.json      the menu                (read)
    reference/*.md          assumptions + policy     (the agent's "runbook")
    state/log/              recommendations + transcript (WRITE — the agent's action)

The seed tab.json is treated read-only for demo repeatability; the evolving
session is written to state/log/. A real cloud Routine would commit back to
tab.json each tick instead.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import config
from .bac_model import BodyParams, DrinkEvent, bac_at, bac_curve, peak_bac
from .drinks import Drink, find_drink, load_library
from .recommend import ORDER, Recommendation, recommend_next


# --------------------------------------------------------------------------
# State loading
# --------------------------------------------------------------------------
@dataclass
class State:
    profile: dict
    body: BodyParams
    events: list[DrinkEvent]
    library: list[Drink]
    session_start: datetime
    window: tuple[float, float]
    ceiling: float
    tick_interval_min: float
    session_duration_hours: float


def _hours_since(start: datetime, ts: str) -> float:
    return (datetime.fromisoformat(ts) - start).total_seconds() / 3600.0


def load_state(root: str | Path = ".") -> State:
    root = Path(root)
    profile = json.loads((root / "state/profile.json").read_text(encoding="utf-8"))
    tab = json.loads((root / "state/tab.json").read_text(encoding="utf-8"))
    target = json.loads((root / "state/target.json").read_text(encoding="utf-8"))
    library = load_library(root / "drink-library.json")

    session_start = datetime.fromisoformat(tab["session_start"])
    events: list[DrinkEvent] = []
    for item in tab["consumed"]:
        drink = find_drink(library, item["name"])
        if drink is None:
            raise ValueError(f"tab references unknown drink {item['name']!r}")
        events.append(DrinkEvent(
            t_hours=_hours_since(session_start, item["time"]),
            grams=drink.total_ethanol_g,
            label=drink.name,
            food_state=item.get("food_state", config.DEFAULT_FOOD_STATE),
        ))

    return State(
        profile=profile,
        body=BodyParams.from_profile(profile),
        events=events,
        library=library,
        session_start=session_start,
        window=(target["target_low"], target["target_high"]),
        ceiling=target["safety_ceiling"],
        tick_interval_min=target.get("tick_interval_min", 20),
        session_duration_hours=target.get("session_duration_hours", 5.0),
    )


# --------------------------------------------------------------------------
# Burndown: when do we leave the target window?
# --------------------------------------------------------------------------
def time_to_leave_window(current_bac: float, window: tuple[float, float],
                         beta: float) -> float | None:
    """Hours until BAC declines out the BOTTOM of the window, assuming NO more
    drinks and steady zero-order elimination β.

    Returns None if already below the window (nothing to burn down). If above the
    window, this is the time to drop below the *low* edge (i.e. fully exit), which
    is the 'burndown to leaving the range' the user cares about.
    """
    low, _ = window
    if current_bac <= low:
        return None
    return (current_bac - low) / beta


# --------------------------------------------------------------------------
# Tick + session loop
# --------------------------------------------------------------------------
@dataclass
class TickRecord:
    now_hours: float
    clock: str                 # human wall-clock label
    current_bac: float
    status: str
    action: str
    drink_name: str | None
    recommendation: Recommendation
    burndown_hours: float | None     # time-to-leave-window (None if below)


@dataclass
class SessionRecord:
    state: State
    ticks: list[TickRecord] = field(default_factory=list)
    curve_times: list[float] = field(default_factory=list)
    curve_bac: list[float] = field(default_factory=list)
    final_events: list[DrinkEvent] = field(default_factory=list)


def _clock(start: datetime, now_hours: float) -> str:
    from datetime import timedelta
    return (start + timedelta(hours=now_hours)).strftime("%I:%M %p").lstrip("0")


def tick(events: list[DrinkEvent], st: State, now_hours: float,
         food_state: str = config.DEFAULT_FOOD_STATE) -> TickRecord:
    """One wake-up: assess current BAC, produce a recommendation, package it."""
    rec = recommend_next(events, st.body, st.library, now_hours,
                         window=st.window, ceiling=st.ceiling, food_state=food_state)
    burndown = time_to_leave_window(rec.current_bac, st.window, st.body.beta)
    return TickRecord(
        now_hours=now_hours,
        clock=_clock(st.session_start, now_hours),
        current_bac=rec.current_bac,
        status=rec.status,
        action=rec.action,
        drink_name=rec.drink.name if rec.drink else None,
        recommendation=rec,
        burndown_hours=burndown,
    )


def run_session(root: str | Path = ".", auto_consume: bool = True,
                food_state: str = config.DEFAULT_FOOD_STATE,
                write_log: bool = True) -> SessionRecord:
    """Fast-forward the whole night, ticking every tick_interval_min.

    auto_consume: if True, when the agent recommends ORDER the simulated drinker
    follows it — the drink is added to the event list at that tick (STUB:
    confirm_order). This is what makes the BAC curve climb into the band hands-
    free and demonstrates the agent steering the night.
    """
    st = load_state(root)
    events = list(st.events)

    dt_h = st.tick_interval_min / 60.0
    # Start ticking after the last seeded drink (or now), through the session end.
    t = max((e.t_hours for e in events), default=0.0)
    t_end = st.session_duration_hours

    session = SessionRecord(state=st)
    while t <= t_end + 1e-9:
        rec_tick = tick(events, st, t, food_state=food_state)
        session.ticks.append(rec_tick)
        if auto_consume and rec_tick.action == ORDER and rec_tick.recommendation.drink:
            d = rec_tick.recommendation.drink
            events.append(DrinkEvent(t_hours=t, grams=d.total_ethanol_g,
                                     label=d.name, food_state=food_state))
        t += dt_h

    # Full curve over the night for the dashboard.
    times, bac = bac_curve(events, st.body, t_end=t_end + 1.0, t_start=0.0)
    session.curve_times = times
    session.curve_bac = bac
    session.final_events = events

    if write_log:
        _write_log(root, session)
    return session


def _write_log(root: str | Path, session: SessionRecord) -> Path:
    """Append the session transcript to state/log/ (the agent's 'action')."""
    log_dir = Path(root) / "state" / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = session.state.session_start.strftime("%Y%m%dT%H%M")
    out = log_dir / f"session-{stamp}.md"
    lines = [f"# Ballmer session log — start {session.state.session_start.isoformat()}",
             "",
             f"- r = {session.state.body.r:.4f}, "
             f"weight = {session.state.body.weight_kg:.1f} kg, "
             f"β = {session.state.body.beta} %/hr, "
             f"k_a = {session.state.body.k_a_base} /hr",
             f"- target window {session.state.window[0]:.3f}-{session.state.window[1]:.3f}%, "
             f"ceiling {session.state.ceiling:.3f}%",
             "",
             "| time | BAC% | status | action | drink | burndown(h) |",
             "|------|------|--------|--------|-------|-------------|"]
    for tk in session.ticks:
        bd = f"{tk.burndown_hours:.2f}" if tk.burndown_hours is not None else "-"
        lines.append(f"| {tk.clock} | {tk.current_bac:.3f} | {tk.status} | "
                     f"{tk.action} | {tk.drink_name or '-'} | {bd} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
