"""Referral codes (a link's `r-<code>` / `?start=<code>`) and which ones mean acquisition.

A code in a link is stored as the user's first-touch acquisition source (``users.referral_code``)
and counted on the admin Marketing screen. Codes on the app's own links to users it already has
(notification buttons, broadcasts) say what brought a user back, not where they came from, so
they're listed here and passed to ``CoreRequestsService(internal_referal_ids=...)``: they're never
stored as a source, listed or registrable. A new link to existing users gets its code added here.
"""

INTERNAL_REFERRAL_CODES = frozenset(
    {
        "dailynotification",  # tgbot/keyboards/notification_keyboards.py (notifications + "daily" broadcast button)
    }
)
