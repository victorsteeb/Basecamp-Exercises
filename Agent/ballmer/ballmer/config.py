"""Physiological constants, unit conversions, and tunable model parameters.

EVERY constant here carries its source and a plausible range. Where the
literature gives a range, we use a defensible midpoint and say so. Nothing in
this file is fabricated; where a value is an engineering choice rather than a
measured constant (e.g. the safety ceiling, the overshoot penalty), that is
called out explicitly.

# TODO: validate the *whole* model against published BAC time-course data
# (e.g. controlled-dosing studies). The demo proves the wiring is correct, NOT
# that the predictions are accurate. A Widmark-family model is an approximation.
"""

# --------------------------------------------------------------------------
# Unit conversions (the easy thing to get wrong — so they live in one place)
# --------------------------------------------------------------------------
LB_TO_KG = 0.45359237      # exact, international avoirdupois pound
IN_TO_CM = 2.54            # exact, international inch
ETHANOL_DENSITY_G_PER_ML = 0.789  # g/mL at 20 °C (CRC Handbook of Chemistry & Physics)
OZ_TO_ML = 29.5735         # US fluid ounce -> mL

# Water fraction of whole blood, by weight (~80%). Widmark's BAC is a *blood*
# concentration, but Watson's TBW is *total body* water — so converting TBW to a
# Widmark r requires dividing by the blood water fraction (see config.py note on
# FLAT_WIDMARK_R and bac_model.widmark_r for the full derivation). Value 0.806 is
# the classically cited whole-blood water content (Widmark; widely reproduced).
BLOOD_WATER_FRACTION = 0.806

# --------------------------------------------------------------------------
# Reference quantities
# --------------------------------------------------------------------------
# US "standard drink" = 14 g pure ethanol (NIAAA, US Dept. of Health). Used only
# for sanity checks and human-readable framing, never inside the engine.
STANDARD_DRINK_G = 14.0

# --------------------------------------------------------------------------
# Widmark elimination rate (zero-order)
# --------------------------------------------------------------------------
# Ethanol elimination is saturable (Michaelis-Menten) but is well-approximated
# as ZERO-ORDER (constant rate) at the concentrations relevant here — this is
# the defining feature of the Widmark model.
#   Default 0.015 %/hr. Population range ~0.012-0.020 %/hr.
#   Source: Jones AW, "Evidence-based survey of the elimination rates of ethanol
#   from blood", Forensic Sci Int 2010. Midpoint chosen.
WIDMARK_BETA_DEFAULT = 0.015   # %BAC per hour
WIDMARK_BETA_RANGE = (0.012, 0.020)

# --------------------------------------------------------------------------
# First-order absorption rate constant k_a
# --------------------------------------------------------------------------
# ABSORPTION KINETICS IS THE WEAKEST PART OF ANY WIDMARK-FAMILY MODEL.
# We model each drink as absorbing into blood with first-order rate k_a (1/hr):
#   absorbed_fraction(t) = 1 - exp(-k_a * (t - t_dose))
# k_a relates to absorption half-life by t_half = ln(2) / k_a.
#   Default k_a = 2.5 /hr  -> t_half ~ 0.28 hr (~17 min), Tmax ~ 30-60 min.
#   Plausible range: t_half 10-60 min  -> k_a ~ 0.7-4.2 /hr.
#   These are order-of-magnitude consistent with controlled-dosing literature;
#   treat as an approximation, not a measured personal constant.
K_A_BASE = 2.5             # 1/hr
K_A_RANGE = (0.7, 4.2)

# Food / stomach-contents modifier — MULTIPLIES k_a. Food slows gastric
# emptying, so ethanol reaches the small intestine (where most absorption
# happens) more slowly -> lower k_a -> lower, later, broader peak.
# These multipliers are coarse engineering approximations, NOT measured values.
FOOD_FACTORS = {
    "empty": 1.4,   # empty stomach -> faster absorption
    "light": 1.0,   # a snack -> baseline
    "full":  0.6,   # full meal -> markedly slower
}
DEFAULT_FOOD_STATE = "light"

