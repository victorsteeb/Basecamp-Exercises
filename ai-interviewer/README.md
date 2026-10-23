# AI Interviewer (Data + AI) — milestone 1: the agent loop

Takes a job description and a resume, interviews the candidate, scores them on a fixed
rubric, then has a separate auditor check the interview and the scoring. Failed audits
loop back, within hard limits, and every outcome goes to a human for the decision.

This milestone runs the full loop with an **LLM-simulated candidate** (or you typing).
The video web app, the code sandbox and proctoring come in later milestones.

## Flow

```
JD + resume → Planner → Interviewer ⇄ candidate → Scorer → Auditor
                                                    ▲         │
                     rescore (max 1 per session) ───┘         │
   reinterview on gaps only (max 2 sessions total) ◀──────────┤
                        escalate / limits hit → human queue ◀─┤
                                   pass → report for a human ◀┘
```

| Agent | Sees | Produces |
|---|---|---|
| Planner (`agents.plan_interview`) | Raw JD + resume (text or PDF) | Plan: role type, must-haves, topics, **redacted** background, injection flag |
| Interviewer (`agents.Interviewer`) | Plan only, no name or protected attributes | One spoken turn at a time (`InterviewerTurn`) |
| Scorer (`agents.score`) | Plan + transcript, not the interviewer's private notes | `Scorecard`: 8 buckets, verbatim evidence, gates, claim checks |
| Quote check (`agents.check_quotes`) | Scorecard + transcript | Plain code: is every quote really in that candidate turn? |
| Auditor (`agents.audit`) | All of the above | `pass` / `rescore` / `reinterview` (+ gap topics) / `escalate` |
| Orchestrator (`orchestrator.py`) | Plain code, not an LLM | Enforces the limits, saves everything |

The weighted score is computed in code (`rubric.py`) from per-role weight templates,
not by an LLM.

## Run

From the repo root (uses `ANTHROPIC_API_KEY` from your environment or a `.env`):

```bash
python3 -m venv .venv && .venv/bin/pip install -r ai-interviewer/requirements.txt
.venv/bin/python ai-interviewer/run.py --persona strong
.venv/bin/python ai-interviewer/run.py --persona human --minutes 30        # you answer
.venv/bin/python ai-interviewer/run.py --jd jd.pdf --resume cv.pdf --persona average
```

Personas: `strong`, `average`, `weak`, `bluffer`, `injector`, `no_consent`, `human`.

Each run writes `ai-interviewer/runs/<timestamp>-<persona>/` (gitignored): `plan.json`,
`transcript.json/.md`, `scorecard_vN.json`, `audit_vN.json`, `run.json` and `report.md`.

Every agent defaults to `claude-opus-5-5`; override per agent with `PLANNER_MODEL`,
`INTERVIEWER_MODEL`, `SCORER_MODEL`, `AUDITOR_MODEL`, `CANDIDATE_MODEL`. Running the
auditor on a different model than the scorer reduces self-preference bias.

## Limits and safeguards

- Max 2 interview sessions per candidate; the second covers only the auditor's gap topics.
- Max 1 re-score per session; after that a human reviews it.
- The auditor escalates (never loops) on biased or illegal questions, a successful prompt
  injection, interviewer misconduct, or withdrawn consent.
- JD, resume and candidate speech are treated as data, never as instructions.
- The output is a recommendation for a human, never an automatic reject.

## Not built yet

2. Docker code sandbox (Python + DuckDB) and a `run_code` tool.
3. Local web app: webcam/mic recording, browser speech-to-text and text-to-speech, Monaco editor, consent screen.
4. Proctoring flags (second face, long look-aways, paste events): flags for a human only, never scored.
5. Reviewer page linking evidence quotes to video timestamps.
6. Golden-set evaluation across personas and adverse-impact checks.
