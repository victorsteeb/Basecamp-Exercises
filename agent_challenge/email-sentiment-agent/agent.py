"""
Email Sentiment Agent — main loop.

Usage:
  python agent.py

Reads unprocessed emails from mock_emails.json one at a time, calls Claude
to score sentiment, writes results to SQLite, and fires alerts to the
marketing team when sentiment crosses configured thresholds.

Keep the dashboard running in a separate terminal:
  uvicorn dashboard:app --port 8000 --reload
"""

import json
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

import anthropic

import db
from config import (
    ALERT_CRITICAL_SCORE_THRESHOLD,
    ALERT_NEGATIVE_RATE_THRESHOLD,
    ALERT_WINDOW_SIZE,
    ALERTS_LOG_PATH,
    ANTHROPIC_MODEL,
    DASHBOARD_PORT,
    EMAILS_PATH,
    MARKETING_TEAM_EMAIL,
    PROCESS_DELAY_SECONDS,
)

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a customer sentiment analyst for a marketing team.
Your job is to analyse customer email replies to a marketing campaign and return
structured sentiment data. Be accurate and nuanced — a politely disappointed
email is still negative. An angry demand is very negative. A simple status
question is neutral even if mildly frustrated.

Always respond with valid JSON only — no markdown fences, no extra text."""

ANALYSIS_PROMPT = """Analyse this customer email and return a JSON object with exactly these keys:

- sentiment: "positive", "neutral", or "negative"
- score: float from -1.0 (extremely negative) to 1.0 (extremely positive)
- confidence: float 0.0–1.0 indicating how clear the sentiment is
- themes: list of 2–4 short theme strings from the email
  (e.g. "delivery delay", "product quality", "refund request", "positive experience")
- summary: one sentence capturing the email's sentiment and main point
- urgency: "low", "medium", or "high"
  (high = explicit refund demand, legal threat, chargeback, or viral/social media threat)

Email:
From: {sender}
Subject: {subject}
Body:
{body}"""


def load_emails():
    with open(EMAILS_PATH) as f:
        return json.load(f)


def save_emails(emails):
    with open(EMAILS_PATH, "w") as f:
        json.dump(emails, f, indent=2)


def analyse_sentiment(email):
    prompt = ANALYSIS_PROMPT.format(
        sender=email["from"],
        subject=email["subject"],
        body=email["body"],
    )
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    # Strip markdown code fences that the model sometimes adds despite instructions
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()
    return json.loads(text)


# ── Alert logic ───────────────────────────────────────────────────────────────

def _fire_alert(alert_type, message, trigger_value):
    border = "=" * 62
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{border}")
    print(f"  MARKETING ALERT  |  {ts}")
    print(border)
    print(f"  To:      {MARKETING_TEAM_EMAIL}")
    print(f"  Type:    {alert_type}")
    print(f"  Trigger: {trigger_value:.3f}")
    print(f"\n  {message}")
    print(f"{border}\n")

    db.save_alert(alert_type, message, trigger_value, MARKETING_TEAM_EMAIL)

    with open(ALERTS_LOG_PATH, "a") as f:
        f.write(f"\n[{ts}] {alert_type}  (trigger={trigger_value:.3f})\n")
        f.write(f"To: {MARKETING_TEAM_EMAIL}\n")
        f.write(message + "\n")
        f.write("-" * 62 + "\n")


def check_alerts(state: dict) -> dict:
    window = db.get_rolling_window(ALERT_WINDOW_SIZE)
    if len(window) < 5:
        return state

    neg_rate = sum(1 for e in window if e["sentiment"] == "negative") / len(window)
    avg_score = sum(e["score"] for e in window) / len(window)
    state = dict(state)

    # High negative rate
    if neg_rate >= ALERT_NEGATIVE_RATE_THRESHOLD and not state.get("high_negative"):
        _fire_alert(
            "HIGH_NEGATIVE_RATE",
            (
                f"Negative response rate has reached {neg_rate:.0%} "
                f"across the last {len(window)} emails "
                f"(rolling avg score: {avg_score:+.2f}). "
                "Recommend immediate campaign review and customer service escalation."
            ),
            neg_rate,
        )
        state["high_negative"] = True
    elif neg_rate < ALERT_NEGATIVE_RATE_THRESHOLD * 0.75:
        state["high_negative"] = False  # reset if conditions improve

    # Critical average score
    if avg_score <= ALERT_CRITICAL_SCORE_THRESHOLD and not state.get("critical_score"):
        _fire_alert(
            "CRITICAL_SENTIMENT",
            (
                f"Rolling average sentiment score has dropped to {avg_score:+.2f} "
                f"(threshold: {ALERT_CRITICAL_SCORE_THRESHOLD:+.2f}). "
                "Campaign is generating strongly negative customer reactions. "
                "Escalation to campaign leadership required."
            ),
            avg_score,
        )
        state["critical_score"] = True
    elif avg_score > ALERT_CRITICAL_SCORE_THRESHOLD + 0.15:
        state["critical_score"] = False

    return state


# ── Main loop ─────────────────────────────────────────────────────────────────

ICONS = {"positive": "✓", "neutral": "~", "negative": "✗"}


def run():
    db.init_db()

    print("=" * 62)
    print("  Email Sentiment Agent")
    print(f"  Dashboard -> http://localhost:{DASHBOARD_PORT}")
    print(f"  Model     -> {ANTHROPIC_MODEL}")
    print("=" * 62)
    print("  Press Ctrl+C to stop.\n")

    alert_state: dict = {}
    total_processed = 0

    while True:
        try:
            emails = load_emails()
        except FileNotFoundError:
            print(f"ERROR: {EMAILS_PATH} not found. Run `python generate_emails.py` first.")
            sys.exit(1)

        unprocessed = [e for e in emails if not e.get("processed")]

        if not unprocessed:
            if total_processed == 0:
                print(f"No emails to process. Run `python generate_emails.py` first.")
                sys.exit(0)
            print(f"\nAll {total_processed} emails processed. Agent idle — polling for new emails...")
            time.sleep(10)
            continue

        email = unprocessed[0]
        ts_label = email["timestamp"][:10]

        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            f"({ts_label})  {email['subject'][:52]:<52}",
            end=" ",
            flush=True,
        )

        try:
            result = analyse_sentiment(email)

            db.save_sentiment(
                email["id"],
                email["timestamp"],
                email["from"],
                email["subject"],
                email["body"],
                result,
            )

            for e in emails:
                if e["id"] == email["id"]:
                    e["processed"] = True
                    break
            save_emails(emails)

            icon = ICONS.get(result["sentiment"], "?")
            print(f"{icon} {result['sentiment']:<8} score={result['score']:+.2f}  urgency={result['urgency']}")

            total_processed += 1
            alert_state = check_alerts(alert_state)

        except json.JSONDecodeError as exc:
            print(f"[JSON parse error] {exc}")
        except anthropic.APIError as exc:
            print(f"[API error] {exc}")
            time.sleep(5)
        except Exception as exc:
            print(f"[Error] {exc}")

        time.sleep(PROCESS_DELAY_SECONDS)


if __name__ == "__main__":
    run()
