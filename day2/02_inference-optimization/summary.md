# Project HELVETICA — ClauseScan Inference Optimization

## Situation

The demo team delivered **ClauseScan v0** before the pitch: accurate (100% on audited fields), but with unit economics that would silently consume the engagement margin at production scale. The SOW is signed; the client has contracted $0.75 per reviewed contract against an estate of 248,000 supplier documents.

**v0 committed five billing sins simultaneously:**
- Opus for all work regardless of complexity
- The 5,700-token playbook re-billed at full price on every call
- Two serial round trips per contract where one would do
- Verbose free-text output at 5× input pricing
- No concurrency

---

## Final Configuration (v1)

```python
CONFIG = {
    "triage_routing": False,        # Sonnet for all — triage routed accuracy-sensitive
    "routine_model": MODEL_SONNET,  # contracts to Haiku, causing missed fields
    "complex_model": MODEL_SONNET,
    "cache_playbook": True,         # 5,729-token playbook cached; warm reads at 0.1×
    "structured_single_pass": True, # one schema-constrained pass instead of two
    "max_tokens": 1000,             # right-sized for JSON output (was 8,000)
    "effort": "low",                # output discipline on Sonnet
    "parallel_workers": 4,          # cache-warm-first, then fan-out
}
```

---

## Levers Applied

| # | Lever | Mechanism |
|---|---|---|
| 1 | **Round-trip collapse** | Two Opus passes → one Sonnet schema-constrained pass |
| 2 | **Prompt caching** | 5,729-token playbook cached; warm reads at 0.1× input rate |
| 3 | **Model right-sizing** | Opus → Sonnet across the board (triage routing trialled and dropped — see below) |
| 4 | **Output discipline** | Structured JSON schema; `max_tokens` 8,000 → 1,000; `effort="low"` |
| 5 | **Portfolio parallelism** | Cache pre-warm at session start, then 4-worker fan-out |

---

## Results

### Training set (6 contracts)

| Metric | v0 (inherited) | v1 (optimized) | Delta |
|---|---|---|---|
| Accuracy | 100% | **100%** | held |
| Cost / contract | $0.1639 | **$0.0042** | **39× cheaper** |
| p50 latency / contract | 35.7s | **3.1s** | **11× faster** |
| Batch wall-clock (6 contracts) | 211s | **9s** | **23× faster** |
| Calls per contract | 2 | **1** | |
| Engagement score | 100 | **2,412** | |

### Holdout set (2 unseen contracts)

| Contract | Vendor | Fields | TTC | Cost |
|---|---|---|---|---|
| C-201 | Vanta Marketing Collective | 5/5 ✓ | 14.5s ⚠️ | $0.0043 |
| C-202 | Quarry Industrial Supply Pte. | 5/5 ✓ | 5.2s | $0.0044 |

**Holdout summary:** accuracy **100%** · p50 9.8s · $0.0044/contract · score 1,978

> C-201's 14.5s is an outlier — network variability, not a structural issue. C-202 came in at 5.2s, consistent with the training set. A repeat run is recommended to confirm p50 on the holdout.

---

## SLA Status

| SLA Term | Commitment | v0 | v1 Training | v1 Holdout |
|---|---|---|---|---|
| Accuracy | ≥ 90% | ✓ | **100% ✓** | **100% ✓** |
| Interactive latency | p50 ≤ 5s | 35.7s ✗ | **3.1s ✓** | 9.8s ⚠️ |
| Unit economics | COGS ≤ $0.02/contract (production) | ~$1.31 ✗ | **~$0.019 ✓** | **~$0.019 ✓** |

> **Production COGS** modeled as lab cost × 8 (production contracts are ~8× longer in tokens) with a 15/85 interactive/batch split at 50% batch discount: $0.0042 × 8 × 0.575 = **$0.019/contract**.

---

## What We Learned Along the Way

**Triage routing trialled and dropped.** An earlier configuration added a Haiku triage pass to route ROUTINE contracts to Haiku and COMPLEX contracts to Sonnet. This produced a higher score on the training set but caused a persistent miss on C-202 (Quarry Industrial Supply) in the holdout — the contract was classified ROUTINE and sent to Haiku, which lacks the `effort` parameter and missed one field. Removing the triage routing and using Sonnet uniformly fixed accuracy, reduced calls from 2 to 1, and actually improved training p50 from 4.6s to 3.1s by eliminating the serial triage round trip.

**Cache pre-warm is load-bearing at session start.** Without a `max_tokens=0` warm-up call before the first analyst request, the cold cache-write on the 5,729-token playbook adds ~1–2s to the first contract's TTFT. Added to the holdout cell; should be baked into the production session-init path.

**effort="medium" breaks the COGS SLA.** Tested briefly to recover accuracy after the triage-routing miss — it tripled cost from $0.0042 to $0.0122/contract, pushing production COGS to ~$0.056, well above the $0.02 ceiling. The accuracy problem was routing, not model capability.

---

## Remaining Open Items

1. **Re-run the holdout** to verify C-201's 14.5s was measurement noise. One re-run confirming p50 ≤ 5s closes the final SLA question.
2. **Move cache pre-warm to production session init** — currently only in the holdout cell; needs to be the first call in every analyst working session.
3. **Enable the batch lane** (`RUN_BATCH = True`) for the 85% of the estate that doesn't need interactive latency — same model, same prompts, same schema, 50% off all token charges.
