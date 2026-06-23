# Model Assumptions & Sources (the agent's "runbook")

Every physiological constant Ballmer uses, with its source and plausible range.
This is the analog of `runbooks/*.md` in the Always-On Ops exercise — the
reference the agent reasons against. The authoritative copy of these values
lives in `ballmer/config.py`; this doc explains the *why*.

## BAC model: Widmark + Watson + first-order absorption

**Core relation (units: A grams, W kg, r dimensionless, BAC in % = g/100mL):**

    BAC%_peak = A / (r * W_kg * 10)

Derivation in `ballmer/bac_model.py` module docstring.

### r-factor — Watson TBW with blood-water correction
- Watson PE, Watson ID, Batt RD. *Total body water volumes for adult males and
  females estimated from simple anthropometric measurements.* Am J Clin Nutr
  1980;33(1):27-39.
- Male TBW(L) = 2.447 − 0.09516·age + 0.1074·height_cm + 0.3362·weight_kg
- Female TBW(L) = −2.097 + 0.1069·height_cm + 0.2466·weight_kg
- **r = TBW / (0.806 · weight_kg).** The 0.806 is the water fraction of whole
  blood; Widmark's r is referenced to *blood*, Watson's TBW to *total body*
  water, so the conversion is required. A naive `r = TBW/weight` gives ~0.52 for
  the demo profile, which is too low and breaks the sanity anchors below.
- **Demo profile (73 in / 220 lb / 39 / M):** TBW ≈ 52.2 L, **r ≈ 0.649**
  (expected band 0.64–0.66). Below the flat Widmark 0.68 because a heavier person
  has proportionally more fat (less body water) — so a flat 0.68 would
  *underestimate* peak BAC here.

### Elimination β (zero-order)
- Default **0.015 %/hr**; population range **~0.012–0.020 %/hr**.
- Jones AW. *Evidence-based survey of the elimination rates of ethanol from
  blood.* Forensic Sci Int 2010. Midpoint chosen.
- Zero-order (constant-rate) is the defining Widmark approximation; true kinetics
  are saturable (Michaelis–Menten) but ~zero-order at relevant concentrations.

### Absorption k_a (first-order) — THE WEAKEST LINK
- **Absorption kinetics is the least reliable part of any Widmark-family model.**
- Modeled as first-order: absorbed_fraction(t) = 1 − exp(−k_a·(t−t_dose)).
- Default **k_a = 2.5 /hr** (t½ ≈ 17 min, Tmax ≈ 30–60 min). Range t½ 10–60 min
  ⇒ k_a ≈ 0.7–4.2 /hr. Order-of-magnitude consistent with controlled-dosing
  literature; treat as an approximation.
- **Food modifier** multiplies k_a: empty ×1.4, light ×1.0, full ×0.6 (food slows
  gastric emptying → slower, lower, broader peak). Coarse engineering values.

### Constants
- Ethanol density **0.789 g/mL** at 20 °C (CRC Handbook).
- US standard drink = **14 g** ethanol (NIAAA) — framing only, not used in engine.
- 1 fl oz = 29.5735 mL; 1 in = 2.54 cm; 1 lb = 0.45359237 kg.

## Sanity anchors (baked into tests/test_bac_model.py)
- One 14 g standard drink, demo profile, **before elimination** ⇒ ~0.0216% (the
  brief's "0.018–0.020%", a touch higher because r=0.649 < 0.68).
- The *realized* continuous-model peak of one drink is lower (~0.0085%) because
  β eliminates a large share of one small drink during the ~30 min it absorbs.
  This is why hitting the (absurd) 0.13% band requires many drinks close together.

## Known limitations
- First-order single-compartment absorption; no first-pass/bioavailability term.
- TBW→r blood-water correction is a simplification of a genuinely messy
  physiological relationship.
- Euler integration at 1-minute steps.
- **TODO: validate against published BAC time-course data.** "The demo runs" is
  NOT "the model is right." The faked tab proves the wiring, not the accuracy.
