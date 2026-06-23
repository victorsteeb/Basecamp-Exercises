import sqlite3
import json
from datetime import datetime
from config import DB_PATH


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sentiment_results (
            id          TEXT PRIMARY KEY,
            email_ts    TEXT NOT NULL,
            processed_at TEXT NOT NULL,
            sender      TEXT,
            subject     TEXT,
            preview     TEXT,
            sentiment   TEXT,
            score       REAL,
            confidence  REAL,
            themes      TEXT,
            summary     TEXT,
            urgency     TEXT
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            fired_at     TEXT NOT NULL,
            alert_type   TEXT NOT NULL,
            message      TEXT NOT NULL,
            trigger_value REAL,
            sent_to      TEXT
        );
    """)
    conn.commit()
    conn.close()


def save_sentiment(email_id, email_ts, sender, subject, body, result):
    conn = _connect()
    conn.execute(
        """INSERT OR REPLACE INTO sentiment_results
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            email_id, email_ts,
            datetime.utcnow().isoformat(),
            sender, subject,
            body[:200],
            result["sentiment"],
            result["score"],
            result["confidence"],
            json.dumps(result["themes"]),
            result["summary"],
            result["urgency"],
        ),
    )
    conn.commit()
    conn.close()


def save_alert(alert_type, message, trigger_value, sent_to):
    conn = _connect()
    conn.execute(
        "INSERT INTO alerts (fired_at,alert_type,message,trigger_value,sent_to) VALUES (?,?,?,?,?)",
        (datetime.utcnow().isoformat(), alert_type, message, trigger_value, sent_to),
    )
    conn.commit()
    conn.close()


# ── read helpers ──────────────────────────────────────────────────────────────

def get_time_series():
    conn = _connect()
    rows = conn.execute("""
        SELECT
            DATE(email_ts) AS day,
            ROUND(AVG(score), 3)  AS avg_score,
            COUNT(*)              AS total,
            SUM(sentiment='positive') AS positive,
            SUM(sentiment='neutral')  AS neutral,
            SUM(sentiment='negative') AS negative
        FROM sentiment_results
        GROUP BY day
        ORDER BY day
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    conn = _connect()
    r = conn.execute("""
        SELECT
            COUNT(*)                  AS total,
            ROUND(AVG(score), 3)      AS avg_score,
            SUM(sentiment='positive') AS positive,
            SUM(sentiment='neutral')  AS neutral,
            SUM(sentiment='negative') AS negative
        FROM sentiment_results
    """).fetchone()
    conn.close()
    if not r["total"]:
        return {"total": 0, "avg_score": 0.0,
                "positive": 0, "neutral": 0, "negative": 0,
                "positive_pct": 0.0, "neutral_pct": 0.0, "negative_pct": 0.0}
    t = r["total"]
    return {
        "total": t,
        "avg_score": r["avg_score"],
        "positive": r["positive"], "neutral": r["neutral"], "negative": r["negative"],
        "positive_pct": round(r["positive"] / t * 100, 1),
        "neutral_pct":  round(r["neutral"]  / t * 100, 1),
        "negative_pct": round(r["negative"] / t * 100, 1),
    }


def get_recent_emails(limit=25):
    conn = _connect()
    rows = conn.execute("""
        SELECT id, email_ts, sender, subject, preview,
               sentiment, score, urgency, summary, processed_at
        FROM sentiment_results
        ORDER BY email_ts DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_alerts(limit=10):
    conn = _connect()
    rows = conn.execute("""
        SELECT fired_at, alert_type, message, trigger_value, sent_to
        FROM alerts ORDER BY fired_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_emails_since(processed_at: str, limit=50):
    """Emails written to DB after `processed_at`, oldest-first (for SSE streaming)."""
    conn = _connect()
    rows = conn.execute("""
        SELECT id, email_ts, sender, subject, preview,
               sentiment, score, urgency, summary, processed_at
        FROM sentiment_results
        WHERE processed_at > ?
        ORDER BY processed_at ASC
        LIMIT ?
    """, (processed_at, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_alerts_since(fired_at: str, limit=20):
    """Alerts fired after `fired_at`, oldest-first."""
    conn = _connect()
    rows = conn.execute("""
        SELECT fired_at, alert_type, message, trigger_value, sent_to
        FROM alerts WHERE fired_at > ?
        ORDER BY fired_at ASC LIMIT ?
    """, (fired_at, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_rolling_window(size=20):
    """Latest N results for alert calculations."""
    conn = _connect()
    rows = conn.execute("""
        SELECT sentiment, score FROM sentiment_results
        ORDER BY email_ts DESC, processed_at DESC
        LIMIT ?
    """, (size,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
