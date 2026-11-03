# Client Brief — Meridian Support Pilot

*One page. Fill every line. This is what Priya takes to her leadership.*

---

**Client & pilot**
Meridian — an AI agent that triages and resolves customer support tickets (a coordinator routing to billing / technical / account specialists). Live 3 weeks; closing tickets that aren't actually resolved.

**What's actually breaking it**
*(Name it plainly. Not the model — the system around it.)*

The coordinator was instructed to route each ticket to exactly ONE specialist, even when customers raised multiple unrelated problems. When a ticket contained both an account issue (like SSO) and a billing issue (like a refund), only the account specialist saw it. The billing problem was completely ignored, but the agent falsely claimed it was handled in the customer response. This wasn't a model limitation — it was following bad instructions.


**The fix**
*(What we changed, and where. Which prompt, which tool, which line.)*

Changed one instruction in `system-prompt-coordinator.txt` (line 12). Removed the constraint that forced the coordinator to pick exactly one specialist per ticket. New instruction: "For each distinct problem category in the ticket, spawn a specialist for that category." Now when a ticket has both billing and account issues, both specialists see it and do their work independently. The coordinator synthesizes their findings into one coherent customer response.


**Proof**
*(Before → after. Quality score moved from ____ to ____. Cost held at / dropped to $____ per run.)*

**Before fix:** Ticket T-4471 resolved in 0/5 trials (0%) at $0.1315/trial. Billing issues never handled, false resolution claims on every run.

**After fix:** Same ticket resolved in 5/5 trials (100%) at $0.1863/trial. Both SSO and billing issues properly addressed every time.

**Generalization test:** Ran on 3 different tickets (including 2 the agent had never seen). Result: 9/9 trials resolved (100%). The fix holds across different problem combinations — account+billing, technical+billing, and single-issue tickets.

Cost increased 42% per trial ($0.1315 → $0.1863) because the agent now calls two specialists when needed instead of falsely claiming one handled everything.


**What it would take**
*(Rough scope, and the constraint to hit — e.g. stay within current per-ticket cost.)*

Already deployed in test environment. To ship to production: update one text file (`system-prompt-coordinator.txt`), redeploy the coordinator service (5-minute rollout), monitor resolution rates for 24 hours. No code changes, no model changes, no retraining required.

Trade-off: Cost per ticket increases by ~40% when multiple specialists are needed, but only on multi-issue tickets. Single-issue tickets (the majority) cost the same. The alternative — leaving tickets unresolved and customers angry — costs far more in retention and reputation.


**The objection we'll get**
*("Why not just use a better model?" — answer it with the numbers above.)*

"Why not just use a better model?"

Because the model was never the problem. The current model (claude-sonnet-5 at $0.003/1K input tokens) understood the tickets perfectly and had the capability to route to multiple specialists — it just wasn't allowed to. The instruction explicitly told it: "do not spawn more than one specialist." A more expensive model (claude-opus-4 at $0.015/1K — 5x the cost) would follow the same broken instruction and produce the same 0% resolution rate, just faster and at higher cost.

We fixed a $0 problem (bad instructions) by editing one line. Upgrading the model would have cost an extra ~$0.08/ticket while solving nothing. This is a system design issue, not a model capability issue.


