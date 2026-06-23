"""
Eval helpers for the email sentiment agent.

All public functions are imported by evals.ipynb.
Run from the evals/ directory so relative paths resolve correctly.
"""

import json
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import anthropic

# ── Models ────────────────────────────────────────────────────────────────────

AGENT_MODEL = "claude-haiku-4-5-20251001"   # same model the live agent uses
JUDGE_MODEL = "claude-sonnet-4-6"           # independent judge — different model avoids circularity

_DEFAULT_CASES_PATH   = Path(__file__).parent / "test_cases.json"
_DEFAULT_RESULTS_PATH = Path(__file__).parent / "results.json"
_DEFAULT_JUDGE_PATH   = Path(__file__).parent / "judge_results.json"

# ── Sentiment analysis (mirrors agent.py exactly) ─────────────────────────────

_SYSTEM_PROMPT = """You are a customer sentiment analyst for a marketing team.
Your job is to analyse customer email replies to a marketing campaign and return
structured sentiment data. Be accurate and nuanced — a politely disappointed
email is still negative. An angry demand is very negative. A simple status
question is neutral even if mildly frustrated.

Always respond with valid JSON only — no markdown fences, no extra text."""

_ANALYSIS_PROMPT = """Analyse this customer email and return a JSON object with exactly these keys:

- sentiment: "positive", "neutral", or "negative"
- score: float from -1.0 (extremely negative) to 1.0 (extremely positive)
- confidence: float 0.0-1.0 indicating how clear the sentiment is
- themes: list of 2-4 short theme strings from the email
  (e.g. "delivery delay", "product quality", "refund request", "positive experience")
- summary: one sentence capturing the email's sentiment and main point
- urgency: "low", "medium", or "high"
  (high = explicit refund demand, legal threat, chargeback, or viral/social media threat)

Email:
From: {sender}
Subject: {subject}
Body:
{body}"""


def _call_agent(sender, subject, body):
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=AGENT_MODEL,
        max_tokens=400,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _ANALYSIS_PROMPT.format(
            sender=sender, subject=subject, body=body,
        )}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(text)


# ── Test-case loading ─────────────────────────────────────────────────────────

def load_test_cases(path=None):
    with open(path or _DEFAULT_CASES_PATH) as f:
        return json.load(f)


# ── Eval runner ───────────────────────────────────────────────────────────────

def run_all_evals(test_cases, results_path=None, skip_existing=True, delay=0.3):
    """
    Run the agent on every test case. Saves incrementally after each call so
    progress is not lost if the run is interrupted.

    Parameters
    ----------
    test_cases    : list from load_test_cases()
    results_path  : path to save/reload results.json
    skip_existing : skip cases already present in results_path
    delay         : seconds between API calls

    Returns
    -------
    list of result dicts (one per test case, ordered as test_cases)
    """
    results_path = Path(results_path or _DEFAULT_RESULTS_PATH)

    existing = {}
    if skip_existing and results_path.exists():
        with open(results_path) as f:
            for r in json.load(f):
                existing[r["id"]] = r

    ordered = []
    for tc in test_cases:
        tid = tc["id"]

        if skip_existing and tid in existing:
            ordered.append(existing[tid])
            print(f"  [cached]  {tid}")
            continue

        print(f"  [running] {tid}  {tc['subject'][:52]}...", end=" ", flush=True)
        try:
            pred = _call_agent(tc["from"], tc["subject"], tc["body"])
            result = {
                "id":                  tid,
                "case_type":           tc.get("case_type", ""),
                "notes":               tc.get("notes", ""),
                "from":                tc["from"],
                "subject":             tc["subject"],
                "body":                tc["body"],
                # ground truth
                "expected_sentiment":  tc["expected"]["sentiment"],
                "expected_score_min":  tc["expected"]["score_min"],
                "expected_score_max":  tc["expected"]["score_max"],
                "expected_urgency":    tc["expected"]["urgency"],
                # predictions
                "predicted_sentiment": pred["sentiment"],
                "predicted_score":     pred["score"],
                "predicted_urgency":   pred["urgency"],
                "predicted_themes":    pred.get("themes", []),
                "predicted_summary":   pred.get("summary", ""),
                "predicted_confidence":pred.get("confidence", 0.0),
                # pass / fail
                "label_correct":    pred["sentiment"] == tc["expected"]["sentiment"],
                "score_in_range":   tc["expected"]["score_min"] <= pred["score"] <= tc["expected"]["score_max"],
                "urgency_correct":  pred["urgency"] == tc["expected"]["urgency"],
            }
            mark = "pass" if result["label_correct"] else "FAIL"
            print(f"[{mark}] {pred['sentiment']:<8} score={pred['score']:+.2f}")
        except Exception as exc:
            print(f"[ERROR] {exc}")
            result = {
                "id": tid, "case_type": tc.get("case_type", ""), "notes": tc.get("notes", ""),
                "from": tc["from"], "subject": tc["subject"], "body": tc["body"],
                "expected_sentiment": tc["expected"]["sentiment"],
                "expected_score_min": tc["expected"]["score_min"],
                "expected_score_max": tc["expected"]["score_max"],
                "expected_urgency":   tc["expected"]["urgency"],
                "error": str(exc),
                "label_correct": False, "score_in_range": False, "urgency_correct": False,
            }

        ordered.append(result)
        existing[tid] = result
        with open(results_path, "w") as f:
            json.dump(list(existing.values()), f, indent=2)
        time.sleep(delay)

    return ordered


