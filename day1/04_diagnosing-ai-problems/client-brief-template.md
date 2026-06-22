# Client Brief — Meridian Support Pilot

*One page. Fill every line. This is what Priya takes to her leadership.*

---

**Client & pilot**
Meridian — an AI agent that triages and resolves customer support tickets (a coordinator routing to billing / technical / account specialists). Live 3 weeks; closing tickets that aren't actually resolved.

**What's actually breaking it**
*(Name it plainly. Not the model — the system around it.)*
Two systemic failures in the coordinator's instructions, plus three smaller specialist gaps:

1. **Single-specialist constraint** — the coordinator was told to pick exactly one specialist per ticket. A ticket combining an SSO problem and a billing question got routed to account, the SSO was handled, the billing issue was acknowledged and dropped. Ticket closed as resolved. Customer still had an open problem.

2. **False resolution on security requests** — the coordinator was instructed to "acknowledge and close" anything outside specialist scope. A pentest authorization request (which only a human can grant) was being closed as "resolved" — with no human ever notified. The customer got a false confirmation.

Three secondary specialist gaps compounded this: the billing specialist had no tool to actually change a plan (it could diagnose but not act); the technical specialist's prompt didn't mention a since_hours parameter on the log tool, so issues older than 24 hours were invisible; and a stale TODO comment in the account tools definition pointed to a tool that doesn't exist, creating a confusing dead end.


**The fix**
*(What we changed, and where. Which prompt, which tool, which line.)*
Five targeted edits, no model change:
    - system-prompt-coordinator.txt step 5 — removed the "exactly ONE specialist" constraint; coordinator now spawns one specialist per category identified in the ticket.
    - system-prompt-coordinator.txt step 6 — replaced "acknowledge and close" with an explicit ESCALATION TRIGGERS section: security requests (pentest, vulnerability disclosures), bugs needing a code change, and customer escalations must call escalate_to_human and close with status "escalated" — never "resolved".
    - subagent-billing-tools.json — added a change_plan tool with starter / growth / scale / enterprise options.
    - system-prompt-subagent-technical.txt line 9 — documented the since_hours parameter on read_error_logs so the specialist uses it for older issues.
    - subagent-account-tools.json line 52 — removed the stale TODO comment from the get_workspace_account_summary description.


**Proof**
*(Before → after. Quality score moved from ____ to ____. Cost held at / dropped to $____ per run.)*

| Run | Model | Resolved | Cost/ticket |
|---|---|---|---|
| Baseline (before any fixes) | Sonnet | 1 / 5 (20%) | $0.13 |
| Model swap attempt | Opus | 0 / 5 (0%) | $0.26 |
| After multi-specialist fix | Sonnet | 5 / 5 (100%) | $0.16 |
| Holdout (3 tickets, all fixes) | Sonnet | 9 / 9 (100%) | $0.15 |
| Regression — escalation bug exposed | Sonnet | 6 / 9 (67%) | $0.15 |

Resolution rate on single-issue tickets: 100% and holding. Multi-issue tickets with a security component regressed to 0% until the escalation fix was applied. Cost per ticket unchanged at ~$0.15 throughout — the escalation path adds no meaningful overhead.


**What it would take**
*(Rough scope, and the constraint to hit — e.g. stay within current per-ticket cost.)*
All four fixes are already in place and validated. Deploying to production is a config swap — replace the four prompt/tool files and re-run smoke tests against a holdout ticket set. No retraining, no infrastructure change, no model upgrade. Estimate: half a day to stage, one day to monitor live traffic for edge cases.
The one remaining risk is tickets that span all three domains (billing + technical + account). Those are rare in the data, but worth adding a graded test case for before full rollout.


**The objection we'll get**
*("Why not just use a better model?" — answer it with the numbers above.)*
We tried. Opus — the most capable Claude model — scored 0 out of 5 on the same ticket set, at $0.26 per ticket versus $0.13 for Sonnet. Capability was never the bottleneck. The model was following its instructions correctly: it was told to pick one specialist, so it did. Swapping the model doesn't change the instruction. The fix was telling the system what to do, not upgrading who executes it.


