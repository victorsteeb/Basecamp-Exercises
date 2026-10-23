"""Human-reviewer report (markdown). Weighted totals are computed here, not by an LLM."""

import rubric
from schemas import InterviewPlan, Scorecard


def render(plan: InterviewPlan, turns: list[dict], card: Scorecard, history: list[dict], meta: dict) -> str:
    scored = {b.bucket: b.score for b in card.buckets if b.status == "scored"}
    overall = rubric.weighted_score(plan.role_type, scored)
    coverage = rubric.weight_coverage(plan.role_type, set(scored))
    weights = rubric.ROLE_WEIGHTS[plan.role_type]

    out = [
        "# Interview report (advisory: a human makes the decision)",
        "",
        f"**Status:** {meta['status']}  ",
        f"**Role:** {plan.role_type} ({plan.seniority})  ",
        f"**Recommendation:** {card.recommendation}  ",
        f"**Weighted score:** {overall if overall is not None else 'n/a'} / 5 "
        f"over {coverage}% of the role's weight  ",
        f"**Sessions:** {meta['sessions']} · **Score versions:** {meta['score_versions']}",
        "",
        card.summary,
        "",
        "## Buckets",
        "",
        "| Bucket | Weight | Score | Rationale |",
        "|---|---|---|---|",
    ]
    for b in card.buckets:
        s = str(b.score) if b.status == "scored" else "not assessed"
        out.append(f"| {b.bucket} | {weights[b.bucket]}% | {s} | {' '.join(b.rationale.replace('|', '/').split())} |")

    out += ["", "## Must-have gates", ""]
    out += [f"- **{g.skill}**: {g.met} ({g.rationale})" for g in card.must_have_gates]
    out += ["", "## Resume claims", ""]
    out += [f"- {c.claim}: **{c.result}** ({c.note})" for c in card.resume_claims]
    out += ["", "## Strengths", ""] + [f"- {s}" for s in card.strengths]
    out += ["", "## Concerns", ""] + [f"- {c}" for c in card.concerns]

    out += ["", "## Evidence", ""]
    for b in card.buckets:
        for e in b.evidence:
            out.append(f"- *{b.bucket}* (turn {e.turn}): \"{e.quote}\"")

    out += ["", "## Audit trail", ""]
    for h in history:
        out.append(f"### Score v{h['version']} → {h['verdict']}")
        out.append(h["audit"]["summary"])
        for i in h["audit"]["issues"]:
            out.append(f"- [{i['severity']}] {i['category']} → {i['fix_route']}: {i['description']}")
        for p in h["quote_problems"]:
            out.append(f"- quote check: {p}")
        out.append("")

    if plan.injection_detected:
        out += ["## ⚠️ Input injection detected", "", plan.injection_notes, ""]

    u = meta["usage"]
    out += ["## Run", "",
            f"Models: {meta['models']}  ",
            f"Calls: {u['calls']} · input tokens: {u['input_tokens']:,} · output tokens: "
            f"{u['output_tokens']:,} · {meta['seconds']}s"]
    return "\n".join(out) + "\n"
