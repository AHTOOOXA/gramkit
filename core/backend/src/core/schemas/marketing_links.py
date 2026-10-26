"""Admin marketing links: a registry of acquisition codes with ready links and results."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# The code rides in `?startapp=r-<code>` (where '-' separates params) and is stored in
# users.referral_code (varchar 40).
CODE_PATTERN = re.compile(r"^[a-z0-9_]{2,40}$")

# paid_back: revenue has covered the price; in_progress: not yet, and it's within its first 14 days;
# not_paid_back: not yet, 14 days on.
Payback = Literal["paid_back", "in_progress", "not_paid_back"]


class MarketingLinkStats(BaseModel):
    users: int = 0
    # Users with at least one activation event (the app defines it; default: opened the app).
    activated: int = 0
    payers: int = 0
    revenue_rub: float = 0.0  # all time, net of refunds, Stars/USD converted at fixed rates
    revenue_purchases_rub: float = 0.0  # the part the users paid themselves, without automatic renewals
    revenue_d14_rub: float = 0.0  # paid within 14 days of start_date
    first_user_at: datetime | None = None
    last_user_at: datetime | None = None
    first_payment_at: datetime | None = None
    # Retention: of the users signed up at least N days ago, those active N or more days after
    # signing up (the app defines "active"; default: in the app).
    eligible_d1: int = 0
    returned_d1: int = 0
    eligible_d7: int = 0
    returned_d7: int = 0
    eligible_d30: int = 0
    returned_d30: int = 0


class MarketingLinkItem(BaseModel):
    id: int | None  # None: the code is in users but not in the registry (pre-registry)
    code: str
    registered: bool
    channel: str | None = None
    price_rub: float | None = None
    published_on: date | None = None
    start_date: date | None = None  # published_on, or the first sign-up for a code without it
    is_archived: bool = False
    created_at: datetime | None = None
    app_link: str
    bot_link: str
    stats: MarketingLinkStats
    cac_rub: float | None = None  # price / users
    ltv_rub: float | None = None  # all-time revenue / users
    roas: float | None = None  # all-time revenue / price
    payback: Payback | None = None  # None without a price
    payback_days: int | None = None  # day (1 = the start date) the revenue first covered the price


class MarketingLinkListResponse(BaseModel):
    items: list[MarketingLinkItem]


class MarketingLinkCreateRequest(BaseModel):
    code: str
    channel: str | None = Field(default=None, max_length=120)
    price_rub: float | None = Field(default=None, ge=0)
    published_on: date | None = None

    @field_validator("code")
    @classmethod
    def _code_format(cls, value: str) -> str:
        value = value.strip().lower()
        if not CODE_PATTERN.match(value):
            raise ValueError("2–40 characters: lowercase latin letters, digits and _ only")
        return value


class MarketingLinkUpdateRequest(BaseModel):
    channel: str | None = Field(default=None, max_length=120)
    price_rub: float | None = Field(default=None, ge=0)
    published_on: date | None = None
    is_archived: bool | None = None
