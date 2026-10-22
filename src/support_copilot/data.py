"""Load the Customer Support export from local files.

The export is read-only input. Everything the tools write goes to the state
directory (see store.py), so a run never mutates the source data.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# The export was taken on 29 Sep 2026 09:00 UTC (README). Ages and SLA checks are
# measured from that moment, not from the wall clock, so results are reproducible.
DEFAULT_NOW = "2026-09-29T09:00:00Z"


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def data_dir() -> Path:
    return Path(os.environ.get("SUPPORT_DATA_DIR", REPO_ROOT / "data"))


def now() -> datetime:
    return parse_ts(os.environ.get("SUPPORT_NOW", DEFAULT_NOW))


@dataclass(frozen=True)
class Customer:
    customer_id: str
    full_name: str
    email: str
    phone: str
    country: str
    currency: str
    vip_tier: str
    kyc_status: str
    kyc_review_reason: str
    self_excluded: bool
    balance: float
    registered_at: str

    @property
    def given_name(self) -> str:
        parts = self.full_name.split()
        # Vietnamese names put the given name last ("Tran Thi Thu Ha" -> "Ha").
        return parts[-1] if self.country == "VN" else parts[0]


@dataclass(frozen=True)
class Transaction:
    txn_id: str
    customer_id: str
    type: str
    amount: float
    currency: str
    status: str
    provider: str
    created_at: datetime
    updated_at: datetime
    note: str


@dataclass(frozen=True)
class Ticket:
    ticket_id: str
    customer_id: str
    channel: str
    created_at: datetime
    subject: str
    message: str
    status: str
    assigned_to: str | None
    first_response_at: str | None
    agent_reply: str | None
    resolution: str | None


@dataclass
class Export:
    customers: dict[str, Customer]
    transactions: list[Transaction]
    tickets: dict[str, Ticket]
    handbook: str
    bonus_terms: str
    marketing_plan: str
    finance_notes: str
    slack: list[dict] = field(default_factory=list)

    def customer_transactions(self, customer_id: str) -> list[Transaction]:
        return [t for t in self.transactions if t.customer_id == customer_id]

    def customer_tickets(self, customer_id: str) -> list[Ticket]:
        return [t for t in self.tickets.values() if t.customer_id == customer_id]

    def open_tickets(self) -> list[Ticket]:
        return [t for t in self.tickets.values() if t.status == "open"]


def load_export(path: Path | None = None) -> Export:
    root = path or data_dir()

    with open(root / "customers.csv", newline="", encoding="utf-8") as f:
        customers = {
            r["customer_id"]: Customer(
                customer_id=r["customer_id"],
                full_name=r["full_name"],
                email=r["email"],
                phone=r["phone"],
                country=r["country"],
                currency=r["currency"],
                vip_tier=r["vip_tier"],
                kyc_status=r["kyc_status"],
                kyc_review_reason=r["kyc_review_reason"],
                self_excluded=r["self_excluded"].strip().lower() == "true",
                balance=float(r["balance"] or 0),
                registered_at=r["registered_at"],
            )
            for r in csv.DictReader(f)
        }

    with open(root / "transactions.csv", newline="", encoding="utf-8") as f:
        transactions = [
            Transaction(
                txn_id=r["txn_id"],
                customer_id=r["customer_id"],
                type=r["type"],
                amount=float(r["amount"]),
                currency=r["currency"],
                status=r["status"],
                provider=r["provider"],
                created_at=parse_ts(r["created_at"]),
                updated_at=parse_ts(r["updated_at"]),
                note=r["note"],
            )
            for r in csv.DictReader(f)
        ]

    raw_tickets = json.loads((root / "tickets.json").read_text(encoding="utf-8"))
    tickets = {
        t["ticket_id"]: Ticket(
            ticket_id=t["ticket_id"],
            customer_id=t["customer_id"],
            channel=t["channel"],
            created_at=parse_ts(t["created_at"]),
            subject=t["subject"],
            message=t["message"],
            status=t["status"],
            assigned_to=t["assigned_to"],
            first_response_at=t["first_response_at"],
            agent_reply=t["agent_reply"],
            resolution=t["resolution"],
        )
        for t in raw_tickets
    }

    return Export(
        customers=customers,
        transactions=transactions,
        tickets=tickets,
        # v2 is the handbook in force since 15 Aug 2026. v1 is deliberately not loaded:
        # it is superseded, and half the policy mistakes in the export come from it.
        handbook=(root / "support-handbook-v2.md").read_text(encoding="utf-8"),
        bonus_terms=(root / "bonus-terms.md").read_text(encoding="utf-8"),
        marketing_plan=(root / "marketing-q4-campaigns.md").read_text(encoding="utf-8"),
        finance_notes=(root / "finance-month-end-sept.md").read_text(encoding="utf-8"),
        slack=json.loads((root / "slack-support-channel.json").read_text(encoding="utf-8")),
    )
