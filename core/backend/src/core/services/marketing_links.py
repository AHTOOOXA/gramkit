"""Admin marketing links (acquisition attribution): register a code per external placement,
hand out its Mini App / bot links, and show what it brought.

Results come from users.referral_code (first touch), so codes used before the registry existed
are listed too, unregistered, to be given a channel name. Codes of the app's own links to existing
users (notifications, broadcasts; ``CoreRequestsService.internal_referal_ids``) are not acquisition
and never listed or registrable.

What counts as *activity* (activated users, return after N days) is the app's call: it passes a
``MarketingLinksConfig`` to ``CoreRequestsService(..., marketing_links_config=...)``. Without one,
activity = the user opened the app (``users.last_activity_date``).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import CompoundSelect, Select
from sqlalchemy.exc import IntegrityError

from core.exceptions import MarketingCodeNotAllowedException, MarketingLinkNotFoundException
from core.infrastructure.config import settings
from core.infrastructure.database.models import MarketingLink
from core.infrastructure.database.repo.marketing_links import default_activity
from core.infrastructure.telegram.admin_messages import esc, fmt_money, tags
from core.schemas.marketing_links import (
    MarketingLinkCreateRequest,
    MarketingLinkItem,
    MarketingLinkListResponse,
    MarketingLinkStats,
    MarketingLinkUpdateRequest,
)
from core.schemas.users import UserSchema
from core.services.base import BaseService

D14 = timedelta(days=14)
DIGEST_DAYS = (1, 7, 14)  # owner digests this many days after the publish date

# Rough fixed rates to put every payment in rubles, good enough to tell whether a placement paid
# back: Stars at the developer payout (~$0.013/★), dollars at ~85 ₽. An app overrides them with
# ``MarketingLinksConfig.rub_per_unit``.
DEFAULT_RUB_PER_UNIT: Mapping[str, float] = {"RUB": 1.0, "USD": 85.0, "XTR": 1.1}

# A zero-argument factory of a SELECT (or UNION ALL) whose rows are labelled (user_id, at).
ActivityQuery = Callable[[], Select | CompoundSelect]


@dataclass(frozen=True)
class MarketingLinksConfig:
    """How an app measures its marketing links. Passed once to ``CoreRequestsService``.

    The hooks are query fragments, not callbacks: they are joined per user inside one aggregate
    query (a deliberate exception to the admin ``register_*`` registries, see the core-promotion
    plan, Phase 4 P4-D2).
    """

    # Users with any row count as `activated`. None: they opened the app.
    activation: ActivityQuery | None = None
    # Rows that count for return (retention): the latest `at` per user. None: ``activation``.
    activity: ActivityQuery | None = None
    # English, used in owner digests: "40% opened the app".
    activation_label: str = "opened the app"
    rub_per_unit: Mapping[str, float] = field(default_factory=lambda: dict(DEFAULT_RUB_PER_UNIT))


def app_link(base: str, code: str) -> str:
    """Opens the Mini App; the app records `r-<code>` on the first session."""
    # TODO: let a link pick its landing screen — the app can route `startapp=...-p-<page>`
    # (useAppInit.ts), e.g. a post opening a specific screen.
    return f"{base}?startapp=r-{code}"


def bot_link(base: str, code: str) -> str:
    """Opens the bot chat; /start records the code right away."""
    return f"{base}?start={code}"


def _economics(
    price: float | None, stats: MarketingLinkStats, start: datetime | None, payments: list[tuple[datetime, float]]
) -> dict[str, Any]:
    """CAC, LTV (revenue per user), ROAS (revenue / price) and payback: the day the running revenue
    first covered the price or, until it does, whether the code is still in its first 14 days."""
    users = stats.users
    payback, payback_days = None, None
    if price:
        running = 0.0
        for paid_at, rub in payments:
            running += rub
            if running >= price:
                payback, payback_days = "paid_back", max((paid_at - start).days + 1, 1) if start else None
                break
        else:
            late = start is not None and datetime.now(UTC) >= start + D14
            payback = "not_paid_back" if late else "in_progress"
    return {
        "cac_rub": round(price / users, 2) if price is not None and users else None,
        "ltv_rub": round(stats.revenue_rub / users, 2) if users else None,
        "roas": round(stats.revenue_rub / price, 2) if price else None,
        "payback": payback,
        "payback_days": payback_days,
    }


class MarketingLinksService(BaseService):
    def _config(self) -> MarketingLinksConfig:
        return self.services.marketing_links_config or MarketingLinksConfig()

    def _internal_codes(self) -> frozenset[str]:
        """The app's own link codes (re-engagement, not acquisition)."""
        return frozenset(self.services.internal_referal_ids)

    def _link_bases(self) -> tuple[str, str]:
        """(Mini App URL, bot URL). One seam, so core-only tests needn't load app settings."""
        return settings.web.app_url, settings.bot.url

    async def list_links(self) -> MarketingLinkListResponse:
        cfg = self._config()
        activation = (cfg.activation or default_activity)()
        activity = (cfg.activity or cfg.activation or default_activity)()
        stats = await self.repo.marketing_links.stats_by_code(activation=activation, activity=activity)
        links = await self.repo.marketing_links.list_all()
        published_on = {link.code: link.published_on for link in links}
        app_base, bot_base = self._link_bases()
        internal = self._internal_codes()

        # A code's clock starts the day the post went out or, with no date set (e.g. codes from
        # before this page), at its first sign-up.
        def start_of(code: str) -> datetime | None:
            if published_on.get(code):
                return datetime.combine(published_on[code], time(), tzinfo=UTC)
            return stats.get(code, {}).get("first_user_at")

        payments: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
        purchases: dict[str, float] = defaultdict(float)  # without subscription auto-renewals
        for payment in await self.repo.marketing_links.payments_by_code():
            rub = payment.amount * cfg.rub_per_unit.get(payment.currency, 0.0)
            payments[payment.code].append((payment.created_at, rub))
            if payment.is_purchase:
                purchases[payment.code] += rub

        def item(code: str, link: MarketingLink | None) -> MarketingLinkItem:
            start = start_of(code)
            revenue = sum(rub for _, rub in payments[code])
            revenue_d14 = sum(rub for paid_at, rub in payments[code] if start and paid_at < start + D14)
            code_stats = MarketingLinkStats(
                **stats.pop(code, {}),
                revenue_rub=round(revenue, 2),
                revenue_purchases_rub=round(purchases[code], 2),
                revenue_d14_rub=round(revenue_d14, 2),
                first_payment_at=payments[code][0][0] if payments[code] else None,
            )
            price = link.price_rub if link else None
            return MarketingLinkItem(
                id=link.id if link else None,
                code=code,
                registered=link is not None,
                channel=link.channel if link else None,
                price_rub=price,
                published_on=link.published_on if link else None,
                start_date=start.date() if start else None,
                is_archived=link.is_archived if link else False,
                created_at=link.created_at if link else None,
                app_link=app_link(app_base, code),
                bot_link=bot_link(bot_base, code),
                stats=code_stats,
                **_economics(price, code_stats, start, payments[code]),
            )

        items = [item(link.code, link) for link in links]
        for code, _ in sorted(stats.items(), key=lambda kv: -kv[1]["users"]):
            if code not in internal:
                items.append(item(code, None))
        return MarketingLinkListResponse(items=items)

    async def create(self, actor: UserSchema, body: MarketingLinkCreateRequest) -> MarketingLinkItem:
        """Register a code. Raises ``MarketingCodeNotAllowedException`` for one of the app's own
        codes or a code that's already registered (also when a concurrent request just took it)."""
        if body.code in self._internal_codes():
            raise MarketingCodeNotAllowedException("This code is used by the app's own notifications")
        if await self.repo.marketing_links.get_by_code(body.code):
            raise MarketingCodeNotAllowedException("This code is already registered")
        try:
            # A savepoint: a concurrent create of the same code fails on the unique constraint
            # without poisoning the request transaction, and becomes the same 400.
            async with self.repo.session.begin_nested():
                link = await self.repo.marketing_links.create(
                    {
                        "code": body.code,
                        "channel": (body.channel or "").strip() or None,
                        "price_rub": body.price_rub,
                        "published_on": body.published_on,
                        "created_by": actor.username or str(actor.id),
                    }
                )
        except IntegrityError as e:
            raise MarketingCodeNotAllowedException("This code is already registered") from e
        await self.services.audit_log.record(
            actor=actor,
            action="marketing_link_create",
            target_type="marketing_link",
            target_id=link.code,
            detail={"channel": link.channel},
        )
        return await self._item(link.code)

    async def update(self, actor: UserSchema, link_id: int, body: MarketingLinkUpdateRequest) -> MarketingLinkItem:
        """Edit a link (channel, price, publish date, archived). Raises ``MarketingLinkNotFoundException``."""
        link = await self.repo.marketing_links.get_by_id(link_id)
        if not link:
            raise MarketingLinkNotFoundException("Marketing link not found")
        changes = body.model_dump(exclude_unset=True)
        if changes.get("is_archived") is None:
            changes.pop("is_archived", None)  # an explicit null leaves the flag alone (the column is NOT NULL)
        if isinstance(changes.get("channel"), str):
            changes["channel"] = changes["channel"].strip() or None
        await self.repo.marketing_links.update(link_id, changes)
        await self.services.audit_log.record(
            actor=actor,
            action="marketing_link_update",
            target_type="marketing_link",
            target_id=link.code,
            detail=jsonable_encoder(changes),
        )
        return await self._item(link.code)

    async def _item(self, code: str) -> MarketingLinkItem:
        return next(item for item in (await self.list_links()).items if item.code == code)

    # ── Owner alerts (sent hourly by marketing_links_alerts_job) ─────────────────────────────

    async def pending_alerts(self) -> list[MarketingAlert]:
        """Alerts due for live links: the first user and the first payment (only if they came
        after the link was saved here, so registering an old code doesn't replay its history),
        and a digest on days 1, 7 and 14 after the publish date."""
        now = datetime.now(UTC)
        label = self._config().activation_label
        links = {link.id: link for link in await self.repo.marketing_links.list_all()}
        alerts = []
        for item in (await self.list_links()).items:
            link = links.get(item.id)
            if link is None or link.is_archived:
                continue
            sent = set(link.alerts_sent or [])
            stats = item.stats
            if "first_user" not in sent and stats.first_user_at and stats.first_user_at >= link.created_at:
                alerts.append(MarketingAlert(link.id, "first_user", _first_user_text(item)))
            if "first_payment" not in sent and stats.first_payment_at and stats.first_payment_at >= link.created_at:
                alerts.append(MarketingAlert(link.id, "first_payment", _first_payment_text(item)))
            if item.published_on:
                start = datetime.combine(item.published_on, time(), tzinfo=UTC)
                for day in DIGEST_DAYS:
                    due = start + timedelta(days=day)
                    if f"day_{day}" not in sent and due <= now < due + timedelta(days=1):
                        alerts.append(
                            MarketingAlert(link.id, f"day_{day}", _digest_text(item, day, label), silent=True)
                        )
        return alerts

    async def mark_alerts_sent(self, alerts: list[MarketingAlert]) -> None:
        keys: dict[int, set[str]] = defaultdict(set)
        for alert in alerts:
            keys[alert.link_id].add(alert.key)
        for link_id, new_keys in keys.items():
            link = await self.repo.marketing_links.get_by_id(link_id)
            if link:
                await self.repo.marketing_links.update(
                    link_id, {"alerts_sent": sorted(set(link.alerts_sent or []) | new_keys)}
                )


