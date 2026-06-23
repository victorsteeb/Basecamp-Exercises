"""Terminal dashboard: are you IN RANGE, and when will you burn down out of it?

Pure-text, zero-dependency renderer so the always-on demo always works in any
terminal. Renders:
  * a status banner (BELOW / IN RANGE / ABOVE / PAST CEILING)
  * a BAC gauge with the target band marked
  * an ASCII BAC-vs-time curve for the whole night, band shaded
  * the burndown: projected time until BAC leaves the target window

A matplotlib renderer (dashboard_plot.py) can be layered on top without touching
this file or the engine.
"""

from __future__ import annotations

from .agent import SessionRecord, TickRecord, time_to_leave_window
from .recommend import ABOVE, BELOW, IN, PAST_CEILING

# ANSI colors (degrade gracefully if the terminal ignores them).
_RESET = "\033[0m"
_C = {BELOW: "\033[36m", IN: "\033[32m", ABOVE: "\033[33m", PAST_CEILING: "\033[31m"}
_LABEL = {BELOW: "BELOW BAND", IN: "IN RANGE ✦", ABOVE: "ABOVE BAND",
          PAST_CEILING: "PAST CEILING ⚠"}


def status_banner(tk: TickRecord, window, ceiling) -> str:
    color = _C.get(tk.status, "")
    low, high = window
    bd = ("—" if tk.burndown_hours is None
          else f"{tk.burndown_hours:.2f} h until you drop below {low:.3f}%")
    return (f"{color}[{_LABEL.get(tk.status, tk.status)}]{_RESET}  "
            f"BAC {tk.current_bac:.3f}%  |  band {low:.3f}-{high:.3f}%  "
            f"|  ceiling {ceiling:.3f}%  |  burndown: {bd}")


def gauge(current: float, window, ceiling, width: int = 50) -> str:
    """A horizontal BAC gauge from 0 to just past the ceiling, band marked [ ]."""
    low, high = window
    top = max(ceiling * 1.15, high * 1.2, current * 1.1, 1e-6)
    def pos(v):
        return min(width - 1, max(0, int(round(v / top * (width - 1)))))
    cells = [" "] * width
    for i in range(pos(low), pos(high) + 1):     # shade the target band
        cells[i] = "="
    cells[pos(low)] = "["
    cells[pos(high)] = "]"
    cells[pos(ceiling)] = "X"                      # ceiling marker
    cells[pos(current)] = "●"                      # you are here
    bar = "".join(cells)
    return f"0% |{bar}| {top:.3f}%   ([ ]=target band  X=ceiling  ●=you)"


def curve_chart(session: SessionRecord, height: int = 12, width: int = 64) -> str:
    """ASCII line chart of BAC over the night, target band shaded as '·' rows."""
    times, bac = session.curve_times, session.curve_bac
    if not bac:
        return "(no curve)"
    low, high = session.state.window
    ceiling = session.state.ceiling
    top = max(max(bac), ceiling) * 1.12
    # downsample to `width` columns
    cols = []
    n = len(bac)
    for c in range(width):
        i = int(c / width * n)
        cols.append(bac[i])
    rows = []
    for r in range(height, -1, -1):
        level = r / height * top
        line = []
        for v in cols:
            if v >= level - (top / height / 2):
                line.append("█")
            elif low <= level <= high:
                line.append("·")        # shade the band region across the row
            else:
                line.append(" ")
        # axis label
        rows.append(f"{level:6.3f} |" + "".join(line))
    t0, t1 = times[0], times[-1]
    axis = "       +" + "-" * width
    xlabel = f"        {t0:.1f}h{' ' * (width - 8)}{t1:.1f}h  (session hours)"
    band_note = f"  (band {low:.3f}-{high:.3f}% shown as '·';  █ = BAC curve)"
    return "\n".join(rows) + "\n" + axis + "\n" + xlabel + band_note


def session_dashboard(session: SessionRecord) -> str:
    """Full end-of-night dashboard: curve + per-tick burndown table + summary."""
    st = session.state
    out = ["", "=" * 78, "  BALLMER DASHBOARD — BAC vs. the (joke) Ballmer Peak band", "=" * 78,
           "", curve_chart(session), "",
           "  Tick-by-tick:", "  " + "-" * 74,
           f"  {'time':>8} {'BAC%':>7} {'status':>13} {'action':>20} {'burndown':>10}",
           "  " + "-" * 74]
    for tk in session.ticks:
        bd = "—" if tk.burndown_hours is None else f"{tk.burndown_hours:.2f}h"
        label = _LABEL.get(tk.status, tk.status)
        act = tk.action + (f": {tk.drink_name}" if tk.drink_name else "")
        out.append(f"  {tk.clock:>8} {tk.current_bac:>7.3f} {label:>13} {act:>20} {bd:>10}")
    out.append("  " + "-" * 74)

    # Summary: time spent in band, peak, and final burndown.
    in_band = [tk for tk in session.ticks if tk.status == IN]
    peak_tk = max(session.ticks, key=lambda t: t.current_bac)
    out += ["",
            f"  Peak BAC: {peak_tk.current_bac:.3f}% at {peak_tk.clock}",
            f"  Ticks spent IN the target band: {len(in_band)} / {len(session.ticks)}",
            f"  Final burndown: " + (
                "below band — nothing to burn down"
                if peak_tk.burndown_hours is None and session.ticks[-1].burndown_hours is None
                else (f"{session.ticks[-1].burndown_hours:.2f} h to leave the band"
                      if session.ticks[-1].burndown_hours is not None
                      else "below band")),
            "=" * 78, ""]
    return "\n".join(out)
