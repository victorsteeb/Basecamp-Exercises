"""Unit tests for the BAC engine, checked against hand calculations.

Run from the outer `ballmer/` directory:
    python -m pytest -q
    # or, without pytest installed:
    python tests/test_bac_model.py
"""

import math
import os
import sys

# Allow `import ballmer...` when run directly (not just under pytest).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ballmer import config
from ballmer.bac_model import (
    BodyParams,
    DrinkEvent,
    bac_curve,
    ethanol_grams,
    forecast,
    peak_bac,
    r_from_profile,
    watson_tbw_liters,
    weight_kg_from_profile,
    widmark_r,
)

PROFILE = {"height_in": 73, "weight_lb": 220, "age": 39, "sex": "male"}


def approx(a, b, tol):
    return abs(a - b) <= tol


# --------------------------------------------------------------------------
# Watson TBW + r-factor
# --------------------------------------------------------------------------
def test_watson_tbw_demo_profile():
    # height 73in -> 185.42cm, weight 220lb -> 99.79kg
    # TBW = 2.447 - 0.09516*39 + 0.1074*185.42 + 0.3362*99.79 = 52.2 L (hand calc)
    height_cm = PROFILE["height_in"] * config.IN_TO_CM
    weight_kg = PROFILE["weight_lb"] * config.LB_TO_KG
    tbw = watson_tbw_liters("male", 39, height_cm, weight_kg)
    assert approx(tbw, 52.2, 0.3), f"TBW {tbw:.2f} L not ~52.2"


def test_r_factor_in_expected_band():
    # With the blood-water correction r = TBW/(0.806*W) -> ~0.649, in the
    # prompt's expected 0.64-0.66 band (and below the flat 0.68, as expected
    # for a heavier individual with more fat).
    r = r_from_profile(PROFILE)
    assert 0.64 <= r <= 0.66, f"r={r:.4f} outside expected 0.64-0.66"
    assert r < config.FLAT_WIDMARK_R["male"]


def test_widmark_r_formula_directly():
    # r = TBW / (0.806 * W). Plug TBW=52.2, W=99.79.
    expected = 52.2 / (config.BLOOD_WATER_FRACTION * 99.79)
    got = widmark_r(52.2, 99.79)
    assert approx(got, expected, 1e-9)


# --------------------------------------------------------------------------
# Ethanol mass from recipe
# --------------------------------------------------------------------------
def test_ethanol_grams_standard_shot():
    # 44 mL (1.5 oz) of 40% spirit -> 44 * 0.40 * 0.789 = 13.89 g (~1 std drink)
    g = ethanol_grams(44.0, 0.40)
    assert approx(g, 13.89, 0.05), f"{g:.2f} g not ~13.89"


def test_ethanol_grams_zero_for_water():
    assert ethanol_grams(355.0, 0.0) == 0.0


# --------------------------------------------------------------------------
# Widmark peak (no-elimination) — the closed-form anchor
# --------------------------------------------------------------------------
def test_single_drink_widmark_peak_closed_form():
    # BAC%_peak = A / (r * W * 10). 14 g, r=0.649, W=99.79.
    body = BodyParams.from_profile(PROFILE)
    expected = 14.0 / (body.r * body.weight_kg * 10.0)
    assert approx(expected, 0.0216, 0.001), f"closed-form peak {expected:.4f} not ~0.0216"


def test_single_drink_peak_before_elimination_sanity():
    # THE sanity check from the brief: one standard drink (~14 g) should land
    # "around 0.018-0.020% BAC BEFORE ELIMINATION" for this profile. That is the
    # closed-form Widmark peak A/(r*W*10) = ~0.0216 (a touch above 0.020 because
    # our Watson-derived r=0.649 is slightly below the flat 0.68). We assert a
    # band around the brief's number. If this is WILDLY off, suspect the Watson
    # unit conversion (in -> cm, lb -> kg) first.
    body = BodyParams.from_profile(PROFILE)
    peak_before_elim = 14.0 / (body.r * body.weight_kg * 10.0)
    assert 0.018 <= peak_before_elim <= 0.023, (
        f"before-elimination peak {peak_before_elim:.4f} outside sanity band")


