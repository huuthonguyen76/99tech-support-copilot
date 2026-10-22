#!/usr/bin/env bash
# Runs the copilot on every open ticket with a real client: Claude Code in headless
# mode, connected to the MCP server over stdio, with only the copilot tools allowed.
# Writes state to output/state/ and the full tool-call transcript to output/transcript.jsonl,
# then renders output/open-tickets-report.md.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
rm -rf output/state && mkdir -p output/state

CONFIG="$(mktemp)"
cat > "$CONFIG" <<JSON
{"mcpServers": {"support-copilot": {
  "command": "uv", "args": ["run", "--directory", "$ROOT", "support-copilot"],
  "env": {"SUPPORT_STATE_DIR": "$ROOT/output/state"}}}}
JSON

TOOLS="mcp__support-copilot__list_open_tickets mcp__support-copilot__get_ticket_context \
mcp__support-copilot__save_draft_reply mcp__support-copilot__escalate_ticket \
mcp__support-copilot__request_refund mcp__support-copilot__find_stuck_withdrawals"

claude -p "$(cat scripts/run_prompt.md)" \
  --mcp-config "$CONFIG" --strict-mcp-config \
  --tools "" --allowedTools $TOOLS \
  --model "${MODEL:-claude-opus-5-5}" \
  --output-format stream-json --verbose \
  < /dev/null > output/transcript.jsonl

rm -f "$CONFIG"
uv run python scripts/build_report.py
