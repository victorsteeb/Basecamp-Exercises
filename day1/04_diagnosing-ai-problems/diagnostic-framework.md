# The Diagnostic Loop

A repeatable framework for diagnosing any AI system failure — from a single broken prompt to a fifty-agent pipeline.

---

## Step 1 — Symptom
**What the customer reports, in their words.**

Don't reframe it yet. Don't add your interpretation. Write down exactly what they said is wrong, as they said it.

*In Meridian:* Priya's email — agent gave the wrong answer, didn't escalate, didn't use available data.

---

## Step 2 — Hypothesis
**What you suspect before seeing any internals.**

Force at least three hypotheses from the symptom alone. Don't jump to the artifacts. Naming hypotheses before you look commits you to a position — and teaches you where your diagnostic reflexes are strong or weak.

Common structural hypotheses:
- Routing / classification failure
- Tool description too vague to use reliably
- Missing or wrong escalation path
- Sub-agent over-claiming resolution
- Context not reaching the model that needs it
- Cache placement breaking shared prompt regions

*In Meridian:* routing (single-dispatch coordinator), opaque tool name (`fetch_customer_v2_databricks`), sub-agent over-claiming.

---

## Step 3 — Evidence
**What the artifacts confirm or rule out.**

For any agentic system, the first three things to ask for:
1. **System prompts** — what is the agent trying to do?
2. **Tool descriptions** — what can the model see and when would it use each tool?
3. **Execution traces** — what actually happened, step by step?

Read each artifact against your hypotheses. Point to the specific line that confirms or rules out each one. "The prompt seems off" is not evidence — "line 14 says pick one category even if two apply" is.

*In Meridian:* coordinator prompt line ("pick the one the customer seems most blocked by"), tool description with no trigger language, trace showing sub-agent claiming resolution without calling any resolution tool.

---

## Step 4 — Recommendation
**A fix scoped to the actual root cause.**

Not "improve the prompt." Scoped: which prompt, which line, what change, and why it would prevent the specific failure you just diagnosed.

If you can't write a recommendation that references the exact artifact and line, go back to Step 3.

*In Meridian:* rewrite classifier to support multi-route dispatch, rename tool with trigger language ("use this when a customer reports rate limiting or usage anomalies"), add verification requirement to sub-agent prompt before reporting resolution.

---

## Quick reference

| Step | Question | Output |
|------|----------|--------|
| Symptom | What is the customer actually reporting? | Plain-English problem statement |
| Hypothesis | What could cause this? (3 minimum, before artifacts) | Ranked hypothesis list |
| Evidence | Which hypothesis does each artifact confirm or rule out? | Line-cited evidence per hypothesis |
| Recommendation | What change, in which file, prevents this failure? | Scoped fix per root cause |

---

*Diagnosing AI Problems · Partner Basecamp Day 1*
