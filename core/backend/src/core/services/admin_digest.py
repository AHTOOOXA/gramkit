"""Daily admin digest — data shape + Telegram formatting.

Answers "how did the last day go?" in a few seconds: one table putting every number next to
its 7-day context, plus a few summary lines. Rendered twice from the same data:

- ``rich_html``  — Bot API 10.1 Rich Message (real table, <footer>)
- ``text``       — classic Telegram HTML fallback (monospace table)

Revenue stays per-currency everywhere (no base currency exists); the headline delta is taken
on the currency that earned the most this week.

Apps add rows, summary lines and warnings through ``core.services.admin_metrics.register_digest_row``;
they arrive here as ``DailyDigest.rows``. Texts come from ``core.admin.digest.*`` (en / ru).
"""

from dataclasses import dataclass, field
from datetime import datetime

from core.infrastructure.i18n import t
from core.infrastructure.telegram.admin_messages import esc, fmt_delta, fmt_int, fmt_money_map
from core.services.admin_metrics import DigestRow

# Orders of core's table rows; app rows registered with an order in between land in between.
ROW_ORDER_REVENUE = 10
ROW_ORDER_NEW_USERS = 20
ROW_ORDER_PURCHASES = 40
ROW_ORDER_RENEWALS = 50
ROW_ORDER_EXPIRED = 60


@dataclass
class DigestPeriod:
    revenue: dict[str, float] = field(default_factory=dict)
    new_users: int = 0
    purchases: int = 0
    renewals: int = 0
    expired: int = 0


@dataclass
class DailyDigest:
    window_start: datetime
    window_end: datetime
    day: DigestPeriod
    week: DigestPeriod
    prev_week: DigestPeriod
    dau: int = 0
    wau: int = 0
    mau: int = 0
    active_subs: int = 0
    past_due: int = 0
    canceled_day: int = 0
    # App rows from the digest registry: (order, row), already in order.
    rows: list[tuple[int, DigestRow]] = field(default_factory=list)
    app_title: str = "app"
    error: str | None = None

    @property
    def partial(self) -> bool:
        """True for a manual /stats mid-day — the window isn't a full day yet."""
        return (self.window_end - self.window_start).total_seconds() < 23 * 3600


def _tr(key: str, locale: str, **kwargs) -> str:
    return t(f"core.admin.digest.{key}", locale, **kwargs)


def _main_currency_delta(current: dict[str, float], previous: dict[str, float]) -> str:
    if not current and not previous:
        return "="
    main = max({**previous, **current}, key=lambda c: current.get(c, 0) or previous.get(c, 0))
    return fmt_delta(current.get(main, 0), previous.get(main, 0))


def _count_cells(label: str, day: int, week: int, prev_week: int) -> tuple[str, str, str, str]:
    return label, fmt_int(day), fmt_int(week), fmt_delta(week, prev_week)


def _rows(d: DailyDigest, locale: str) -> list[tuple[str, str, str, str]]:
    """(label, day, 7d, vs prev 7d) — shared by both renderings. Core and app rows merged by order."""

    def core_row(key: str, attr: str) -> tuple[str, str, str, str]:
        return _count_cells(_tr(key, locale), getattr(d.day, attr), getattr(d.week, attr), getattr(d.prev_week, attr))

    revenue = (
        _tr("revenue", locale),
        fmt_money_map(d.day.revenue),
        fmt_money_map(d.week.revenue),
        _main_currency_delta(d.week.revenue, d.prev_week.revenue),
    )
    # (order, 0 = core first on a tie, position, cells)
    entries = [
        (ROW_ORDER_REVENUE, 0, 0, revenue),
        (ROW_ORDER_NEW_USERS, 0, 1, core_row("new_users", "new_users")),
        (ROW_ORDER_PURCHASES, 0, 2, core_row("purchases", "purchases")),
        (ROW_ORDER_RENEWALS, 0, 3, core_row("renewals", "renewals")),
        (ROW_ORDER_EXPIRED, 0, 4, core_row("expired", "expired")),
    ]
    for position, (order, row) in enumerate(_table_rows(d)):
        entries.append((order, 1, position, _count_cells(esc(row.label), row.day, row.week, row.prev_week)))
    return [cells for *_, cells in sorted(entries, key=lambda entry: entry[:3])]


