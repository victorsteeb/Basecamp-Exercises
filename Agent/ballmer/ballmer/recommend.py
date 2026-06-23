"""Recommendation layer: rank candidate next-drinks against the target window.

Scoring metric (chosen): DWELL + OVERSHOOT PENALTY.
    score = minutes_in_window  -  OVERSHOOT_PENALTY * minutes_above_window
Rewards a candidate that keeps the BAC curve inside the (joke) target band the
longest, while penalising any time spent ABOVE the band. The "hold / no drink"
option is always scored too — sometimes the best move is to wait and let
elimination carry you, rather than overshoot.

Safety (chosen): SOFT NUDGE. Past the configurable safety ceiling the agent
stops recommending alcohol and recommends the non-alcoholic option, but keeps
the monitoring loop alive to watch BAC decline. See reference/safety-policy.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import config
from .bac_model import BodyParams, DrinkEvent, ForecastResult, bac_at, forecast
from .drinks import Drink

# Status of the drinker relative to the target band / safety ceiling.
BELOW = "BELOW_WINDOW"
IN = "IN_WINDOW"
ABOVE = "ABOVE_WINDOW"
PAST_CEILING = "PAST_CEILING"

# Action the agent recommends.
ORDER = "ORDER"
HOLD = "HOLD"
NUDGE_NA = "NUDGE_NON_ALCOHOLIC"


def score_forecast(fc: ForecastResult,
                   window: tuple[float, float],
                   ceiling: float,
                   overshoot_penalty: float = config.OVERSHOOT_PENALTY) -> float:
    """Dwell-minus-overshoot, plus a continuous climb/brake gradient. Higher=better.

    See config.py for the full rationale. The shortfall term lets the agent climb
    the multi-drink staircase toward the band (since no single drink reaches it
    from a low base); the ceiling term makes crossing the safety ceiling
    strictly worse than any in-band option.
    """
    low, high = window
    shortfall = max(0.0, low - fc.projected_peak_bac)        # %BAC below the band
    over_ceiling = max(0.0, fc.projected_peak_bac - ceiling)  # %BAC above the ceiling
    return (fc.minutes_in_window
            - overshoot_penalty * fc.minutes_above_window
            - config.SHORTFALL_WEIGHT * shortfall
            - config.CEILING_WEIGHT * over_ceiling)


@dataclass
class Candidate:
    drink: Drink | None          # None == the "hold / no drink" option
    forecast: ForecastResult
    score: float


@dataclass
class Recommendation:
    status: str                  # BELOW / IN / ABOVE / PAST_CEILING
    action: str                  # ORDER / HOLD / NUDGE_NA
    current_bac: float
    drink: Drink | None
    forecast: ForecastResult | None
    message: str
    ranked: list[Candidate] = field(default_factory=list)


def _na_drink(library: list[Drink]) -> Drink | None:
    for d in library:
        if not d.is_alcoholic:
            return d
    return None


def recommend_next(events: list[DrinkEvent],
                   body: BodyParams,
                   library: list[Drink],
                   now_hours: float,
                   window: tuple[float, float] = (config.TARGET_LOW, config.TARGET_HIGH),
                   ceiling: float = config.SAFETY_CEILING,
                   food_state: str = config.DEFAULT_FOOD_STATE,
                   horizon_hours: float = 3.0) -> Recommendation:
    """Decide what (if anything) to order next.

    Pipeline: assess current BAC -> if past ceiling, soft-nudge; else forecast
    every alcoholic candidate + the hold option, rank by dwell+overshoot, and
    recommend the best (which may be HOLD).
    """
    low, high = window
    current = bac_at(events, body, now_hours)

    # ---- Safety ceiling: soft nudge -------------------------------------
    if current >= ceiling:
        na = _na_drink(library)
        return Recommendation(
            status=PAST_CEILING,
            action=NUDGE_NA,
            current_bac=current,
            drink=na,
            forecast=None,
            message=(
                f"You're at {current:.3f}% — past the safety ceiling "
                f"({ceiling:.3f}%). I'm not recommending more alcohol. "
                f"Have a {na.name if na else 'water'} and let it come down. "
                "I'll keep watching."
            ),
        )

    # ---- Forecast every candidate (alcoholic) + the HOLD option ----------
    candidates: list[Candidate] = []

    hold_fc = forecast(events, None, body, window, now_hours, horizon_hours)
    candidates.append(Candidate(drink=None, forecast=hold_fc,
                                score=score_forecast(hold_fc, window, ceiling)))

    for d in library:
        if not d.is_alcoholic:
            continue
        cand_event = DrinkEvent(t_hours=now_hours, grams=d.total_ethanol_g,
                                label=d.name, food_state=food_state)
        fc = forecast(events, cand_event, body, window, now_hours, horizon_hours)
        candidates.append(Candidate(drink=d, forecast=fc,
                                    score=score_forecast(fc, window, ceiling)))

    # Rank: best score first; tie-break toward higher dwell, then lower overshoot.
    candidates.sort(key=lambda c: (c.score, c.forecast.minutes_in_window,
                                   -c.forecast.minutes_above_window), reverse=True)
    best = candidates[0]

    # ---- Status + message ------------------------------------------------
    if low <= current <= high:
        status = IN
    elif current < low:
        status = BELOW
    else:
        status = ABOVE

    if best.drink is None:
        action = HOLD
        message = (
            f"You're at {current:.3f}% ({status.replace('_', ' ').lower()}). "
            f"Best move is to HOLD — any drink right now would overshoot the "
            f"{low:.3f}-{high:.3f}% band more than it helps. Let elimination work."
        )
    else:
        action = ORDER
        fc = best.forecast
        message = (
            f"You're at {current:.3f}% ({status.replace('_', ' ').lower()}). "
            f"Order a {best.drink.name} ({best.drink.standard_drinks:.1f} std drinks). "
            f"Projected peak {fc.projected_peak_bac:.3f}% at "
            f"+{fc.t_peak_hours - now_hours:.2f} h; ~{fc.minutes_in_window:.0f} min "
            f"in the target band, ~{fc.minutes_above_window:.0f} min above it."
        )

    return Recommendation(
        status=status, action=action, current_bac=current,
        drink=best.drink, forecast=best.forecast, message=message,
        ranked=candidates,
    )
