"""Human review step. The model drafts; an agent approves (optionally editing) or rejects.

    uv run support-review list
    uv run support-review show T-5101
    uv run support-review approve T-5101 --by Linh [--text-file edited.txt]
    uv run support-review reject T-5101 --by Linh --why "wrong amount"

Approving re-runs the guardrails on the final text, so a human edit can't
quietly reintroduce a policy break. Approved replies are what the agent pastes
into the helpdesk; this tool still never contacts the customer.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import store
from .data import load_export, now
from .guardrails import as_dicts, check_draft
from .policy import assess


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="support-review")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    s = sub.add_parser("show"); s.add_argument("ticket_id")
    a = sub.add_parser("approve"); a.add_argument("ticket_id"); a.add_argument("--by", required=True)
    a.add_argument("--text-file", type=Path)
    r = sub.add_parser("reject"); r.add_argument("ticket_id"); r.add_argument("--by", required=True)
    r.add_argument("--why", required=True)
    args = p.parse_args(argv)

    drafts = store.load("drafts")
    if args.cmd == "list":
        for d in sorted(drafts.values(), key=lambda d: (d["priority"], d["ticket_id"])):
            print(f"{d['ticket_id']}  {d['priority']}  {d['status']:<16} {d['language']}  escalated={','.join(d['escalated_to']) or '-'}")
        return 0

    tid = args.ticket_id.upper()
    if tid not in drafts:
        print(f"No draft for {tid}", file=sys.stderr)
        return 1
    d = drafts[tid]

    if args.cmd == "show":
        print(f"{tid} [{d['status']}] lang={d['language']}\n\n{d['reply_text']}\n\n-- internal note --\n{d['internal_note']}")
        for w in d["warnings"]:
            print(f"! {w['code']}: {w['detail']}")
        return 0

    if args.cmd == "reject":
        store.upsert("drafts", tid, {**d, "status": "rejected", "reviewed_by": args.by, "review_note": args.why,
                                     "reviewed_at": now().isoformat()})
        print(f"{tid} rejected")
        return 0

    text = args.text_file.read_text(encoding="utf-8") if args.text_file else d["reply_text"]
    export = load_export()
    ticket = export.tickets[tid]
    blocking = [v for v in check_draft(text, ticket, assess(ticket, export), export) if v.blocking]
    if blocking:
        for v in as_dicts(blocking):
            print(f"BLOCKED {v['code']}: {v['detail']}", file=sys.stderr)
        return 2
    store.upsert("drafts", tid, {**d, "reply_text": text, "status": "approved", "reviewed_by": args.by,
                                 "edited_by_reviewer": text != d["reply_text"], "reviewed_at": now().isoformat()})
    print(f"{tid} approved by {args.by}. Paste the reply into the helpdesk to send.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