# ── Metrics ───────────────────────────────────────────────────────────────────

def compute_label_metrics(results):
    """
    Returns accuracy, per-class precision/recall/F1, and a confusion matrix.
    Only counts results that have a predicted_sentiment (skips errored runs).
    """
    classes = ["positive", "neutral", "negative"]
    cm = {a: {p: 0 for p in classes} for a in classes}
    valid = [r for r in results if "predicted_sentiment" in r]

    for r in valid:
        a, p = r["expected_sentiment"], r["predicted_sentiment"]
        if a in cm and p in cm:
            cm[a][p] += 1

    correct  = sum(r["label_correct"] for r in valid)
    accuracy = correct / len(valid) if valid else 0.0

    per_class = {}
    for cls in classes:
        tp = cm[cls][cls]
        fp = sum(cm[o][cls] for o in classes if o != cls)
        fn = sum(cm[cls][o] for o in classes if o != cls)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        per_class[cls] = {
            "precision": round(prec, 3),
            "recall":    round(rec,  3),
            "f1":        round(f1,   3),
            "support":   tp + fn,
        }

    return {
        "accuracy":         round(accuracy, 4),
        "correct":          correct,
        "total":            len(valid),
        "per_class":        per_class,
        "confusion_matrix": [[cm[a][p] for p in classes] for a in classes],
        "classes":          classes,
    }


def compute_score_calibration(results):
    """
    Returns mean / min / max predicted score grouped by ground-truth class,
    plus a list of individual scores for box-plot use.
    """
    classes = ["positive", "neutral", "negative"]
    grouped = {c: [] for c in classes}

    for r in results:
        if "predicted_score" in r:
            grouped[r["expected_sentiment"]].append(r["predicted_score"])

    out = {}
    for cls, scores in grouped.items():
        if scores:
            out[cls] = {
                "mean":   round(sum(scores) / len(scores), 3),
                "min":    round(min(scores), 3),
                "max":    round(max(scores), 3),
                "count":  len(scores),
                "scores": scores,
            }
    return out


