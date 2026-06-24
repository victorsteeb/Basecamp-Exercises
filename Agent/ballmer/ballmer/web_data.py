"""Turn a deterministic SessionRecord into per-tick JSON frames for the web UI.

Pure data transform — no I/O, no server. The web server (serve_dashboard.py)
plays these frames back on a wall-clock cadence so the dashboard updates "live".

Each frame is the complete state to render at one tick:
  * current BAC, status, the recommendation message + action
  * the REALIZED BAC curve up to "now" (recomputed from drinks consumed so far,
    so we never reveal the future)
  * the BURNDOWN projection: a dashed decline line from now until BAC crosses the
    bottom of the band, plus the ETA clock time
  * drink-event markers consumed so far
  * the running tick log
"""

from __future__ import annotations

from datetime import timedelta

from .agent import SessionRecord, time_to_leave_window
from .bac_model import bac_curve
from .recommend import IN, ORDER, _na_drink  # noqa: F401  (_na_drink kept for parity)

_STATUS_LABEL = {
    "BELOW_WINDOW": "BELOW BAND",
    "IN_WINDOW": "IN RANGE",
    "ABOVE_WINDOW": "ABOVE BAND",
    "PAST_CEILING": "PAST CEILING",
}


def _clock(session: SessionRecord, now_hours: float) -> str:
    return (session.state.session_start + timedelta(hours=now_hours)
            ).strftime("%I:%M %p").lstrip("0")


def build_frames(session: SessionRecord) -> list[dict]:
    """One frame per tick. Frame N shows the world as of tick N (no future leak)."""
    st = session.state
    low, high = st.window
    beta = st.body.beta
    frames: list[dict] = []

    for i, tk in enumerate(session.ticks):
        now = tk.now_hours

        # Realized curve from drinks consumed AT OR BEFORE now (no future leak).
        events_so_far = [e for e in session.final_events if e.t_hours <= now + 1e-9]
        if now > 0:
            times, bac = bac_curve(events_so_far, st.body, t_end=now, t_start=0.0)
        else:
            times, bac = [0.0], [0.0]

        # Burndown projection: ODE forward from now with no new drinks.
        # Uses the same integrator as the main curve so residual absorption is
        # captured — the simple linear formula (current - low) / beta misses this.
        bd_hours = tk.burndown_hours
        bd_t, bd_bac = [], []
        bd_eta = None
        if bd_hours is not None and bd_hours > 0:
            low = st.window[0]
            t_end_proj = now + bd_hours + 1.0
            fwd_times, fwd_bacs = bac_curve(events_so_far, st.body,
                                             t_end=t_end_proj, t_start=now)
            for ft, fb in zip(fwd_times, fwd_bacs):
                bd_t.append(round(ft, 4))
                bd_bac.append(round(fb, 5))
                if fb <= low:
                    break
            if bd_t:
                bd_eta = _clock(session, bd_t[-1])

        events_marks = [
            {"t": round(e.t_hours, 3), "label": e.label, "grams": round(e.grams, 1)}
            for e in events_so_far
        ]

        body = st.body
        ticklog = []
        tab_total = 0.0
        for j in range(i + 1):
            tk_j = session.ticks[j]
            drink_obj = tk_j.recommendation.drink if tk_j.action == ORDER else None
            price = drink_obj.price if drink_obj else None
            bac_delta = (round(drink_obj.total_ethanol_g / (body.r * body.weight_kg * 10), 4)
                         if drink_obj else None)
            if price:
                tab_total += price
            ticklog.append({
                "clock": tk_j.clock,
                "bac": round(tk_j.current_bac, 3),
                "status": _STATUS_LABEL.get(tk_j.status, tk_j.status),
                "action": tk_j.action,
                "drink": tk_j.drink_name,
                "burndown": (round(tk_j.burndown_hours, 2)
                             if tk_j.burndown_hours is not None else None),
                "price": price,
                "bac_delta": bac_delta,
            })

        frames.append({
            "cursor": i,
            "n_ticks": len(session.ticks),
            "clock": tk.clock,
            "now_hours": round(now, 4),
            "band": [low, high],
            "ceiling": st.ceiling,
            "current_bac": round(tk.current_bac, 5),
            "status": tk.status,
            "status_label": _STATUS_LABEL.get(tk.status, tk.status),
            "in_range": tk.status == IN,
            "action": tk.action,
            "drink": tk.drink_name,
            "message": tk.recommendation.message,
            "burndown_hours": round(bd_hours, 3) if bd_hours is not None else None,
            "burndown_eta": bd_eta,
            "curve": {"t": [round(x, 4) for x in times], "bac": [round(x, 5) for x in bac]},
            "burndown_line": {"t": bd_t, "bac": bd_bac},
            "events": events_marks,
            "ticks": ticklog,
            "tab_total": round(tab_total, 2),
        })
    return frames


def session_meta(session: SessionRecord) -> dict:
    """Static metadata shown in the dashboard header."""
    st = session.state
    return {
        "session_start": st.session_start.isoformat(),
        "start_time": st.session_start.strftime("%H:%M"),
        "profile": st.profile,
        "r": round(st.body.r, 4),
        "beta": st.body.beta,
        "k_a": st.body.k_a_base,
        "band": list(st.window),
        "ceiling": st.ceiling,
        "duration_hours": st.session_duration_hours,
    }
