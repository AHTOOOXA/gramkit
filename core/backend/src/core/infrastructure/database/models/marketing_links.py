from datetime import date

from sqlalchemy import JSON, Boolean, Date, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from core.infrastructure.database.models.base import Base, CreatedAtMixin, TableNameMixin, UpdatedAtMixin, int_pk


class MarketingLink(Base, TableNameMixin, CreatedAtMixin, UpdatedAtMixin):
    """A registered acquisition code: one per external placement (post, ad, partner).

    The code travels in the link (`?startapp=r-<code>` / `?start=<code>`) and ends up in
    `users.referral_code` on the user's first touch, so per-code results come from there.
    """

    id: Mapped[int_pk]
    code: Mapped[str] = mapped_column(String(40), unique=True)  # a-z, 0-9, _
    channel: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )  # where it ran, e.g. "Partner channel, post 3"
    price_rub: Mapped[float | None] = mapped_column(Float, nullable=True)  # what the placement cost
    published_on: Mapped[date | None] = mapped_column(Date, nullable=True)  # day the post went out: D14 starts here
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Owner alerts already sent for this link ("first_user", "first_payment", "day_1", ...).
    alerts_sent: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
