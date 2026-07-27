#!/bin/bash

# Post-tool-use hook for Claude Code
# Logs all tool usage to a file for debugging and tracking

# Create logs directory if it doesn't exist (root-level)
LOGS_DIR="${CLAUDE_PROJECT_DIR}/logs"
mkdir -p "$LOGS_DIR"

# Log file path with date
LOG_FILE="${LOGS_DIR}/tool-usage-$(date +%Y-%m-%d).log"

# Read the JSON input from stdin
INPUT=$(cat)

# Extract key fields from JSON using jq (if available) or basic parsing
if command -v jq &> /dev/null; then
    # Use jq for clean JSON parsing
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // "unknown"')
    SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"')
    TOOL_INPUT=$(echo "$INPUT" | jq -c '.tool_input // {}')
    TOOL_RESPONSE=$(echo "$INPUT" | jq -c '.tool_response // {}')

    # Create a nicely formatted log entry
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

    echo "=== Tool Usage: $TIMESTAMP ===" >> "$LOG_FILE"
    echo "Tool: $TOOL_NAME" >> "$LOG_FILE"
    echo "Session: $SESSION_ID" >> "$LOG_FILE"
    echo "Input: $TOOL_INPUT" >> "$LOG_FILE"
    echo "Response: $TOOL_RESPONSE" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"

else
    # Fallback: simple logging without JSON parsing
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

    echo "=== Tool Usage: $TIMESTAMP ===" >> "$LOG_FILE"
    echo "$INPUT" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
fi

# Always allow the tool to proceed
exit 0
