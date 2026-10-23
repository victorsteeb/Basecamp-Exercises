"""Plain-code state machine: plan -> interview -> score -> audit -> (rescore | reinterview | escalate | pass).

Limits keep the loop from running forever or wearing the candidate out:
- at most MAX_SESSIONS interviews per candidate (main + one gap follow-up),
- at most MAX_RESCORES re-scores per session before a human takes over.
Whatever the outcome, the result is advisory and goes to a human reviewer.
"""

import json
import pathlib
import time

import agents
import llm
import report
from schemas import InterviewPlan

MAX_SESSIONS = 2
MAX_RESCORES = 1
WORDS_PER_MIN = 140  # spoken pace, used to advance the simulated clock


def run_session(plan: InterviewPlan, topics, minutes: int, candidate, turns: list[dict],
                session: int, max_turns: int, log) -> None:
    """Run one interview session, appending turns in place."""
    interviewer = agents.Interviewer(plan, topics, minutes, followup=session > 1)
    elapsed, said = 0.0, None
    for _ in range(max_turns):
        q = interviewer.turn(said, elapsed)
        turns.append({"turn": len(turns) + 1, "session": session, "speaker": "interviewer",
                      "text": q.say, "topic": q.current_topic_id, "note": q.private_note})
        log(f"  🤖 [{q.current_topic_id}] {q.say}")
        elapsed += len(q.say.split()) / WORDS_PER_MIN + 0.1
        if q.end_interview:
            return
        said = candidate.reply(q.say)
        turns.append({"turn": len(turns) + 1, "session": session, "speaker": "candidate", "text": said})
        log(f"  🧑 {said[:300]}{'…' if len(said) > 300 else ''}")
        elapsed += len(said.split()) / WORDS_PER_MIN + 0.3
    log(f"  ⏱  hit the {max_turns}-turn safety cap; ending session")
    turns.append({"turn": len(turns) + 1, "session": session, "speaker": "system",
                  "text": "Session ended by turn cap."})


def run(jd: pathlib.Path, resume: pathlib.Path, candidate_factory, minutes: int,
        max_turns: int, out_dir: pathlib.Path, log=print) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    def save(name: str, obj) -> None:
        data = obj.model_dump() if hasattr(obj, "model_dump") else obj
        (out_dir / name).write_text(json.dumps(data, indent=2, ensure_ascii=False))

    t0 = time.time()
    log("📋 Planning interview…")
    plan = agents.plan_interview(jd, resume, minutes)
    save("plan.json", plan)
    log(f"   role={plan.role_type} seniority={plan.seniority} topics={[t.id for t in plan.topics]}")
    if plan.injection_detected:
        log(f"   ⚠️  injection in inputs: {plan.injection_notes}")

    candidate = candidate_factory()
    turns: list[dict] = []
    log("🎙  Session 1")
    run_session(plan, plan.topics, minutes, candidate, turns, 1, max_turns, log)
    save("transcript.json", turns)

    sessions, rescores, version, feedback = 1, 0, 0, None
    history = []
    while True:
        version += 1
        log(f"🧮 Scoring (v{version})…")
        card = agents.score(plan, turns, feedback)
        quote_problems = agents.check_quotes(card, turns)
        save(f"scorecard_v{version}.json", card)
        log(f"   recommendation={card.recommendation}; quote problems={len(quote_problems)}")

        log(f"🔍 Auditing (v{version})…")
        result = agents.audit(plan, turns, card, quote_problems,
                              reinterview_allowed=sessions < MAX_SESSIONS)
        save(f"audit_v{version}.json", result)
        history.append({"version": version, "session_count": sessions, "verdict": result.verdict,
                        "quote_problems": quote_problems, "audit": result.model_dump()})
        log(f"   verdict={result.verdict}: {result.summary}")

        if result.verdict == "pass":
            status = "ready_for_human_review"
            break
        if result.verdict == "rescore":
            if rescores < MAX_RESCORES:
                rescores += 1
                feedback = result
                continue
            status = "escalated: scoring did not converge"
            break
        if result.verdict == "reinterview":
            if sessions < MAX_SESSIONS and result.followup_topics:
                sessions += 1
                rescores, feedback = 0, None
                follow_min = max(10, sum(t.minutes for t in result.followup_topics) + 4)
                log(f"🎙  Session {sessions} (follow-up, {follow_min} min): "
                    f"{[t.id for t in result.followup_topics]}")
                run_session(plan, result.followup_topics, follow_min, candidate, turns,
                            sessions, max_turns, log)
                save("transcript.json", turns)
                continue
            status = "escalated: coverage gaps after follow-up limit"
            break
        status = "escalated: auditor flagged issues for a human"
        break

    meta = {"status": status, "sessions": sessions, "score_versions": version,
            "models": {k: v[0] for k, v in llm.AGENTS.items()}, "usage": llm.USAGE,
            "seconds": round(time.time() - t0)}
    save("run.json", meta)
    (out_dir / "report.md").write_text(report.render(plan, turns, card, history, meta))
    (out_dir / "transcript.md").write_text(agents.render_transcript(turns))
    log(f"✅ {status}. Report: {out_dir / 'report.md'}")
    return meta