def compute_urgency_metrics(results):
    """
    Precision, recall, F1 for high-urgency detection.
    Also returns a detail table of every case where expected or predicted is 'high'.
    """
    valid = [r for r in results if "predicted_urgency" in r]
    tp = sum(1 for r in valid if r["expected_urgency"] == "high" and r["predicted_urgency"] == "high")
    fp = sum(1 for r in valid if r["expected_urgency"] != "high" and r["predicted_urgency"] == "high")
    fn = sum(1 for r in valid if r["expected_urgency"] == "high" and r["predicted_urgency"] != "high")

    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

    detail = [
        {
            "id":        r["id"],
            "subject":   r["subject"][:55],
            "expected":  r["expected_urgency"],
            "predicted": r["predicted_urgency"],
            "correct":   r["urgency_correct"],
        }
        for r in valid
        if r["expected_urgency"] == "high" or r["predicted_urgency"] == "high"
    ]

    return {
        "precision": round(prec, 3),
        "recall":    round(rec,  3),
        "f1":        round(f1,   3),
        "tp": tp, "fp": fp, "fn": fn,
        "high_urgency_cases": detail,
    }


# ── LLM Judge ────────────────────────────────────────────────────────────────

_JUDGE_SYSTEM = """You are an expert evaluator assessing the output quality of an AI sentiment
analysis system. Be fair and precise. Respond with valid JSON only — no markdown fences."""

_JUDGE_PROMPT = """You are grading an AI's analysis of a customer email.

EMAIL:
Subject: {subject}
Body:
{body}

AI OUTPUT:
- Sentiment: {sentiment}  (score: {score})
- Themes: {themes}
- Summary: {summary}

Grade on two dimensions (integer 1, 2, or 3):

theme_score:
  3 = All themes clearly present in the email and well-chosen
  2 = Mostly relevant, one theme is weak or a key theme is missing
  1 = Themes are vague, wrong, or miss the main concerns

summary_score:
  3 = Summary accurately captures the sentiment and main point in one sentence
  2 = Mostly correct but misses a nuance or is slightly imprecise
  1 = Misrepresents the tone or main point of the email

Also provide a one-sentence 'judge_notes' explaining any issues found (or "No issues." if perfect).

Return JSON with keys: theme_score (int), summary_score (int), judge_notes (str)"""


def run_judge_evals(results, judge_path=None, skip_existing=True, delay=0.5):
    """
    Use claude-sonnet-4-6 to grade theme relevance and summary quality for
    each result. Saves incrementally to judge_path.

    Returns list of judge result dicts.
    """
    judge_path = Path(judge_path or _DEFAULT_JUDGE_PATH)
    client = anthropic.Anthropic()

    existing = {}
    if skip_existing and judge_path.exists():
        with open(judge_path) as f:
            for r in json.load(f):
                existing[r["id"]] = r

    judged = []
    for r in results:
        if "predicted_sentiment" not in r:
            continue  # skip errored runs

        rid = r["id"]
        if skip_existing and rid in existing:
            judged.append(existing[rid])
            print(f"  [cached]  {rid}")
            continue

        print(f"  [judging] {rid}  {r['subject'][:52]}...", end=" ", flush=True)
        try:
            prompt = _JUDGE_PROMPT.format(
                subject=r["subject"],
                body=r["body"],
                sentiment=r["predicted_sentiment"],
                score=r["predicted_score"],
                themes=", ".join(r.get("predicted_themes", [])),
                summary=r.get("predicted_summary", ""),
            )
            resp = client.messages.create(
                model=JUDGE_MODEL,
                max_tokens=200,
                system=_JUDGE_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            grades = json.loads(text)

            jr = {
                "id":           rid,
                "subject":      r["subject"],
                "theme_score":  int(grades["theme_score"]),
                "summary_score":int(grades["summary_score"]),
                "judge_notes":  grades.get("judge_notes", ""),
                "themes":       r.get("predicted_themes", []),
                "summary":      r.get("predicted_summary", ""),
            }
            print(f"themes={jr['theme_score']}/3  summary={jr['summary_score']}/3")
        except Exception as exc:
            print(f"[ERROR] {exc}")
            jr = {"id": rid, "subject": r["subject"], "error": str(exc),
                  "theme_score": None, "summary_score": None}

        judged.append(jr)
        existing[rid] = jr
        with open(judge_path, "w") as f:
            json.dump(list(existing.values()), f, indent=2)
        time.sleep(delay)

    return judged