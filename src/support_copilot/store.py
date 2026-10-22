"""Write side: drafts, escalations and refund requests, kept as local JSON.

Stands in for the helpdesk. Nothing here sends anything to a customer: drafts
sit at `pending_review` until a person approves them with the review CLI.
Every write is also appended to audit.jsonl.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .data import REPO_ROOT

FILES = ("drafts", "escalations", "refund_requests")


def state_dir() -> Path:
    path = Path(os.environ.get("SUPPORT_STATE_DIR", REPO_ROOT / "state"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _path(name: str) -> Path:
    return state_dir() / f"{name}.json"


def load(name: str) -> dict:
    p = _path(name)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save(name: str, records: dict) -> None:
    p = _path(name)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(records, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    tmp.replace(p)


def audit(action: str, **fields) -> None:
    entry = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "action": action, **fields}
    with open(state_dir() / "audit.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def upsert(name: str, key: str, record: dict) -> dict:
    """Insert or replace one record. Re-running a ticket overwrites, it doesn't duplicate."""
    records = load(name)
    previous = records.get(key)
    record = {**record, "revision": (previous or {}).get("revision", 0) + 1}
    records[key] = record
    save(name, records)
    audit(f"{name}.upsert", key=key, revision=record["revision"])
    return record
