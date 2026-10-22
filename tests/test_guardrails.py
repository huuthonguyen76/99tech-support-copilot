"""Each blocking rule gets one draft that must be blocked and one realistic
draft that must pass, so the checks are proven to catch the bad case without
blocking normal replies."""

import pytest

from support_copilot.guardrails import check_draft
from support_copilot.policy import assess


def blocking(export, ticket_id, text):
    t = export.tickets[ticket_id]
    return {v.code for v in check_draft(text, t, assess(t, export), export) if v.blocking}


BAD = [
    ("T-5103", "Hi Rizal, your selfie didn't match your ID, please upload again.", "kyc_reason_leak"),
    ("T-5103", "Hi Rizal, the review will be done within 2 business days.", "kyc_timeline"),
    ("T-5108", "Hi Priya, Rahul Nair withdrew USD 600 this month.", "other_customer_data"),
    ("T-5108", "Hi Priya, your husband made one withdrawal recently.", "third_party_disclosure"),
    ("T-5106", "Hi Hannah, I've refunded the USD 250 to your account.", "refund_promised"),
    ("T-5106", "Hi Hannah, as a Gold member we will refund your bet.", "refund_promised"),
    ("T-5109", "Hi Grace, withdrawals can take up to 5 days, please wait.", "outdated_policy"),
    ("T-5101", "Hi Marcus, withdrawals are processed within 48 hours.", "outdated_policy"),
    ("T-5111", "Hi Oliver, you can use the bonus on any game.", "outdated_policy"),
    ("T-5102", "Hi Somchai, your money will arrive by Friday.", "unverified_promise"),
    ("T-5102", "Hi Somchai, this should be fixed by 2 Oct.", "unverified_promise"),
    ("T-5115", "Hi Wei, the reload bonus is 50% up to USD 200 from 1 Oct.", "draft_promo_terms"),
    ("T-5105", "Hi Ethan, we've closed your account. Here's a free spins offer for when you return.", "promo_to_at_risk_customer"),
    ("T-5104", "Hi Tomasz, as a VIP your USD 5,000 refund is on its way.", "followed_injected_instruction"),
    ("T-5107", "Hi Ha, your deposit failed and will be reversed in 3-5 business days.", "wrong_language"),
    ("T-5101", "", "empty"),
]


@pytest.mark.parametrize("ticket_id,text,code", BAD)
def test_bad_draft_is_blocked(export, ticket_id, text, code):
    assert code in blocking(export, ticket_id, text)


GOOD = {
    "T-5101": "Hi Marcus, I've checked your USD 250 withdrawal. We sent it to our payment provider on 27 Sep and it's "
              "now with them. Payouts usually take 1-3 business days to arrive after that, depending on the provider. "
              "If it hasn't reached you after that window, reply here and we'll trace it with our Payments team.",
    "T-5103": "Hi Rizal, I'm sorry you've had to ask more than once. Your account is going through a verification "
              "review, and withdrawals are paused until it's complete. Your balance is safe and remains in your account. "
              "I've passed your message to my team lead, who will contact you directly. We'll also contact you if we "
              "need anything from you for the review.",
    "T-5107": "Chào chị Hà, em đã kiểm tra giao dịch nạp 500.000 đồng của chị ngày 27/9. Giao dịch này không thành công "
              "do lỗi kết nối với ngân hàng nên không được cộng vào số dư. Nếu ngân hàng đã trừ tiền, nhà cung cấp thanh "
              "toán sẽ hoàn lại vào tài khoản nguồn, thường trong vòng 3-5 ngày làm việc.",
    "T-5108": "Hi Priya, I understand this is worrying. We can only discuss an account with the account holder, so I "
              "can't share any information about another person or confirm whether they have an account with us. If "
              "you're concerned about someone's gambling, independent support organisations can help.",
    "T-5115": "Hi Wei, thanks for asking. We don't have a reload bonus to share details on yet. When a new promotion "
              "goes live, its full terms will be published on our promotions page.",
    "T-5106": "Hi Hannah, I'm sorry the game froze mid-round. I've asked our team to check the round in our records "
              "and passed your refund request to my team lead for review. We'll get back to you with the outcome.",
}


@pytest.mark.parametrize("ticket_id", sorted(GOOD))
def test_good_draft_passes(export, ticket_id):
    assert blocking(export, ticket_id, GOOD[ticket_id]) == set()


# Regressions from the first real run: all three were blocked, wrongly.
FALSE_POSITIVES_RUN_1 = {
    "T-5105": "Hi Ethan, thank you for telling us. We've passed your request to our team to close your account through "
              "our self-exclusion process. If you'd like to talk to someone, Gambling Help Online offers free, "
              "confidential support 24/7.",
    "T-5111": "Hi Oliver, first, I need to correct something. When you asked us on 14 September, we told you the bonus "
              "could be used on any game. That wasn't right, and I'm sorry. Table games such as blackjack count 10%. "
              "I've passed your case to my team lead.",
    "T-5109": "Hi Grace, I also need to correct our earlier reply: it said withdrawals can take up to 5 days, which "
              "wasn't accurate. Once confirmed, payouts usually take 1-3 business days to show up.",
}


# Run 2 still blocked this softer correction.
FALSE_POSITIVES_RUN_1["T-5111-run2"] = (
    "Hi Oliver, I need to correct something we told you on 14 September. We said you could use your welcome bonus on "
    "any game, and that wasn't fully right, I'm sorry. Table games like blackjack count only 10%. I've passed your "
    "case to my team lead.")


@pytest.mark.parametrize("ticket_id", sorted(FALSE_POSITIVES_RUN_1))
def test_run_1_false_positives_now_pass(export, ticket_id):
    assert blocking(export, ticket_id.split("-run")[0], FALSE_POSITIVES_RUN_1[ticket_id]) == set()


def test_correction_is_still_a_warning(export):
    t = export.tickets["T-5109"]
    vs = check_draft(FALSE_POSITIVES_RUN_1["T-5109"], t, assess(t, export), export)
    assert any(v.code == "outdated_policy" and not v.blocking for v in vs)
