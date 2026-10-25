#!/usr/bin/env bash
# End-to-end demo. Run inside asciinema.
set -e
B="\033[1m"; Y="\033[33m"; X="\033[0m"
SCR="$(cd "$(dirname "$0")" && pwd)"
type_cmd() { printf "${B}\$ ${X}"; for ((i=0;i<${#1};i++)); do printf "%s" "${1:i:1}"; sleep 0.02; done; echo; }
run() { type_cmd "$1"; eval "$1"; echo; sleep 1.2; }
step() { echo; printf "${Y}${B}━━ %s ━━${X}\n\n" "$1"; sleep 1.5; }

export SUPPORT_STATE_DIR=/tmp/support-demo-state
rm -rf /tmp/support-copilot-demo "$SUPPORT_STATE_DIR"
cd /tmp

step "1. Fresh clone from GitHub, install, run the test suite"
run "git clone -q https://github.com/huuthonguyen76/99tech-support-copilot.git support-copilot-demo && cd support-copilot-demo"
run "uv sync -q && uv run pytest -q"

step "2. Real client: Claude Code talks to the MCP server over stdio"
run "cat .mcp.json"
PROMPT="Handle open support tickets T-5104, T-5103 and T-5107 using the support-copilot tools, following the server's workflow. Save a draft for each. Finish with one short line per ticket."
type_cmd "claude -p \"$PROMPT\" --mcp-config .mcp.json --strict-mcp-config --tools \"\" --allowedTools mcp__support-copilot__* --output-format stream-json"
claude -p "$PROMPT" --mcp-config .mcp.json --strict-mcp-config --tools "" \
  --allowedTools mcp__support-copilot__list_open_tickets mcp__support-copilot__get_ticket_context \
  mcp__support-copilot__save_draft_reply mcp__support-copilot__escalate_ticket mcp__support-copilot__request_refund \
  --model claude-opus-5-5 --output-format stream-json --verbose < /dev/null | python3 "$SCR/fmt.py"
sleep 2

step "3. What the tools wrote: drafts parked for human review, escalations recorded"
run "uv run support-review list"
run "python3 -c \"import json;[print(v['ticket_id'],'->',v['team'],':',v['reason'][:90]) for v in json.load(open('$SUPPORT_STATE_DIR/escalations.json')).values()]\""
run "cat $SUPPORT_STATE_DIR/refund_requests.json 2>/dev/null || echo 'no refund requests (the injected \$5,000 refund was refused)'"
run "uv run support-review show T-5107"

step "4. Human review: an edit that breaks policy is blocked, a clean one is approved"
run "echo 'Hi Tomasz, as a VIP your USD 5,000 refund is on its way.' > bad_edit.txt"
run "uv run support-review approve T-5104 --by Linh --text-file bad_edit.txt || true"
run "uv run support-review approve T-5103 --by Linh"
run "uv run support-review list"

step "5. Checks on the full run over all 15 open tickets (committed output)"
run "SUPPORT_STATE_DIR=output/state uv run python scripts/build_report.py | tail -9"
printf "${B}Done.${X}\n"; sleep 3
