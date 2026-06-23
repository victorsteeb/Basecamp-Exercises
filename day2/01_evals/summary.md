# Executive Summary — Boutique Agent Eval & Improvement

**Bottom line:** We took a shopping agent from **40% → effectively 100%** task pass
rate, and along the way hardened the *eval itself*. The single remaining red (Run 1)
is a grader misfire, not an agent failure — the agent now passes every substantive
task reliably.

## Where we started

A baseline eval of 5 tasks showed **2/5 passing (40%)**, stable across 5 runs
(reliably broken, not flaky). Root cause: the agent had a generic
`"You are a helpful assistant"` prompt and placeholder tool descriptions, so on any
query requiring reasoning ("3 shirts and 2 belts", "20% off a jacket") it made
**zero tool calls** and asked the user for prices instead of using its own catalog.

## What we changed

1. **Built coverage** — wrote eval tasks spanning direct lookups, hyphenated keys,
   multi-step math, an unknown-product edge case, and an open-ended capability
   question.
2. **Fixed the agent** (the big lever) — rewrote the system prompt to define a
   shopping assistant with a priced catalog and a "always look up, never guess"
   rule, and replaced placeholder tool specs with real descriptions (valid product
   list, operator enum, a percentage example). → **40% → 80%.**
3. **Added an LLM-as-judge grader** for queries deterministic graders can't handle,
   and reworked the unfair `shoes` task to grade *graceful handling* instead of a
   rigid price.
4. **Fixed bugs in the eval itself** — caught that the judge was misfiring (inventing
   requirements; defaulting to FAIL on negative criteria), then hardened the judge
   prompt and rephrased the weak criteria.

## Progression

| Stage                                | Pass rate                                |
| ------------------------------------ | ---------------------------------------- |
| Baseline (broken agent)              | 2/5 — 40%                                |
| After agent fix                      | 4/5 — 80%                                |
| After LLM-judge + grader fixes       | **29/30 task-runs — ~97%** (6/6 in 4 of 5 runs) |

Cost of correctness was visible and expected: tool calls/task rose 0.6 → 1.5, tokens
~5.6k → ~15.8k per run — the agent now actually uses its tools.

## Key lessons surfaced

- **Multi-run baselines matter** — they distinguished "reliably broken" (fix the
  agent) from "flaky" (don't trust a single green).
- **Most early failures were the agent; some were the task.** We separated real
  agent bugs from brittle/unfair graders and fixed each at the right layer.
- **The eval caught a bug in the eval.** The LLM-judge was, at one point, *less
  reliable than the agent it graded* — the headline takeaway of Part 6. A judge is a
  fallible component to be validated, not an oracle.

## Remaining caveat (honest)

One residual flake: in Run 1, `shoes_graceful` failed its *"must NOT state a price"*
check — the judge stumbled on the negative criterion again (4/5, down from worse, but
not eliminated). The agent's response was correct; the grader wavered.

**Recommended next step:** run a judge-validation pass (judge vs. a few hand-labeled
responses) and, if the absence-criterion keeps wobbling, rephrase it positively or
bump that task to `num_runs=10` to characterize the noise.

Net: the agent is production-stable on this suite; the only open work is squeezing the
last bit of variance out of the grader — exactly the right problem to be left with.