# --------------------------------------------------------------------------
# Watson total-body-water equations (1980)
# --------------------------------------------------------------------------
# Source: Watson PE, Watson ID, Batt RD. "Total body water volumes for adult
# males and females estimated from simple anthropometric measurements."
# Am J Clin Nutr 1980;33(1):27-39. Inputs: age (yr), height (cm), weight (kg).
# Output: TBW in LITRES. (Coefficients are embedded in bac_model.watson_tbw_liters.)
#
# We derive the Widmark r-factor from TBW. The naive form r = TBW/weight is
# DELIBERATELY NOT USED: it yields ~0.52 for the demo profile, which is both
# physiologically off and inconsistent with the well-established Widmark range.
# Widmark's r is referenced to *blood* alcohol, and blood is ~80.6% water, so:
#       r = TBW_litres / (BLOOD_WATER_FRACTION * weight_kg)
# This gives r ~ 0.65 for the demo profile (heavy 39yo male) — exactly the
# expected 0.64-0.66 band — and makes a single 14 g standard drink peak at
# ~0.02% as expected. (Derivation in bac_model.widmark_r.)
#
# Using Watson TBW (rather than a flat r) adapts to body composition: a heavier
# individual carries proportionally more fat (which holds little water), lowering
# r and therefore RAISING peak BAC for a given dose. A flat 0.68 underestimates
# that peak for this profile.
FLAT_WIDMARK_R = {"male": 0.68, "female": 0.55}  # for comparison / fallback only

# --------------------------------------------------------------------------
# Target window (THE JOKE) + safety
# --------------------------------------------------------------------------
# XKCD #323 "Ballmer Peak": programmers code best at 0.129%-0.138% BAC.
# THIS IS A COMIC-STRIP GAG. It is far above every legal driving limit
# (e.g. 0.08% US, 0.05% many countries) and is not a health recommendation.
TARGET_LOW = 0.129     # %BAC
TARGET_HIGH = 0.138    # %BAC

# Safety ceiling: an ENGINEERING CHOICE, not a medical threshold. Above this the
# agent stops recommending alcohol (soft-nudge mode — see recommend.py /
# safety-policy.md). Set just above the (already absurd) target band.
SAFETY_CEILING = 0.15  # %BAC

# Scoring: dwell minutes in-window MINUS this penalty * minutes spent ABOVE the
# window. Engineering choice; tune to taste. Higher = more overshoot-averse.
OVERSHOOT_PENALTY = 2.0

# The chosen dwell+overshoot metric is MYOPIC (one drink ahead): from a low base
# no single drink reaches the ~0.13% band, so every candidate would tie at
# dwell=0 and the agent would HOLD forever, never climbing the staircase. We add
# a continuous gradient so the agent climbs when below the band and brakes near
# the top. Score (minutes for dwell/overshoot; %BAC for shortfall/ceiling):
#   score = dwell_min
#         - OVERSHOOT_PENALTY * overshoot_min
#         - SHORTFALL_WEIGHT  * max(0, target_low - projected_peak)   # climb toward band
#         - CEILING_WEIGHT    * max(0, projected_peak - safety_ceiling) # never blow past
# Weights are engineering choices: SHORTFALL pulls the projected peak up toward
# the band from below; CEILING dominates everything so a drink that would cross
# the ceiling is never chosen.
SHORTFALL_WEIGHT = 5000.0    # penalty per %BAC the projected peak falls short of the band
CEILING_WEIGHT = 100000.0    # penalty per %BAC the projected peak exceeds the ceiling

# --------------------------------------------------------------------------
# Numerical integration
# --------------------------------------------------------------------------
SIM_DT_HOURS = 1.0 / 60.0   # 1-minute integration step for the BAC ODE
