# Diagnosing AI Problems · Session Materials

## What you're doing
You've received an email from Priya, a client whose AI-powered customer support system is misbehaving. Using the agent artifacts in this folder, your job is to diagnose what went wrong — without running any code.

## Main learning
How to read and interpret the components of an agentic system: system prompts, tool definitions, and execution traces. You'll practice the real-world skill of diagnosing AI failures from artifacts alone, the same way you'd approach a client escalation.

## How to work this session

**Work in pairs or threes** — ideally with someone you don't usually work with. One person on the system prompts, one on the traces, one reconciling hypotheses. You'll cover more ground and catch more than working solo.

Two parts:

1. **Email only (10 min)** — Read the email. Form three hypotheses. Don't open any other file yet.
2. **Artifacts (20 min)** — Confirm or re-evaluate each hypothesis with evidence from the files below.

## What's in this folder

| File | What it is |
|------|-----------|
| `Priya_Email.pdf` | The client email describing the problem — start here |
| `system-prompt-coordinator.txt` | System prompt for the orchestrator agent |
| `system-prompt-subagent-account.txt` | System prompt for the account subagent |
| `system-prompt-subagent-billing.txt` | System prompt for the billing subagent |
| `system-prompt-subagent-technical.txt` | System prompt for the technical subagent |
| `coordinator-tools.json` | Tool schemas available to the coordinator |
| `subagent-account-tools.json` | Tool schemas for the account subagent |
| `subagent-billing-tools.json` | Tool schemas for the billing subagent |
| `subagent-technical-tools.json` | Tool schemas for the technical subagent |
| `trace-T-4471-coordinator.json` | Execution trace for the coordinator on ticket T-4471 |
| `trace-T-4471-subagent-account.json` | Execution trace for the account subagent on T-4471 |
| `diagnostic-framework.md` | One-page framework card to keep |

## No code to run
This is a read-and-diagnose exercise. Open the PDF first, then work through the system prompts and traces to identify the root cause.

## Ask Claude first

Before naming a root cause, paste into Claude and treat the response as a hypothesis to evaluate — not an answer to accept.

**During email-only diagnosis:**
> "Here's an email from a customer about a failing multi-agent support system. What are the most likely structural root causes? Give me three hypotheses, each with a specific thing to look for in the system artifacts."

**During artifact work:**
> "Here's a tool description from a coordinator agent: [paste]. Would a model know when to call this tool from this description alone? What's missing?"

Claude is a profiler, not an oracle. Use it to generate hypotheses, then decide if the reasoning holds up.

## Stretch goals

Work through these only after you've identified all three root causes, drafted fixes, and attempted the caching stretch from the presenter slides.

**Stretch 03 — Infographic for Priya**
Design a visual that explains what went wrong to Priya's non-technical stakeholders. Not a diagnosis document — something her account team could read in 60 seconds. What failed, where in the pipeline, and what the fix addresses.

**Stretch 04 — Observability Dashboard**
Design a dashboard that would give Priya early warning of these failure modes in the future. What metrics would it track? What would trigger an alert? What would the layout show? Spec it out — no code required.
