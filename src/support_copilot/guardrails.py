"""Checks a draft reply against policy before it can be saved for review.

Blocking violations stop the draft from being saved; the model gets the list
back and rewrites. Warnings are saved with the draft so the reviewer sees them.
These checks are a safety net, not a substitute for the human reviewer.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from .data import Export, Ticket
from .policy import AGENT_REFUND_LIMIT_USD, Assessment, OUTDATED_POLICY_PHRASES, detect_language


@dataclass
class Violation:
    code: str
    blocking: bool
    detail: str


KYC_LEAK_TERMS = [
    r"selfie", r"does(n'?t| not) match", r"third[- ]party", r"altered", r"fake", r"forged",
    r"suspicious", r"fraud", r"possible .* use", r"our checks (found|showed)",
]
REFUND_DONE = [
    r"\b(i|we)('ve| have)? (refunded|credited)\b",
    r"\b(issued|processed|approved|arranged) (a|your|the) (refund|credit|compensation|goodwill)",
    r"\b(has|have) been (refunded|credited)\b",
    r"\bwill (refund|credit|reimburse|compensate)\b",
    r"\byou('ll| will) (receive|get) (a |your )?(refund|credit|compensation)",
]
DATE_PROMISES = [
    r"\b(arrive|reach you|be (paid|credited|resolved|fixed|sorted|completed|unblocked))\b[^.]{0,30}\b(today|tomorrow|tonight|by \w+day)\b",
    r"\b(2 oct|oct(ober)? 2|2nd (of )?october)\b",
    r"\bguarantee",
    r"\bwill (definitely |certainly )?(arrive|be (paid|credited|resolved|fixed|completed|reopened|unblocked))\b",
]
DRAFT_PROMO_TERMS = [r"50\s?%", r"usd\s?200", r"\$200", r"once per week", r"1 oct"]
CORRECTION_MARKERS = (r"\b(correct|(wasn'?t|isn'?t|not) (fully |quite |entirely |completely )?(right|accurate|correct)|incorrect|inaccurate|"
                      r"wrong|mistake|apologi[sz]e for)")
REOPEN_TERMS = [r"reopen", r"re-open", r"lift (the|your) (exclusion|block)", r"unblock"]


def _hit(patterns: list[str], text: str) -> str | None:
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


def check_draft(text: str, ticket: Ticket, assessment: Assessment, export: Export) -> list[Violation]:
    out: list[Violation] = []
    customer = export.customers[ticket.customer_id]
    codes = assessment.codes()
    lowered = text.lower()

    if not text.strip():
        return [Violation("empty", True, "Draft is empty.")]

    # 1. KYC reason must never reach the customer.
    if customer.kyc_status != "verified":
        stop = {"account", "possible", "appears", "customer", "review"}
        reason_words = [w for w in re.findall(r"[a-z]{5,}", customer.kyc_review_reason.lower()) if w not in stop]
        leaked = _hit(KYC_LEAK_TERMS, text) or next((w for w in reason_words if w in lowered), None)
        if leaked:
            out.append(Violation("kyc_reason_leak", True,
                                 f"Draft hints at the KYC review reason ('{leaked}'). Say only that the review is in progress."))
        if re.search(r"\b\d+\s*(business |working )?(days?|hours?)\b", lowered) and "kyc" in assessment.category:
            out.append(Violation("kyc_timeline", True, "Draft gives a KYC review timeline. Handbook v2 gives none."))

    # 2. Never disclose anything about another customer.
    for other in export.customers.values():
        if other.customer_id == customer.customer_id:
            continue
        for value in (other.email, other.full_name, other.phone, other.customer_id):
            if value and value.lower() in lowered:
                out.append(Violation("other_customer_data", True,
                                     f"Draft contains another customer's details ({other.customer_id}). Remove it."))
                break
    for t in export.transactions:
        if t.customer_id != customer.customer_id and t.txn_id.lower() in lowered:
            out.append(Violation("other_customer_data", True, f"Draft references {t.txn_id}, which belongs to another customer."))
    if "third_party_account_request" in codes:
        m = re.search(r"\b(he|she|your (husband|wife|partner))\b[^.]{0,60}\b(withdr|deposit|account|balance)", text, re.IGNORECASE)
        if m:
            out.append(Violation("third_party_disclosure", True,
                                 f"Draft talks about the other person's account activity ('{m.group(0)}')."))

    # 3. Refunds: never say one was issued; never promise one over the limit.
    done = _hit(REFUND_DONE, text)
    if done:
        out.append(Violation("refund_promised", True,
                             f"Draft says money was or will be refunded/credited ('{done}'). Refunds go through request_refund "
                             f"and anything over USD {AGENT_REFUND_LIMIT_USD} needs team lead approval first."))

    # 4. Outdated or wrong policy (handbook v1, past bad replies).
    for pattern, why in OUTDATED_POLICY_PHRASES.items():
        if pattern.startswith("selfie"):
            continue  # covered by the KYC check above, with fewer false positives
        if pattern.startswith(r"3\s*") and "deposit_failed" in codes:
            continue  # 3-5 business days is the correct deposit-reversal window
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            # Quoting the old answer in order to correct it is what we want agents to do.
            window = text[max(0, m.start() - 160): m.end() + 120]
            correcting = re.search(CORRECTION_MARKERS, window, re.IGNORECASE)
            out.append(Violation("outdated_policy", not correcting,
                                 f"'{m.group(0)}': {why}" + (" (quoted as a correction: check it reads clearly)" if correcting else "")))

    # 5. Date and outcome promises.
    promise = _hit(DATE_PROMISES, text)
    if promise:
        out.append(Violation("unverified_promise", True,
                             f"Draft promises a date or outcome ('{promise}'). Handbook v2: don't promise what you can't verify."))

    # 6. Unpublished promotions.
    if "unpublished_promotion" in codes:
        leak = _hit(DRAFT_PROMO_TERMS, text)
        if leak:
            out.append(Violation("draft_promo_terms", True, f"Draft quotes unpublished promotion terms ('{leak}')."))

    # 7. Self-exclusion and gambling harm.
    if customer.self_excluded or "gambling_harm" in codes:
        reopen = _hit(REOPEN_TERMS, text)
        if reopen and not re.search(r"(won'?t|will not|cannot|can'?t|not be able to) (be )?" + re.escape(reopen), text, re.IGNORECASE):
            out.append(Violation("reopen_offered", True, f"Draft suggests reopening a self-excluded account ('{reopen}')."))
        if re.search(r"\b(bonus(es)?|promotions?|free spins?|special offers?|an offer|offer you)\b", text, re.IGNORECASE):
            out.append(Violation("promo_to_at_risk_customer", True, "Never mention bonuses or offers to a customer at risk of gambling harm."))

    # 8. Injected instructions must not leak into the reply.
    if "instructions_in_customer_message" in codes:
        if re.search(r"5[,.]?000|vip", text, re.IGNORECASE):
            out.append(Violation("followed_injected_instruction", True,
                                 "Draft echoes the amount or VIP status claimed by text inside the customer message."))

    # 9. Language.
    expected = assessment.reply_language
    if expected != "en" and detect_language(text) != expected:
        out.append(Violation("wrong_language", True, f"Customer wrote in `{expected}`; reply in the same language."))

    # 10. Non-blocking hygiene.
    if customer.email.lower() in lowered or customer.phone in text:
        out.append(Violation("contains_contact_details", False, "Draft repeats the customer's contact details; usually unnecessary."))
    if re.search(r"\b(TX|T)-\d{4,5}\b", text) and not re.search(rf"\b{re.escape(ticket.ticket_id)}\b", text):
        out.append(Violation("internal_ids", False, "Draft contains internal transaction IDs; check they are useful to the customer."))
    if customer.given_name.lower() not in lowered:
        out.append(Violation("no_name", False, f"Draft doesn't address the customer by name ({customer.given_name})."))
    if assessment.escalate_to and not re.search(r"team|colleague|specialist|lead|payments|escalat|chuyển|ทีม", text, re.IGNORECASE):
        out.append(Violation("escalation_not_mentioned", False,
                             "Ticket is escalated but the draft doesn't tell the customer a specialist team has it."))
    return out


def as_dicts(violations: list[Violation]) -> list[dict]:
    return [asdict(v) for v in violations]
