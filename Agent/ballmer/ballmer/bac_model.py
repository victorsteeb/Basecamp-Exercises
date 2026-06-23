"""The BAC forecasting engine — PURE functions, no I/O, fully unit-testable.

This module is the heart of Ballmer and is deliberately isolated from the drink
library and the agent/interaction layer, so the engine can be swapped or
validated independently.

UNITS CONVENTION (read this before touching anything):
    A   grams of pure ethanol
    W   body weight in KILOGRAMS
    r   Widmark factor, DIMENSIONLESS  (= TBW_litres / weight_kg here)
    t   time in HOURS
    BAC reported as PERCENT, i.e. g ethanol / 100 mL blood  (US "%" — 0.08% = legal limit)
    beta  elimination rate in %BAC per hour
    k_a   first-order absorption rate constant, 1/hour

CORE WIDMARK RELATION (derivation):
    Ethanol distributes into a volume Vd = r * W_kg litres (~kg of body water).
    Concentration once fully absorbed, no elimination:
        C = A / (r * W_kg)            [grams / litre of distribution volume]
    Convert g/L -> g/100mL (i.e. "%"): divide by 10.
        BAC%_peak = A / (r * W_kg * 10)
    Worked check: 14 g, r=0.65, W=99.8 kg ->
        14 / (0.65 * 99.8 * 10) = 14 / 648.7 = 0.0216 %   (one std drink, heavy male)
    With absorption spread over time AND simultaneous elimination, the *realised*
    peak is a touch lower (~0.018-0.021%), matching expectation.

r-FACTOR — IMPORTANT DERIVATION (and a deliberate deviation from a naive formula):
    Widmark's BAC is a *blood* concentration. Watson's equation gives *total body*
    water (TBW). Alcohol distributes through body water, so:
        amount A = C_water * TBW
    but BAC is measured in blood, and blood is ~80.6% water by weight, so
        C_blood = C_water * BLOOD_WATER_FRACTION
    Combining with Widmark's C_blood = A / (r * W):
        r = TBW / (BLOOD_WATER_FRACTION * W)
    The naive r = TBW/W (omitting the blood-water term) gives ~0.52 for the demo
    profile, which is too low and inconsistent with the established Widmark range.
    The corrected form gives r ~ 0.65 (expected band 0.64-0.66) and makes a single
    14 g standard drink peak at ~0.02% — matching the model's sanity anchors.
    This is an approximation, not ground truth, but it is the defensible choice.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import config


# ==========================================================================
# Body-water / r-factor  (Watson 1980)
# ==========================================================================
def watson_tbw_liters(sex: str, age: float, height_cm: float, weight_kg: float) -> float:
    """Total body water in LITRES via the Watson (1980) anthropometric equations.

    Male:   TBW = 2.447 - 0.09516*age + 0.1074*height_cm + 0.3362*weight_kg
    Female: TBW = -2.097          + 0.1069*height_cm + 0.2466*weight_kg
            (note: the female equation has NO age term and a negative constant)
    Source: Watson PE, Watson ID, Batt RD, Am J Clin Nutr 1980;33(1):27-39.
    """
    sex = sex.lower()
    if sex == "male":
        return 2.447 - 0.09516 * age + 0.1074 * height_cm + 0.3362 * weight_kg
    elif sex == "female":
        return -2.097 + 0.1069 * height_cm + 0.2466 * weight_kg
    raise ValueError(f"sex must be 'male' or 'female', got {sex!r}")


def widmark_r(tbw_liters: float, weight_kg: float) -> float:
    """Widmark r-factor from Watson TBW, with the blood-water correction.

        r = TBW_litres / (BLOOD_WATER_FRACTION * weight_kg)

    See the module docstring for the full derivation. The blood-water term
    (~0.806) is what converts a *total body water* volume into the *blood*-
    referenced distribution ratio Widmark's equation expects. Lower r (more fat)
    -> higher peak BAC for a given dose.
    """
    return tbw_liters / (config.BLOOD_WATER_FRACTION * weight_kg)


def r_from_profile(profile: dict) -> float:
    """Compute r from a human-friendly profile (imperial units in, SI conversions here).

    profile keys: height_in, weight_lb, age, sex.
    All unit conversions are done HERE and commented, since that is the classic
    source of a 2x BAC error.
    """
    height_cm = profile["height_in"] * config.IN_TO_CM      # inches -> cm
    weight_kg = profile["weight_lb"] * config.LB_TO_KG       # pounds -> kg
    tbw = watson_tbw_liters(profile["sex"], profile["age"], height_cm, weight_kg)
    return widmark_r(tbw, weight_kg)


def weight_kg_from_profile(profile: dict) -> float:
    return profile["weight_lb"] * config.LB_TO_KG


# ==========================================================================
# Ethanol mass from a recipe
# ==========================================================================
def ethanol_grams(volume_ml: float, abv: float) -> float:
    """Grams of pure ethanol in a liquid volume.

    grams = volume_ml * abv * density_ethanol
    abv is a FRACTION (0.40 for 40% / 80-proof), not a percentage.
    Worked check: 44 mL of 40% spirit -> 44 * 0.40 * 0.789 = 13.9 g (~1 std drink).
    """
    return volume_ml * abv * config.ETHANOL_DENSITY_G_PER_ML


# ==========================================================================
# Drink events + the body parameters bundle
# ==========================================================================
@dataclass(frozen=True)
class DrinkEvent:
    """A dose of ethanol entering the body at a point in time.

    t_hours : hours since the start of the session (session-relative clock).
    grams   : grams of pure ethanol in the drink.
    label   : human-readable name (for logs/plots).
    food_state : stomach contents at the time of THIS drink ('empty'|'light'|'full').
                 Modifies this drink's absorption rate only.
    """
    t_hours: float
    grams: float
    label: str = "drink"
    food_state: str = config.DEFAULT_FOOD_STATE


@dataclass(frozen=True)
class BodyParams:
    """The per-person constants the engine needs. Build once from a profile."""
    r: float
    weight_kg: float
    beta: float = config.WIDMARK_BETA_DEFAULT       # %BAC/hr elimination
    k_a_base: float = config.K_A_BASE               # 1/hr absorption

    @classmethod
    def from_profile(cls, profile: dict, beta: float | None = None,
                     k_a_base: float | None = None) -> "BodyParams":
        return cls(
            r=r_from_profile(profile),
            weight_kg=weight_kg_from_profile(profile),
            beta=config.WIDMARK_BETA_DEFAULT if beta is None else beta,
            k_a_base=config.K_A_BASE if k_a_base is None else k_a_base,
        )


def _peak_contribution(grams: float, body: BodyParams) -> float:
    """Full-absorption, no-elimination BAC contribution of a dose (the Widmark peak)."""
    # BAC% = A / (r * W_kg * 10)   — see module docstring derivation.
    return grams / (body.r * body.weight_kg * 10.0)


# ==========================================================================
# The time-course: first-order absorption + zero-order elimination
# ==========================================================================
# We integrate the ODE numerically because there is NO clean closed form when
# first-order absorption is combined with zero-order elimination that switches
# off at BAC = 0. Euler at 1-minute steps is transparent and accurate enough.
#
#   dBAC/dt = absorption_input_rate(t) - elimination_rate(t)
#
#   absorption_input_rate(t) = sum over drinks dosed at t_i <= t of:
#       peak_contribution_i * k_a_i * exp(-k_a_i * (t - t_i))            [%BAC/hr]
#     (this is d/dt of  peak_i * (1 - exp(-k_a_i*(t-t_i))); it integrates to the
#      full Widmark peak as t->inf, i.e. absorption only SPREADS the dose in time)
#
#   elimination_rate(t) = beta   while BAC > 0,   else 0                 [%BAC/hr]

def _absorption_rate(events: list[DrinkEvent], body: BodyParams, t: float) -> float:
    """Instantaneous rate at which ethanol is being delivered to blood, in %BAC/hr."""
    rate = 0.0
    for ev in events:
        if t < ev.t_hours:
            continue
        k_a = body.k_a_base * config.FOOD_FACTORS.get(ev.food_state, 1.0)
        dt = t - ev.t_hours
        rate += _peak_contribution(ev.grams, body) * k_a * math.exp(-k_a * dt)
    return rate


def bac_curve(events: list[DrinkEvent], body: BodyParams, t_end: float,
              t_start: float = 0.0, dt: float = config.SIM_DT_HOURS
              ) -> tuple[list[float], list[float]]:
    """Integrate the BAC-vs-time curve.

    Returns (times, bac) where times are hours (session-relative) on a grid of
    step `dt` and bac is %BAC at each grid point. BAC is clamped at >= 0; within
    a step, elimination cannot drive BAC below zero.
    """
    if t_end <= t_start:
        return [t_start], [0.0]

    n = int(round((t_end - t_start) / dt)) + 1
    times: list[float] = []
    bac_series: list[float] = []

    bac = 0.0
    # Account for any doses strictly before t_start by warming up from 0.
    # Simplest correct approach: always start the integration at 0 (true zero
    # BAC at t=0 by construction) and integrate forward to t_start, then record.
    warmup_start = min(t_start, min((e.t_hours for e in events), default=t_start))
    t = warmup_start
    record_from = t_start
    while t < t_end - 1e-12:
        absorb = _absorption_rate(events, body, t)
        eliminate = body.beta if bac > 0.0 else 0.0
        # Euler step; clamp elimination so BAC can't cross zero mid-step.
        delta = (absorb - eliminate) * dt
        bac = max(0.0, bac + delta)
        t += dt
        if t >= record_from - 1e-12:
            times.append(t)
            bac_series.append(bac)
        if len(times) >= n + 2:  # safety bound
            break

    if not times:  # degenerate (t_end ~ t_start)
        times = [t_start]
        bac_series = [max(0.0, bac)]
    return times, bac_series


# ==========================================================================
# Curve summaries
# ==========================================================================
def bac_at(events: list[DrinkEvent], body: BodyParams, t: float,
           dt: float = config.SIM_DT_HOURS) -> float:
    """BAC% at a single instant `t` (hours). Integrates from 0 to t."""
    if t <= 0:
        return 0.0
    _, bac = bac_curve(events, body, t_end=t, t_start=0.0, dt=dt)
    return bac[-1] if bac else 0.0


def peak_bac(times: list[float], bac: list[float]) -> tuple[float, float]:
    """Return (t_peak_hours, peak_bac%)."""
    i = max(range(len(bac)), key=lambda j: bac[j])
    return times[i], bac[i]


def time_in_window(times: list[float], bac: list[float],
                   low: float, high: float, dt: float = config.SIM_DT_HOURS) -> float:
    """Hours the curve spends inside [low, high] (inclusive)."""
    return sum(dt for v in bac if low <= v <= high)


def time_above(times: list[float], bac: list[float], high: float,
               dt: float = config.SIM_DT_HOURS) -> float:
    """Hours the curve spends strictly ABOVE `high` (overshoot)."""
    return sum(dt for v in bac if v > high)


# ==========================================================================
# Forecast: current state + a candidate next drink
# ==========================================================================
@dataclass
class ForecastResult:
    """Everything the recommendation layer and the demo need to print."""
    candidate_label: str
    candidate_grams: float
    projected_peak_bac: float
    t_peak_hours: float           # session-relative
    minutes_in_window: float
    minutes_above_window: float
    curve_times: list[float] = field(default_factory=list)
    curve_bac: list[float] = field(default_factory=list)
    assumptions: dict = field(default_factory=dict)


def forecast(current_events: list[DrinkEvent],
             candidate: DrinkEvent | None,
             body: BodyParams,
             window: tuple[float, float],
             now_hours: float,
             horizon_hours: float = 3.0,
             dt: float = config.SIM_DT_HOURS) -> ForecastResult:
    """Project the BAC curve forward over `horizon_hours` assuming `candidate` is
    consumed at `now_hours`. Pass candidate=None to forecast the do-nothing path.

    Returns peak BAC, dwell time in the target window, overshoot time, the curve,
    and the full assumption set used (so every recommendation is auditable).
    """
    low, high = window
    events = list(current_events)
    if candidate is not None:
        # re-stamp the candidate to be consumed *now*
        events.append(DrinkEvent(t_hours=now_hours, grams=candidate.grams,
                                 label=candidate.label, food_state=candidate.food_state))

    t_end = now_hours + horizon_hours
    times, bac = bac_curve(events, body, t_end=t_end, t_start=now_hours, dt=dt)
    t_peak, peak = peak_bac(times, bac)
    mins_in = time_in_window(times, bac, low, high, dt) * 60.0
    mins_above = time_above(times, bac, high, dt) * 60.0

    last_drink_t = max((e.t_hours for e in current_events), default=None)
    assumptions = {
        "r": round(body.r, 4),
        "weight_kg": round(body.weight_kg, 2),
        "beta_pct_per_hr": body.beta,
        "k_a_base_per_hr": body.k_a_base,
        "food_state_of_candidate": candidate.food_state if candidate else None,
        "effective_k_a_of_candidate": (
            round(body.k_a_base * config.FOOD_FACTORS.get(candidate.food_state, 1.0), 3)
            if candidate else None
        ),
        "now_hours": round(now_hours, 3),
        "hours_since_last_drink": (round(now_hours - last_drink_t, 3)
                                   if last_drink_t is not None else None),
        "horizon_hours": horizon_hours,
        "target_window_pct": [low, high],
    }
    return ForecastResult(
        candidate_label=candidate.label if candidate else "NO DRINK (hold)",
        candidate_grams=candidate.grams if candidate else 0.0,
        projected_peak_bac=peak,
        t_peak_hours=t_peak,
        minutes_in_window=mins_in,
        minutes_above_window=mins_above,
        curve_times=times,
        curve_bac=bac,
        assumptions=assumptions,
    )
