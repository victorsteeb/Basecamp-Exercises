"""Ballmer demo — fully hands-free.

Flow (per the brief):
  load fake profile -> compute r-factor -> load fake tab -> run BAC-vs-time
  curve -> rank the next drink -> print the recommendation, projected peak BAC,
  time-in-target-window, and EVERY assumption used -> then run the always-on
  session across the whole night and render the dashboard.

Run from this directory:
    python run_demo.py
    python run_demo.py --no-color        # plain text
    python run_demo.py --empty-stomach   # change the food modifier
"""

import argparse
import sys

# Windows terminals default to cp1252, which can't encode the box-drawing /
# block / emoji glyphs in the dashboard. Force UTF-8 on stdout where possible.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

from ballmer import config
from ballmer.agent import load_state, run_session, tick
from ballmer.bac_model import watson_tbw_liters
from ballmer.dashboard import gauge, session_dashboard, status_banner
from ballmer.recommend import recommend_next

SAFETY_BANNER = """\
╔══════════════════════════════════════════════════════════════════════════╗
║  ⚠  THE "BALLMER PEAK" (0.129-0.138% BAC) IS A JOKE FROM XKCD #323.        ║
║     It is FAR above every legal driving limit and is NOT health, safety,   ║
║     or performance advice. Do NOT drive or operate machinery. This is a    ║
║     BAC-modeling demo. Real BAC in this range means serious impairment.    ║
╚══════════════════════════════════════════════════════════════════════════╝"""


def main(argv=None):
    p = argparse.ArgumentParser(description="Ballmer BAC always-on demo")
    p.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    p.add_argument("--empty-stomach", action="store_true", help="food_state=empty")
    p.add_argument("--full-stomach", action="store_true", help="food_state=full")
    p.add_argument("--no-auto-consume", action="store_true",
                   help="don't let the simulated drinker follow recommendations")
    args = p.parse_args(argv)

    if args.no_color:
        import ballmer.dashboard as d
        d._RESET = ""
        d._C = {k: "" for k in d._C}

    food = ("empty" if args.empty_stomach else
            "full" if args.full_stomach else config.DEFAULT_FOOD_STATE)

    print(SAFETY_BANNER)

    # 1-2. Profile + r-factor (show the unit conversions and the Watson math).
    st = load_state(".")
    height_cm = st.profile["height_in"] * config.IN_TO_CM
    weight_kg = st.profile["weight_lb"] * config.LB_TO_KG
    tbw = watson_tbw_liters(st.profile["sex"], st.profile["age"], height_cm, weight_kg)
    print(f"\nProfile: {st.profile['height_in']}in / {st.profile['weight_lb']}lb / "
          f"{st.profile['age']}y / {st.profile['sex']}")
    print(f"  -> {height_cm:.1f} cm, {weight_kg:.1f} kg")
    print(f"  Watson TBW = {tbw:.1f} L   r = TBW/(0.806*kg) = {st.body.r:.4f} "
          f"(flat Widmark would be {config.FLAT_WIDMARK_R['male']}; ours is lower "
          f"=> higher peak BAC, as expected for a heavier build)")
    print(f"  β = {st.body.beta} %/hr, k_a = {st.body.k_a_base} /hr, food = {food}")

    # 3. Seeded tab.
    print(f"\nSeeded tab (from state/tab.json), session start "
          f"{st.session_start.strftime('%I:%M %p').lstrip('0')}:")
    for ev in st.events:
        print(f"  +{ev.t_hours:.2f}h  {ev.label:<16} "
              f"{ev.grams:.1f} g ethanol ({ev.grams / config.STANDARD_DRINK_G:.1f} std)")

    # 4. One-shot recommendation "right now" (at the last drink time) — the
    #    required print of recommendation + projected peak + time-in-window +
    #    all assumptions + the top candidates.
    now = max((e.t_hours for e in st.events), default=0.0)
    rec = recommend_next(st.events, st.body, st.library, now,
                         window=st.window, ceiling=st.ceiling, food_state=food)
    print(f"\n--- Recommendation at {st.session_start.strftime('%I:%M %p').lstrip('0')} "
          f"+{now:.2f}h ---")
    print(f"  {rec.message}")
    print(f"\n  Top candidates (scored by dwell-in-band minus overshoot penalty):")
    print(f"    {'drink':<22}{'peak%':>7}{'min_in':>8}{'min_above':>10}{'score':>8}")
    for c in rec.ranked[:5]:
        name = c.drink.name if c.drink else "HOLD (no drink)"
        fc = c.forecast
        print(f"    {name:<22}{fc.projected_peak_bac:>7.3f}"
              f"{fc.minutes_in_window:>8.0f}{fc.minutes_above_window:>10.0f}{c.score:>8.1f}")
    print(f"\n  Assumptions used (auditable): {rec.ranked[0].forecast.assumptions}")

    # 5-6. Run the whole night hands-free + render the dashboard.
    session = run_session(".", auto_consume=not args.no_auto_consume, food_state=food)
    print("\n  Live status at each tick:")
    for tk in session.ticks:
        print("   " + status_banner(tk, st.window, st.ceiling))
        if tk.action != "HOLD":
            print("      " + gauge(tk.current_bac, st.window, st.ceiling))

    print(session_dashboard(session))
    print(f"Transcript written to state/log/. "
          f"Run `python -m pytest -q` for the engine tests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