@dataclass
class MarketingAlert:
    link_id: int
    key: str  # stored in marketing_links.alerts_sent so it goes out once
    text: str
    silent: bool = False


def _rub(amount: float | None) -> str:
    return fmt_money(round(amount), "RUB") if amount is not None else "—"


def _title(item: MarketingLinkItem) -> str:
    return f"<code>{esc(item.code)}</code>" + (f" · {esc(item.channel)}" if item.channel else "")


def _tags(item: MarketingLinkItem) -> str:
    return tags("marketing", f"code_{item.code}")


def _first_user_text(item: MarketingLinkItem) -> str:
    return f"👋 <b>First user</b> · {_title(item)}\n<i>The link works.</i>\n{_tags(item)}"


def _first_payment_text(item: MarketingLinkItem) -> str:
    stats = item.stats
    return (
        f"💸 <b>First payment</b> · {_title(item)}\n"
        f"<i>{stats.users} users so far · revenue {_rub(stats.revenue_rub)}</i>\n{_tags(item)}"
    )


def _digest_text(item: MarketingLinkItem, day: int, activation_label: str) -> str:
    stats = item.stats
    share = (lambda part: f"{round(part / stats.users * 100)}%") if stats.users else (lambda part: "—")
    lines = [
        f"📣 <b>Day {day}</b> · {_title(item)}",
        f"{stats.users} users · {share(stats.activated)} {esc(activation_label)} · "
        f"{stats.payers} paid ({share(stats.payers)})",
        f"Revenue {_rub(stats.revenue_rub)} · purchases {_rub(stats.revenue_purchases_rub)}",
    ]
    if item.price_rub:
        verdict = {
            "paid_back": f"✅ paid back in {item.payback_days} d",
            "in_progress": "⏳ not yet",
            "not_paid_back": "❌ not paid back in 14 days",
        }[item.payback or "in_progress"]
        lines.append(f"Price {_rub(item.price_rub)} · CAC {_rub(item.cac_rub)} · ×{item.roas:.2f} {verdict}")
    else:
        lines.append("<i>No price set, so no payback.</i>")
    if day == 1 and not stats.users:
        lines.append("⚠️ Nobody came in a day: check the link in the post.")
    lines.append(_tags(item))
    return "\n".join(lines)
