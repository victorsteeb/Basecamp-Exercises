# 🍸 Ballmer — an always-on agent for the (joke) Ballmer Peak

Ballmer sits with you at the bar, recomputes your blood-alcohol concentration as
the night goes on, and recommends what to order next to **reach and hold** the
XKCD #323 "Ballmer Peak" band. The framing is a comic gag; the engine underneath
is a real, auditable Widmark/Watson pharmacokinetic model.

> ## ⚠ Read this first
> The target band (**0.129%–0.138% BAC**) is a **joke from [XKCD #323](https://xkcd.com/323/)**.
> It is **far above every legal driving limit** and is **not** a health, safety,
> or performance recommendation. Real BAC in this range means serious impairment.
> Ballmer **refuses anything tied to driving or machinery** and stops recommending
> alcohol past a safety ceiling. This is a modeling demo, nothing more.

## Built on the "always-on" construct

This reuses the pattern from the Always-On Ops Agent exercise: a scheduled agent
that wakes on a tick, reads repo **state**, reasons against its **runbook/policy**,
and writes an **action**. The mapping:

| Always-On Ops | Ballmer |
|---|---|
| `issues/*.json` (live state) | `state/tab.json` — drinks consumed, timestamped |
| `deploys/recent.json` (what to act on) | `drink-library.json` — the menu |
| `runbooks/*.md` (reference) | `reference/model-assumptions.md` — constants + sources |
| `compliance-policy.md` (rules) | `reference/safety-policy.md` — band caveat, ceiling, no-driving |
| routine tick → triage issue | tick → recompute BAC → recommend next drink |
| agent comments on issue | agent writes to `state/log/` |

The v1 demo runs the tick loop over **fast-forwarded simulated time** (a whole
bar night in one hands-free run) — no cloud, no API key. A real cloud Routine
would call the same `tick()` on a wall-clock schedule.

## Run it

```bash
cd ballmer

# 1) Engine unit tests (hand-calculated Widmark/Watson checks)
python -m pytest -q          # or: python tests/test_bac_model.py

# 2) Hands-free terminal demo (the full flow + ASCII dashboard)
python run_demo.py
python run_demo.py --no-color --empty-stomach

# 3) Live LOCAL web dashboard  (standard library only — no pip installs)
python serve_dashboard.py            # opens http://127.0.0.1:8765
python serve_dashboard.py --speed 1.5 --port 9000
```

The web dashboard shows, live as the simulated night plays out: an **IN RANGE /
BELOW / ABOVE / PAST CEILING** indicator, current BAC, a gauge with the band and
ceiling marked, the BAC curve with the target band shaded and drink events
marked, and the **burndown** — a projected decline line + ETA for when you'd drop
out of the range with no further drinks. Everything is served from localhost.

## Architecture (model / data / interaction are separable)

```
ballmer/
├── ballmer/
│   ├── bac_model.py     # PURE engine: Widmark + Watson TBW + 1st-order absorption
│   ├── config.py        # every constant, with source + plausible range
│   ├── drinks.py        # recipe-level ethanol math + Drink/Ingredient model
│   ├── recommend.py     # dwell+overshoot scoring, safety soft-nudge
│   ├── agent.py         # always-on tick loop + state I/O + burndown
│   ├── dashboard.py     # zero-dep terminal dashboard
│   ├── web_data.py      # SessionRecord -> JSON frames (pure transform)
│   └── stubs.py         # clarifying-question STUBS (pour size, food, etc.)
├── state/               # the always-on state repo (profile, tab, target, log/)
├── reference/           # the agent's runbook + safety policy
├── web/dashboard.html   # vanilla-JS canvas UI (no external libraries)
├── drink-library.json   # the menu (~20 drinks, recipe-defined)
├── run_demo.py          # hands-free terminal demo
├── serve_dashboard.py   # stdlib http.server live web dashboard
└── tests/test_bac_model.py
```

The BAC engine is pure and unit-tested; swap it without touching the library or
UI. The drink library is just JSON — add a drink by appending one object.

## The model (see `reference/model-assumptions.md` for full sources)

- **Widmark** core: `BAC% = A / (r · W_kg · 10)`, A grams ethanol, β=0.015 %/hr
  zero-order elimination (range 0.012–0.020).
- **Watson (1980) TBW → r**, with the **blood-water correction**:
  `r = TBW / (0.806 · weight_kg)`. For the demo profile (73in/220lb/39/M) this
  gives r ≈ **0.649** (vs flat Widmark 0.68 → a heavier build has more fat, less
  water, so a higher peak). A naive `r = TBW/weight` gives ~0.52 and is wrong —
  see the note below.
- **First-order absorption** (k_a, default 2.5/hr, food-modified). Flagged as the
  weakest part of any Widmark-family model.
- **Scoring** (chosen): dwell minutes in-band − penalty·overshoot, plus a climb
  gradient so the agent can build the multi-drink staircase to the band.
- **Safety** (chosen): **soft nudge** past the ceiling — recommends a
  non-alcoholic option and keeps monitoring.

### Note: a deliberate deviation from the original spec
The brief specified `r = TBW_liters / weight_kg`, but that yields r ≈ 0.52 for the
demo profile — which **contradicts the brief's own stated anchors** (it expected
r ≈ 0.64–0.66 and a ~0.02% peak for one drink). Both anchors require the
blood-water correction `r = TBW / (0.806·weight_kg)` (Widmark's r is referenced
to blood; blood is ~80.6% water). We implemented the corrected form so the model
hits the brief's numbers; the rationale is documented in `config.py` and
`bac_model.py`.

> **`# TODO: validate against published BAC time-course data.`** "The demo runs"
> is not "the model is right." The faked tab proves the wiring, not the accuracy.