def test_single_drink_realized_peak_is_lower_than_closed_form():
    # Documents (and regression-locks) the physically-correct fact that a single
    # small drink's REALIZED continuous-model peak is well below its closed-form
    # peak, because elimination (0.015%/hr) removes a large share of one drink's
    # ~0.02% during the ~30 min it takes to absorb. This is why reaching the
    # (absurd) 0.13% Ballmer band requires MANY drinks close together.
    body = BodyParams.from_profile(PROFILE)
    events = [DrinkEvent(t_hours=0.0, grams=14.0, label="std drink", food_state="light")]
    times, bac = bac_curve(events, body, t_end=6.0)
    _, realized = peak_bac(times, bac)
    closed_form = 14.0 / (body.r * body.weight_kg * 10.0)
    assert 0.006 <= realized <= 0.012, f"realized peak {realized:.4f} off expected ~0.0085"
    assert realized < closed_form


# --------------------------------------------------------------------------
# Dynamics: absorption rise, elimination decline, non-negativity
# --------------------------------------------------------------------------
def test_curve_never_negative():
    body = BodyParams.from_profile(PROFILE)
    events = [DrinkEvent(0.0, 14.0, "d", "light")]
    _, bac = bac_curve(events, body, t_end=12.0)
    assert min(bac) >= 0.0


def test_bac_returns_to_zero_eventually():
    body = BodyParams.from_profile(PROFILE)
    events = [DrinkEvent(0.0, 14.0, "d", "light")]
    _, bac = bac_curve(events, body, t_end=12.0)
    # Not exactly 0.0: first-order absorption is asymptotic, so an infinitesimal
    # (~1e-17) tail re-seeds each step once BAC hits zero. "Essentially zero".
    assert bac[-1] < 1e-4, f"BAC should be ~0 within 12h, got {bac[-1]:.6f}"


def test_elimination_is_monotonic_after_peak():
    body = BodyParams.from_profile(PROFILE)
    events = [DrinkEvent(0.0, 14.0, "d", "light")]
    times, bac = bac_curve(events, body, t_end=10.0)
    i_peak = max(range(len(bac)), key=lambda j: bac[j])
    # after the peak, until it hits zero, the series must be non-increasing
    tail = bac[i_peak:]
    nonzero_tail = [v for v in tail if v > 0]
    assert all(nonzero_tail[k] >= nonzero_tail[k + 1] - 1e-9
               for k in range(len(nonzero_tail) - 1))


def test_empty_stomach_peaks_higher_and_earlier_than_full():
    body = BodyParams.from_profile(PROFILE)
    empty = bac_curve([DrinkEvent(0.0, 14.0, "d", "empty")], body, t_end=6.0)
    full = bac_curve([DrinkEvent(0.0, 14.0, "d", "full")], body, t_end=6.0)
    te, pe = peak_bac(*empty)
    tf, pf = peak_bac(*full)
    assert pe > pf, "empty stomach should peak higher"
    assert te < tf, "empty stomach should peak earlier"


def test_two_drinks_stack_higher_than_one():
    body = BodyParams.from_profile(PROFILE)
    one = bac_curve([DrinkEvent(0.0, 14.0, "d", "light")], body, t_end=6.0)
    two = bac_curve(
        [DrinkEvent(0.0, 14.0, "d1", "light"), DrinkEvent(0.5, 14.0, "d2", "light")],
        body, t_end=6.0,
    )
    assert peak_bac(*two)[1] > peak_bac(*one)[1]


# --------------------------------------------------------------------------
# Forecast wiring
# --------------------------------------------------------------------------
def test_forecast_reports_assumptions_and_window_time():
    body = BodyParams.from_profile(PROFILE)
    current = [DrinkEvent(0.0, 28.0, "negroni", "light")]
    candidate = DrinkEvent(1.0, 14.0, "beer", "light")  # t re-stamped to now inside
    fc = forecast(current, candidate, body,
                  window=(config.TARGET_LOW, config.TARGET_HIGH),
                  now_hours=1.0, horizon_hours=3.0)
    assert fc.projected_peak_bac > 0
    assert fc.assumptions["r"] == round(body.r, 4)
    assert fc.assumptions["hours_since_last_drink"] == 1.0
    assert fc.minutes_in_window >= 0
    assert fc.minutes_above_window >= 0


if __name__ == "__main__":
    # Lightweight runner so the file works without pytest installed.
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL  {name}: {e}")
    print(f"\n{'ALL PASSED' if not failures else f'{failures} FAILED'}")
    sys.exit(1 if failures else 0)
