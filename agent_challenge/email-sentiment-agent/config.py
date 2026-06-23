ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"  # Fast + cheap for high-volume analysis

DB_PATH = "sentiment.db"
EMAILS_PATH = "mock_emails.json"
ALERTS_LOG_PATH = "alerts.log"

# Rolling window for alert calculations
ALERT_WINDOW_SIZE = 20

# Fire alert when negative rate in the window exceeds this
ALERT_NEGATIVE_RATE_THRESHOLD = 0.50   # 50%

# Fire alert when rolling avg score drops below this
ALERT_CRITICAL_SCORE_THRESHOLD = -0.40

# Seconds between processing each email (lower = faster simulation)
PROCESS_DELAY_SECONDS = 1.5

MARKETING_TEAM_EMAIL = "marketing-team@company.com"
DASHBOARD_PORT = 8000
