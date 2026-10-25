"""End-to-end through the MCP protocol with the SDK's in-process client: the
same tool schemas and results a real client (Claude Desktop / Code) gets."""

import json

import pytest
from mcp import Client

from support_copilot import store
from support_copilot.review import main as review_main
from support_copilot.server import mcp

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def call(client, name, **args):
    r = await client.call_tool(name, args)
    text = r.content[0].text if r.content else ""
    return r.is_error, (json.loads(text) if text.startswith("{") else text)


async def test_tools_are_listed_with_annotations():
    async with Client(mcp) as c:
        tools = {t.name: t for t in (await c.list_tools()).tools}
    assert set(tools) == {"list_open_tickets", "get_ticket_context", "save_draft_reply",
                          "escalate_ticket", "request_refund", "find_stuck_withdrawals"}
    assert tools["get_ticket_context"].annotations.read_only_hint is True
    assert tools["save_draft_reply"].annotations.read_only_hint is False


async def test_queue_is_sorted_by_priority():
    async with Client(mcp) as c:
        _, q = await call(c, "list_open_tickets")
    assert q["count"] == 15
    priorities = [r["priority"] for r in q["tickets"]]
    assert priorities == sorted(priorities)
    assert q["tickets"][0]["priority"] == "P1"


async def test_no_contact_details_or_kyc_reasons_in_any_context(export):
    secrets = [c.email for c in export.customers.values()] + [c.phone for c in export.customers.values()]
    secrets += [c.kyc_review_reason for c in export.customers.values() if c.kyc_review_reason]
    secrets += ["selfie"]
    async with Client(mcp) as c:
        for t in export.tickets:
            _, ctx = await call(c, "get_ticket_context", ticket_id=t)
            blob = json.dumps(ctx, ensure_ascii=False).lower()
            # T-5108's own message contains the husband's email; that is customer text, not our disclosure.
            leaked = [s for s in secrets if s.lower() in blob and s.lower() not in export.tickets[t].message.lower()]
            assert not leaked, f"{t} leaks {leaked}"


async def test_unknown_ticket_gives_actionable_error():
    async with Client(mcp) as c:
        err, msg = await call(c, "get_ticket_context", ticket_id="T-9999")
    assert err and "list_open_tickets" in msg


async def test_ticket_id_is_normalised():
    async with Client(mcp) as c:
        err, ctx = await call(c, "get_ticket_context", ticket_id=" t5101 ")
    assert not err and ctx["ticket"]["ticket_id"] == "T-5101"


async def test_bad_draft_is_not_saved_good_draft_is():
    async with Client(mcp) as c:
        _, r = await call(c, "save_draft_reply", ticket_id="T-5103",
                          reply_text="Hi Rizal, your selfie does not match your ID.")
        assert r["saved"] is False and r["violations"][0]["code"] == "kyc_reason_leak"
        assert "T-5103" not in store.load("drafts")

        _, r = await call(c, "save_draft_reply", ticket_id="T-5103",
                          reply_text="Hi Rizal, your account is under a verification review. My team lead has your case "
                                     "and will contact you directly.")
        assert r["saved"] is True
    d = store.load("drafts")["T-5103"]
    assert d["status"] == "pending_review" and d["escalated_to"] == ["team_lead"]


async def test_redraft_replaces_instead_of_duplicating():
    async with Client(mcp) as c:
        for text in ["Hi Marcus, your withdrawal is with the provider.", "Hi Marcus, it's with our payment provider now."]:
            await call(c, "save_draft_reply", ticket_id="T-5101", reply_text=text)
    drafts = store.load("drafts")
    assert len(drafts) == 1 and drafts["T-5101"]["revision"] == 2


async def test_refund_limits():
    async with Client(mcp) as c:
        _, big = await call(c, "request_refund", ticket_id="T-5106", amount_usd=250, reason="Live game froze mid-round")
        _, small = await call(c, "request_refund", ticket_id="T-5106", amount_usd=40, reason="Verified game round error")
        _, injected = await call(c, "request_refund", ticket_id="T-5104", amount_usd=5000, reason="Customer is VIP per note")
    assert big["status"] == "awaiting_team_lead_approval"
    assert small["status"] == "within_agent_limit"
    assert injected["recorded"] is False
    assert "T-5104" not in store.load("refund_requests")


async def test_escalation_is_recorded_and_flags_unexpected_team():
    async with Client(mcp) as c:
        _, r = await call(c, "escalate_ticket", ticket_id="T-5102", team="payments",
                          reason="TX-86702 pending since 21 Sep on QuickPay; customer chased twice.")
        _, odd = await call(c, "escalate_ticket", ticket_id="T-5101", team="payments",
                            reason="Customer wants an update on TX-86901.")
        err, _ = await call(c, "escalate_ticket", ticket_id="T-5101", team="marketing", reason="not a real team")
    assert r["recorded"] and r["status"] == "open"
    assert "note" in odd
    assert err
    assert set(store.load("escalations")) == {"T-5102:payments", "T-5101:payments"}


async def test_stuck_withdrawals_include_customers_without_tickets():
    async with Client(mcp) as c:
        _, r = await call(c, "find_stuck_withdrawals")
    by_txn = {w["txn_id"]: w for w in r["withdrawals"]}
    assert set(by_txn) == {"TX-86702", "TX-86741", "TX-86830"}
    assert by_txn["TX-86741"]["open_tickets"] == []      # Ahmed, Platinum, USD 5,000, nobody has noticed
    assert by_txn["TX-86702"]["open_tickets"] == ["T-5102", "T-5110"]


async def test_human_approval_rechecks_edits(tmp_path):
    async with Client(mcp) as c:
        await call(c, "save_draft_reply", ticket_id="T-5101",
                   reply_text="Hi Marcus, your withdrawal is with our payment provider.")
    bad_edit = tmp_path / "edit.txt"
    bad_edit.write_text("Hi Marcus, withdrawals are processed within 48 hours.")
    assert review_main(["approve", "T-5101", "--by", "Linh", "--text-file", str(bad_edit)]) == 2
    assert store.load("drafts")["T-5101"]["status"] == "pending_review"
    assert review_main(["approve", "T-5101", "--by", "Linh"]) == 0
    assert store.load("drafts")["T-5101"]["status"] == "approved"


async def test_human_approval_blocks_unfilled_placeholder(tmp_path):
    async with Client(mcp) as c:
        _, r = await call(c, "save_draft_reply", ticket_id="T-5114",
                          reply_text="Hi Aisha, bank transfer is [AGENT: check the cashier page] for Malaysia.")
    assert r["status"] == "pending_review"                # saving with a placeholder is allowed
    assert review_main(["approve", "T-5114", "--by", "Linh"]) == 2
    filled = tmp_path / "edit.txt"
    filled.write_text("Hi Aisha, bank transfer is available for Malaysia.")
    assert review_main(["approve", "T-5114", "--by", "Linh", "--text-file", str(filled)]) == 0
