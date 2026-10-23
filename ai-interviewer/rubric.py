"""Score buckets, anchored scale and per-role weights.

Weights are fixed templates per role type (not invented per JD) so two candidates
for the same role are always scored on the same scale.
"""

BUCKETS = {
    "sql_data_modeling": "SQL & data modeling: joins, window functions, schema design, normalization vs. denormalization, query performance.",
    "stats_experimentation": "Statistics & experimentation: distributions, hypothesis testing, A/B test design, power, causal pitfalls.",
    "ml_fundamentals": "ML fundamentals: bias/variance, feature engineering, model selection, metrics, leakage, validation strategy.",
    "data_engineering": "Data engineering: batch/stream pipelines, Spark, orchestration, data quality, idempotency, cost.",
    "ml_system_design_mlops": "ML system design & MLOps: training/serving architecture, feature stores, monitoring, drift, CI/CD for models.",
    "genai_llm": "GenAI / LLM: RAG, retrieval quality, prompting, evals, fine-tuning trade-offs, agents, latency/cost, safety.",
    "coding_problem_solving": "Coding & problem solving: writes correct, readable Python/SQL; reasons about edge cases and complexity.",
    "communication_tradeoffs": "Communication & trade-off reasoning: structured answers, states assumptions, weighs alternatives.",
}

ROLE_TYPES = ["ai_engineer", "ml_engineer", "data_scientist", "data_engineer"]

# Percent weights per role; each column sums to 100.
ROLE_WEIGHTS = {
    "ai_engineer": {
        "sql_data_modeling": 5, "stats_experimentation": 5, "ml_fundamentals": 10,
        "data_engineering": 5, "ml_system_design_mlops": 15, "genai_llm": 35,
        "coding_problem_solving": 15, "communication_tradeoffs": 10,
    },
    "ml_engineer": {
        "sql_data_modeling": 5, "stats_experimentation": 10, "ml_fundamentals": 20,
        "data_engineering": 10, "ml_system_design_mlops": 25, "genai_llm": 10,
        "coding_problem_solving": 15, "communication_tradeoffs": 5,
    },
    "data_scientist": {
        "sql_data_modeling": 15, "stats_experimentation": 25, "ml_fundamentals": 20,
        "data_engineering": 5, "ml_system_design_mlops": 10, "genai_llm": 5,
        "coding_problem_solving": 10, "communication_tradeoffs": 10,
    },
    "data_engineer": {
        "sql_data_modeling": 25, "stats_experimentation": 0, "ml_fundamentals": 5,
        "data_engineering": 35, "ml_system_design_mlops": 10, "genai_llm": 0,
        "coding_problem_solving": 15, "communication_tradeoffs": 10,
    },
}

for _role, _w in ROLE_WEIGHTS.items():
    assert sum(_w.values()) == 100, f"{_role} weights sum to {sum(_w.values())}"

SCALE = """\
Anchored 1-5 scale (apply to the candidate's answers in the transcript only):
1 = No meaningful evidence of the skill, or answers were incorrect.
2 = Surface familiarity: names concepts but cannot explain or apply them; needed heavy prompting.
3 = Correct on core points with some prompting; limited depth on trade-offs or edge cases.
4 = Correct and clear without prompting; discusses trade-offs and at least one real edge case.
5 = Deep, precise, unprompted: handles trade-offs, failure modes and production realities; could teach it.
If a bucket was not meaningfully probed, mark it not_assessed - never guess a score."""


def bucket_catalog() -> str:
    return "\n".join(f"- {k}: {v}" for k, v in BUCKETS.items())


def weighted_score(role_type: str, scores: dict[str, int]) -> float | None:
    """Weighted mean on the 1-5 scale over assessed, non-zero-weight buckets.

    Weights of not-assessed buckets are redistributed rather than counted as zero,
    so a missed topic lowers confidence (flagged elsewhere) instead of the score.
    """
    weights = ROLE_WEIGHTS[role_type]
    used = {b: s for b, s in scores.items() if weights.get(b, 0) > 0}
    total_w = sum(weights[b] for b in used)
    if total_w == 0:
        return None
    return round(sum(weights[b] * s for b, s in used.items()) / total_w, 2)


def weight_coverage(role_type: str, assessed: set[str]) -> int:
    """Percent of the role's weight that was actually assessed."""
    return sum(w for b, w in ROLE_WEIGHTS[role_type].items() if b in assessed)