def _table_rows(d: DailyDigest) -> list[tuple[int, DigestRow]]:
    """App rows that render as table rows: a label and no ``line``."""
    return [(order, row) for order, row in d.rows if row.line is None and row.label]


def _warnings(d: DailyDigest, locale: str) -> list[str]:
    # App warnings first (they are usually the most specific), then core's.
    warnings = [esc(row.warning) for _, row in d.rows if row.warning]
    if not d.week.revenue and d.prev_week.revenue:
        warnings.append(_tr("warn_no_revenue", locale))
    if d.past_due:
        key = "warn_past_due_one" if d.past_due == 1 else "warn_past_due_other"
        warnings.append(_tr(key, locale, count=d.past_due))
    return warnings


def _title(d: DailyDigest, locale: str) -> str:
    date = d.window_start.strftime("%a %-d %b")
    return f"📊 {esc(d.app_title)} · {date}{_tr('so_far', locale) if d.partial else ''}"


def _summary_lines(d: DailyDigest, locale: str) -> list[str]:
    """Plain-HTML lines under the table (users, subs, then the app's lines)."""
    subs = _tr("active_subs", locale, count=fmt_int(d.active_subs))
    if d.canceled_day:
        subs += _tr("turned_off", locale, count=d.canceled_day)
    return [
        _tr("users_line", locale, dau=fmt_int(d.dau), wau=fmt_int(d.wau), mau=fmt_int(d.mau)),
        subs,
        *[row.line for _, row in d.rows if row.line],
    ]


def _header(locale: str) -> tuple[str, str, str, str]:
    return "", _tr("day", locale), _tr("week", locale), _tr("delta", locale)


def render_rich(d: DailyDigest, locale: str = "en") -> str:
    """Rich HTML body for sendRichMessage."""
    _, day_h, week_h, delta_h = _header(locale)
    table = [
        "<table bordered striped compact>",
        f"<tr><th></th><th>{day_h}</th><th>{week_h}</th><th>{delta_h}</th></tr>",
    ]
    for label, day, week, delta in _rows(d, locale):
        table.append(
            f'<tr><td>{label}</td><td align="right">{day}</td>'
            f'<td align="right">{week}</td><td align="right">{delta}</td></tr>'
        )
    table.append("</table>")

    parts = [f"<h3>{_title(d, locale)}</h3>", "".join(table)]
    parts += [f"<p>{line}</p>" for line in _summary_lines(d, locale)]
    warnings = _warnings(d, locale)
    if warnings:
        parts.append("<blockquote>" + "<br>".join(f"⚠️ {w}" for w in warnings) + "</blockquote>")
    parts.append(f"<footer>{_tr('footnote', locale)}</footer>")
    return "".join(parts)


def render_text(d: DailyDigest, locale: str = "en") -> str:
    """Classic Telegram HTML fallback: the same table in monospace."""
    rows = [_header(locale), *_rows(d, locale)]
    widths = [max(len(row[i]) for row in rows) for i in range(4)]
    table = "\n".join(
        "  ".join(cell.ljust(widths[0]) if i == 0 else cell.rjust(widths[i]) for i, cell in enumerate(row))
        for row in rows
    )

    parts = [f"<b>{_title(d, locale)}</b>", f"<pre>{table}</pre>", *_summary_lines(d, locale)]
    warnings = _warnings(d, locale)
    if warnings:
        parts += ["", *[f"⚠️ {w}" for w in warnings]]
    parts += ["", f"<i>{_tr('footnote', locale)}</i>"]
    return "\n".join(parts)


def render_error(d: DailyDigest, locale: str = "en") -> str:
    return f"<b>{_title(d, locale)}</b>\n\n{_tr('failed', locale)}\n<pre>{esc(d.error)}</pre>"
