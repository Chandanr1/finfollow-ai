"""
app/prompts/stage_prompts.py
─────────────────────────────
Per-escalation-stage tone instructions injected into the LLM prompt.
Each stage has distinct tone guidelines and content requirements.
"""

from __future__ import annotations

from typing import Dict

STAGE_TONE_PROMPTS: Dict[int, str] = {
    1: """
TONE: Warm & Friendly (Stage 1 — 1-7 days overdue)

Write a warm, courteous reminder. Assume the client may have simply overlooked the invoice.
- Open with a friendly greeting
- Gently mention the invoice is overdue
- Express confidence that payment will be made soon
- Thank them for their business
- Keep it brief and non-threatening
- End with a warm sign-off

Do NOT mention: legal action, penalties, credit scores, or account suspension.
""",

    2: """
TONE: Polite but Firm (Stage 2 — 8-14 days overdue)

Write a polite but clearly firm follow-up. The client has ignored the first reminder.
- Acknowledge previous communication (second notice)
- State clearly that payment is now {days_overdue} days overdue
- Mention that late payment fees may apply per contract terms
- Request immediate payment or a payment arrangement
- Provide the payment link prominently
- Maintain professionalism but be assertive

Do NOT: threaten legal action yet, or be hostile.
""",

    3: """
TONE: Formal & Serious (Stage 3 — 15-21 days overdue)

Write a formal, serious demand letter tone. The situation is now serious.
- Open formally (no pleasantries)
- Reference the outstanding invoice and the number of days overdue
- Cite contractual payment obligations
- State that the account is being reviewed for escalation
- Specify a clear payment deadline (5 business days from today)
- Mention potential consequences: service suspension, credit reporting, collections referral
- Request immediate contact if there is a dispute

Tone: professional, formal, no casual language.
""",

    4: """
TONE: Stern & Urgent (Stage 4 — 22-30 days overdue)

Write a final notice email. This is the last communication before legal/collections action.
- State clearly this is the FINAL NOTICE
- List the exact amount due including any accrued interest/fees if applicable
- State explicitly that failure to pay within 48-72 hours will result in referral to collections/legal
- Do NOT offer further extensions
- Include contact details for last-chance dispute resolution
- Formal closing only

Tone: direct, stern, urgent, completely professional — no threats beyond factual consequences.
""",

    5: """
TONE: N/A — DO NOT GENERATE EMAIL (Stage 5 — >30 days overdue)

This invoice must NOT receive an email. Return a JSON with:
- requires_legal_review: true
- body: "ESCALATED TO LEGAL REVIEW — NO EMAIL SENT"
- subject: "LEGAL REVIEW — Invoice {invoice_id}"
- All other fields populated from invoice data

The account has been flagged for immediate legal/manual finance review.
""",
}


def get_tone_prompt(stage: int, **kwargs) -> str:
    """
    Return the tone prompt for a given escalation stage.
    Safely formats any available kwargs into the prompt.
    """
    prompt = STAGE_TONE_PROMPTS.get(stage, STAGE_TONE_PROMPTS[1])
    try:
        return prompt.format(**kwargs)
    except KeyError:
        return prompt  # Return unformatted if kwargs don't match
