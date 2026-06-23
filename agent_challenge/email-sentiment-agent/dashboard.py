"""
FastAPI dashboard server.

Usage (from the email-sentiment-agent directory):
  python -m uvicorn dashboard:app --port 8000 --reload
"""

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

import db

app = FastAPI(title="Campaign Sentiment Dashboard")

TEMPLATES_DIR = Path(__file__).parent / "templates"


@app.get("/", response_class=FileResponse)
def index():
    return FileResponse(TEMPLATES_DIR / "index.html")


@app.get("/api/stats")
def stats():
    return JSONResponse(db.get_stats())


@app.get("/api/timeseries")
def timeseries():
    return JSONResponse(db.get_time_series())


@app.get("/api/emails")
def recent_emails(limit: int = 25):
    return JSONResponse(db.get_recent_emails(limit))


@app.get("/api/alerts")
def recent_alerts(limit: int = 10):
    return JSONResponse(db.get_recent_alerts(limit))


@app.get("/api/stream")
async def stream():
    """
    Server-Sent Events endpoint. Pushes three event types to the browser:
      - email   new sentiment result (one per message)
      - alert   a new alert fired
      - stats   updated aggregate stats (sent after each batch of new emails)
    """
    async def generator():
        last_email_ts = "0000-00-00T00:00:00"
        last_alert_ts = "0000-00-00T00:00:00"

        # Send initial snapshot so the page renders immediately on connect
        initial_emails = db.get_recent_emails(25)
        initial_stats  = db.get_stats()
        initial_alerts = db.get_recent_alerts(10)

        yield f"data: {json.dumps({'type': 'snapshot', 'emails': initial_emails, 'stats': initial_stats, 'alerts': initial_alerts})}\n\n"

        if initial_emails:
            last_email_ts = max(e["processed_at"] for e in initial_emails)
        if initial_alerts:
            last_alert_ts = max(a["fired_at"] for a in initial_alerts)

        while True:
            await asyncio.sleep(0.6)

            new_emails = db.get_emails_since(last_email_ts)
            new_alerts = db.get_alerts_since(last_alert_ts)

            for email in new_emails:
                yield f"data: {json.dumps({'type': 'email', 'data': email})}\n\n"
                last_email_ts = email["processed_at"]

            for alert in new_alerts:
                yield f"data: {json.dumps({'type': 'alert', 'data': alert})}\n\n"
                last_alert_ts = alert["fired_at"]

            if new_emails or new_alerts:
                stats_data = db.get_stats()
                ts_data    = db.get_time_series()
                yield f"data: {json.dumps({'type': 'stats', 'data': stats_data, 'timeseries': ts_data})}\n\n"

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )