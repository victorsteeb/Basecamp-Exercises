# Client Brief — Meridian Support Pilot

*One page. Fill every line. This is what Priya takes to her leadership.*

---

**Client & pilot**
Meridian — an AI agent that triages and resolves customer support tickets (a coordinator routing to billing / technical / account specialists). Live 3 weeks; closing tickets that aren't actually resolved.

**What's actually breaking it**
*(Name it plainly. Not the model — the system around it.)*

The coordinator was explicitly instructed to hand every ticket to exactly one specialist, even when a ticket raised more than one issue. On T-4471, the customer raised both an SSO/account problem and a billing problem. The coordinator picked one category (account), the account specialist fixed the SSO issue, and the coordinator then wrote back "resolved" — closing the ticket with the billing half never touched. That's why it "gives confidently wrong answers": the model was doing exactly what it was told, and what it was told was wrong.

**The fix**
*(What we changed, and where. Which prompt, which tool, which line.)*

Edited `system-prompt-coordinator.txt` only — no code, no tools, same model:
- Step 5 (DELEGATE): changed from "each ticket is owned by exactly ONE specialist ... do not spawn more than one" to calling `spawn_specialist` once for *every* distinct category the ticket touches.
- Step 6 (SYNTHESIZE): changed from writing up one specialist's findings to combining findings from all specialists spawned into a single customer reply before calling `write_response`.
- Classification guide: dropped the "one ticket, one specialist" routing rule so it no longer contradicts the new delegation step.

**Proof**
*(Before → after. Quality score moved from ____ to ____. Cost held at / dropped to $____ per run.)*

T-4471, 5 trials each, same model (claude-sonnet-5):
- Before: **0/5 resolved** ($0.1355/trial). Billing was never addressed (0/5) and the ticket was falsely marked resolved every time it wasn't.
- After: **4/5 resolved** ($0.1739/trial) — SSO and billing both handled, false-resolution and overclaim checks passing 4/5.
- Holdout (3 unseen tickets, 3 trials each, after the fix): **9/9 resolved** ($0.1707/trial average) — the fix generalized, it wasn't tuned to T-4471.

Cost per trial moved from ~$0.14 to ~$0.17 — a few cents more per ticket for tickets that now actually get fully resolved instead of quietly closed half-done.

**What it would take**
*(Rough scope, and the constraint to hit — e.g. stay within current per-ticket cost.)*

This was a one-file prompt change plus rerunning the existing eval suite — under a day of work, no new infrastructure. Going forward: keep the eval suite in place as a regression check any time the coordinator or specialist prompts change, and consider adding a few more multi-issue tickets to the holdout set so we keep catching this class of bug before it ships.

**The objection we'll get**
*("Why not just use a better model?" — answer it with the numbers above.)*

We tested that directly: same broken prompt on claude-opus-4-8 still resolved **0/5** — and cost roughly **2x more per trial** ($0.28 vs. $0.14) to fail the same way. The bigger model followed the same bad instruction just as faithfully as the smaller one. The problem was never model capability; it was an instruction telling the agent to close tickets it hadn't fully solved. Fixing that cost nothing in model spend and got us from 0% to 100% resolved on the held-out set.


