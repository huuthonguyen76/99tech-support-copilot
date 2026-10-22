"""Golden expectations for every open ticket, written by hand from the handbook
and the data before looking at engine output. If the engine disagrees, one of
them is wrong and the test says which ticket."""

from datetime import datetime, timezone

import pytest

from support_copilot.policy import assess, business_days_between, detect_language

# ticket: (priority, category, language, escalate_to, codes that must be present)
EXPECTED = {
    "T-5101": ("P3", "withdrawal", "en", [], {"withdrawal_processing"}),
    "T-5102": ("P2", "withdrawal", "en", ["payments"], {"withdrawal_pending_overdue", "duplicate_open_ticket"}),
    "T-5103": ("P1", "kyc", "en", ["team_lead"], {"legal_or_chargeback_threat", "kyc_under_review", "prior_reply_broke_policy"}),
    "T-5104": ("P1", "bonus", "en", ["team_lead"], {"instructions_in_customer_message", "bonus_terms"}),
    "T-5105": ("P1", "responsible_gambling", "en", ["team_lead"], {"gambling_harm", "deposit_pattern"}),
    "T-5106": ("P2", "complaint", "en", ["team_lead"], {"refund_request"}),
    "T-5107": ("P2", "deposit", "vi", [], {"deposit_failed", "non_english"}),
    "T-5108": ("P2", "privacy", "en", [], {"third_party_account_request"}),
    "T-5109": ("P3", "withdrawal", "en", [], {"withdrawal_completed", "prior_reply_broke_policy"}),
    "T-5110": ("P2", "withdrawal", "en", ["payments"], {"withdrawal_pending_overdue", "duplicate_open_ticket"}),
    "T-5111": ("P2", "bonus", "en", ["team_lead"], {"bonus_terms", "misinformed_by_us"}),
    "T-5112": ("P3", "account_access", "en", ["team_lead"], {"account_recovery_no_policy"}),
    "T-5113": ("P3", "kyc", "en", [], {"kyc_pending"}),
    "T-5114": ("P4", "deposit", "en", [], {"knowledge_gap"}),
    "T-5115": ("P4", "bonus", "en", [], {"unpublished_promotion"}),
}


def test_every_open_ticket_has_an_expectation(export):
    assert {t.ticket_id for t in export.open_tickets()} == set(EXPECTED)


@pytest.mark.parametrize("ticket_id", sorted(EXPECTED))
def test_assessment_matches_hand_analysis(export, ticket_id):
    priority, category, lang, escalate, codes = EXPECTED[ticket_id]
    a = assess(export.tickets[ticket_id], export)
    assert a.priority == priority
    assert a.category == category
    assert a.reply_language == lang
    assert sorted(a.escalate_to) == sorted(escalate)
    assert codes <= a.codes(), f"missing {codes - a.codes()}"


def test_every_open_ticket_is_past_first_reply_target(export):
    for t in export.open_tickets():
        assert "first_reply_overdue" in assess(t, export).codes()


def test_refund_over_limit_needs_team_lead_even_for_gold(export):
    a = assess(export.tickets["T-5106"], export)
    assert export.customers["C-1002"].vip_tier == "gold"
    assert a.refund_requested_usd == 250
    assert "team_lead" in a.escalate_to


def test_bonus_maths(export):
    detail = next(f.detail for f in assess(export.tickets["T-5111"], export).findings if f.code == "bonus_terms")
    assert "USD 3,000" in detail          # 30 x USD 100
    assert "19 Sep" in detail             # credited 5 Sep + 14 days
    assert "EXPIRED" in detail
    assert "USD 200" in detail            # USD 2,000 on blackjack counts 10%


def test_gambling_harm_blocks_self_resolution(export):
    a = assess(export.tickets["T-5105"], export)
    assert not a.agent_may_resolve
    assert any("bonuses" in m for m in a.must_not)


def test_kyc_reason_never_appears_in_assessment(export):
    reason = export.customers["C-1011"].kyc_review_reason.lower()
    blob = str(assess(export.tickets["T-5103"], export).to_dict()).lower()
    assert reason not in blob
    assert "selfie" not in blob


def test_injected_instruction_does_not_become_an_action(export):
    a = assess(export.tickets["T-5104"], export)
    assert a.priority == "P1"
    assert "payments" not in a.escalate_to


def test_business_days_skips_weekends():
    sat = datetime(2026, 9, 26, 12, tzinfo=timezone.utc)
    tue = datetime(2026, 9, 29, 9, tzinfo=timezone.utc)
    assert business_days_between(sat, tue) == 2


@pytest.mark.parametrize("text,lang", [
    ("Tôi đã nạp 500.000 đồng hôm qua", "vi"),
    ("ถอนเงินยังไม่เข้า", "th"),
    ("Where is my money?", "en"),
])
def test_detect_language(text, lang):
    assert detect_language(text) == lang


def test_now_is_configurable(export, monkeypatch):
    monkeypatch.setenv("SUPPORT_NOW", "2026-09-21T20:00:00Z")  # 6 h after the T-5102 withdrawal
    t = export.tickets["T-5102"]
    codes = assess(t, export).codes()
    assert "withdrawal_pending" in codes and "withdrawal_pending_overdue" not in codes
