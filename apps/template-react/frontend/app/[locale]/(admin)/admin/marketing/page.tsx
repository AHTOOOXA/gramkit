'use client';

import { useMemo, useState, type ReactNode, type SyntheticEvent } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getErrorMessage } from '@tma-platform/core-react/errors';
import {
  Archive,
  ArchiveRestore,
  Copy,
  Ellipsis,
  Loader2,
  Pencil,
  Plus,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { toast } from 'sonner';

import { cn } from '@/lib/utils';
import {
  AdminDataTable,
  type AdminColumn,
} from '@/components/admin/AdminDataTable';
import { AdminEmptyState } from '@/components/admin/AdminStateBlock';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/hooks';
import { useCreateMarketingLink } from '@/src/gen/hooks/useCreateMarketingLink';
import {
  listMarketingLinksQueryKey,
  useListMarketingLinks,
} from '@/src/gen/hooks/useListMarketingLinks';
import { useUpdateMarketingLink } from '@/src/gen/hooks/useUpdateMarketingLink';
import type { MarketingLinkItem } from '@/src/gen/models/MarketingLinkItem';
import type { MarketingLinkStats } from '@/src/gen/models/MarketingLinkStats';

// ── Sorting: newest placements first by default; empty values always sink ──
type SortKey =
  | 'start'
  | 'price'
  | 'users'
  | 'activated'
  | 'returned'
  | 'payers'
  | 'cac'
  | 'revenueD14'
  | 'revenue'
  | 'purchases'
  | 'ltv'
  | 'roas';

const share = (part = 0, total = 0) => (total ? part / total : null);

const SORT_VALUE: Record<SortKey, (row: MarketingLinkItem) => number | null> = {
  start: (row) => (row.start_date ? Date.parse(row.start_date) : null),
  price: (row) => row.price_rub ?? null,
  users: (row) => row.stats.users ?? 0,
  activated: (row) => share(row.stats.activated, row.stats.users),
  returned: (row) => share(row.stats.returned_d7, row.stats.eligible_d7),
  payers: (row) => share(row.stats.payers, row.stats.users),
  cac: (row) => row.cac_rub ?? null,
  revenueD14: (row) => row.stats.revenue_d14_rub ?? 0,
  revenue: (row) => row.stats.revenue_rub ?? 0,
  purchases: (row) => row.stats.revenue_purchases_rub ?? 0,
  ltv: (row) => row.ltv_rub ?? null,
  roas: (row) => row.roas ?? null,
};

const RETENTION: readonly {
  days: number;
  returned: (s: MarketingLinkStats) => number | undefined;
  eligible: (s: MarketingLinkStats) => number | undefined;
}[] = [
  { days: 1, returned: (s) => s.returned_d1, eligible: (s) => s.eligible_d1 },
  { days: 7, returned: (s) => s.returned_d7, eligible: (s) => s.eligible_d7 },
  {
    days: 30,
    returned: (s) => s.returned_d30,
    eligible: (s) => s.eligible_d30,
  },
];

// The stock badge has no success / warning colours.
const PAYBACK_VARIANT = {
  paid_back: 'default',
  in_progress: 'secondary',
  not_paid_back: 'destructive',
} as const;

const CODE_PATTERN = /^[a-z0-9_]{2,40}$/;

const pct = (part = 0, total = 0): string =>
  total ? `${String(Math.round((part / total) * 100))}%` : '—';

interface LinkForm {
  open: boolean;
  item: MarketingLinkItem | null;
  code: string;
  channel: string;
  price: string;
  publishedOn: string;
}

const CLOSED_FORM: LinkForm = {
  open: false,
  item: null,
  code: '',
  channel: '',
  price: '',
  publishedOn: '',
};

/**
 * Admin → Marketing — one acquisition code per external placement (post, ad,
 * partner), from the core marketing-links API. Create the code before the link
 * goes out, copy its Mini App (`?startapp=r-<code>`) or bot (`?start=<code>`)
 * link, and see what it brought: users on first touch, how many did something
 * in the app (the backend's `MarketingLinksConfig` defines it; default: opened
 * the app), who came back, payers and revenue. With a price the backend also
 * returns CAC, LTV, revenue ÷ price and the day it paid back.
 *
 * Codes seen on users before they were registered are listed too; editing one
 * saves it with its history. The whole list comes in one response, so sorting
 * is client-side and there is no pagination. Archiving is reversible, so it
 * needs no confirm.
 *
 * Port of template-vue's `AdminMarketingLinks.vue`.
 */
export default function AdminMarketingPage() {
  const t = useTranslations('admin');
  const locale = useLocale();
  const { isAdminOrOwner } = useAuth();
  const queryClient = useQueryClient();

  const { data, isLoading, error, refetch } = useListMarketingLinks({
    query: { enabled: isAdminOrOwner, staleTime: 30 * 1000 },
  });
  const create = useCreateMarketingLink();
  const update = useUpdateMarketingLink();

  const [showArchived, setShowArchived] = useState(false);
  const [sortBy, setSortBy] = useState<SortKey>('start');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const onSort = (column: string) => {
    if (sortBy === column) {
      setSortDir((dir) => (dir === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortBy(column as SortKey);
      setSortDir('desc');
    }
  };

  const rows = useMemo(() => {
    const value = SORT_VALUE[sortBy];
    const sign = sortDir === 'desc' ? -1 : 1;
    return (data?.items ?? [])
      .filter((item) => showArchived || !item.is_archived)
      .sort((x, y) => {
        const a = value(x);
        const b = value(y);
        if (a === null || b === null) return a === b ? 0 : a === null ? 1 : -1;
        return (a - b) * sign;
      });
  }, [data, showArchived, sortBy, sortDir]);

  // ── Numbers ──────────────────────────────────────────────────────────────
  const rub = (amount: number | null | undefined): string =>
    amount == null
      ? '—'
      : new Intl.NumberFormat(locale, {
          style: 'currency',
          currency: 'RUB',
          currencyDisplay: 'narrowSymbol',
          maximumFractionDigits: 0,
        }).format(amount);

  // Dates come as 'YYYY-MM-DD': parse them as local days, not UTC midnight.
  const formatDay = (iso: string): string =>
    new Date(`${iso}T00:00:00`).toLocaleDateString(locale, {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });

  // ── Links ────────────────────────────────────────────────────────────────
  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(t('marketing.copied'));
    } catch {
      // No clipboard access (e.g. some webviews): show the link so it can be copied by hand.
      toast.error(text);
    }
  };

  // ── Form: a new code, or an existing one (saved on first edit if it predates the registry) ──
  const [form, setForm] = useState<LinkForm>(CLOSED_FORM);
  const codeInvalid =
    !form.item && form.code !== '' && !CODE_PATTERN.test(form.code);
  const canSubmit = form.item !== null || CODE_PATTERN.test(form.code);
  const isSaving = create.isPending || update.isPending;

  const openForm = (item?: MarketingLinkItem) => {
    setForm({
      open: true,
      item: item ?? null,
      code: item?.code ?? '',
      channel: item?.channel ?? '',
      price: item?.price_rub != null ? String(item.price_rub) : '',
      publishedOn: item?.published_on ?? '',
    });
  };

  const closeForm = () => {
    setForm((prev) => ({ ...prev, open: false }));
  };

  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: listMarketingLinksQueryKey() });

  // Plain buttons that close the dialog only on success, so an error keeps the form.
  const submit = async (event: SyntheticEvent) => {
    event.preventDefault();
    if (!canSubmit || isSaving) return;
    const fields = {
      channel: form.channel || null,
      price_rub: form.price === '' ? null : Number(form.price),
      published_on: form.publishedOn || null,
    };
    try {
      if (form.item?.id != null) {
        await update.mutateAsync({ link_id: form.item.id, data: fields });
      } else {
        await create.mutateAsync({
          data: { code: form.item?.code ?? form.code, ...fields },
        });
      }
      toast.success(t('marketing.saved'));
      closeForm();
      await refresh();
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  };

  const toggleArchived = async () => {
    const item = form.item;
    if (item?.id == null || isSaving) return;
    try {
      await update.mutateAsync({
        link_id: item.id,
        data: { is_archived: !item.is_archived },
      });
      toast.success(t('marketing.saved'));
      closeForm();
      await refresh();
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  };

  // ── Columns ──────────────────────────────────────────────────────────────
  const NUM = 'text-right whitespace-nowrap tabular-nums';
  const sorted = (
    key: SortKey,
    cell: (row: MarketingLinkItem) => ReactNode,
    withHint = false
  ): AdminColumn<MarketingLinkItem> => ({
    key,
    label: t(`marketing.columns.${key}`),
    sortable: true,
    className: NUM,
    hint: withHint ? t(`marketing.hints.${key}`) : undefined,
    cell,
  });

  const columns: AdminColumn<MarketingLinkItem>[] = [
    {
      key: 'code',
      label: t('marketing.columns.code'),
      cell: (row) => (
        <div className="flex min-w-32 flex-col">
          <span className="flex flex-wrap items-center gap-1.5">
            <code className="font-mono">{row.code}</code>
            {row.is_archived && (
              <Badge variant="outline" className="text-muted-foreground">
                {t('marketing.badge.archived')}
              </Badge>
            )}
          </span>
          {row.channel && (
            <span className="text-muted-foreground text-xs font-normal">
              {row.channel}
            </span>
          )}
        </div>
      ),
    },
    sorted(
      'start',
      (row) =>
        row.start_date ? (
          <span className={cn(!row.published_on && 'text-muted-foreground')}>
            {formatDay(row.start_date)}
          </span>
        ) : (
          '—'
        ),
      true
    ),
    sorted('price', (row) => rub(row.price_rub)),
    sorted('users', (row) => row.stats.users),
    sorted(
      'activated',
      (row) => (
        <span title={String(row.stats.activated ?? 0)}>
          {pct(row.stats.activated, row.stats.users)}
        </span>
      ),
      true
    ),
    sorted(
      'returned',
      (row) =>
        RETENTION.map((r, i) => (
          <span
            key={r.days}
            title={t('marketing.retentionTitle', {
              days: r.days,
              returned: r.returned(row.stats) ?? 0,
              eligible: r.eligible(row.stats) ?? 0,
            })}
          >
            {i ? ' · ' : ''}
            {pct(r.returned(row.stats), r.eligible(row.stats))}
          </span>
        )),
      true
    ),
    sorted(
      'payers',
      (row) => (
        <span title={String(row.stats.payers ?? 0)}>
          {pct(row.stats.payers, row.stats.users)}
        </span>
      ),
      true
    ),
    sorted('cac', (row) => rub(row.cac_rub), true),
    sorted('revenueD14', (row) => rub(row.stats.revenue_d14_rub), true),
    sorted('revenue', (row) => rub(row.stats.revenue_rub), true),
    sorted('purchases', (row) => rub(row.stats.revenue_purchases_rub), true),
    sorted('ltv', (row) => rub(row.ltv_rub), true),
    sorted(
      'roas',
      (row) =>
        row.payback ? (
          <span className="inline-flex items-center gap-2">
            ×{row.roas?.toFixed(2)}
            <Badge variant={PAYBACK_VARIANT[row.payback]}>
              {t(`marketing.payback.${row.payback}`, {
                days: row.payback_days ?? 0,
              })}
            </Badge>
          </span>
        ) : (
          '—'
        ),
      true
    ),
    // Empty label: the actions column (next to the card title on phones).
    {
      key: 'actions',
      label: t('marketing.columns.actions'),
      className: 'text-right',
      cell: (row) => (
        <div className="flex justify-end">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                size="icon-sm"
                variant="ghost"
                aria-label={t('marketing.actions.menu')}
              >
                <Ellipsis className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={() => void copy(row.app_link)}>
                <Copy className="h-4 w-4" />
                {t('marketing.actions.copyApp')}
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => void copy(row.bot_link)}>
                <Copy className="h-4 w-4" />
                {t('marketing.actions.copyBot')}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onSelect={() => {
                  openForm(row);
                }}
              >
                <Pencil className="h-4 w-4" />
                {t('marketing.actions.edit')}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-muted-foreground max-w-2xl text-sm">
          {t('marketing.description')}
        </p>
        <Button
          className="w-fit shrink-0"
          onClick={() => {
            openForm();
          }}
        >
          <Plus className="h-4 w-4" />
          {t('marketing.new')}
        </Button>
      </div>

      <label className="text-muted-foreground flex w-fit items-center gap-2 text-sm">
        <Checkbox
          checked={showArchived}
          onCheckedChange={(checked) => {
            setShowArchived(checked === true);
          }}
        />
        {t('marketing.showArchived')}
      </label>

      <AdminDataTable
        columns={columns}
        rows={rows}
        rowKey={(row) => row.code}
        isLoading={isLoading}
        error={error}
        sortBy={sortBy}
        sortDir={sortDir}
        dense
        hidePagination
        onSort={onSort}
        onRetry={() => void refetch()}
        empty={<AdminEmptyState>{t('marketing.empty')}</AdminEmptyState>}
      />

      <Dialog
        open={form.open}
        onOpenChange={(open) => {
          setForm((prev) => ({ ...prev, open }));
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {form.item
                ? t('marketing.form.editTitle', { code: form.item.code })
                : t('marketing.new')}
            </DialogTitle>
          </DialogHeader>
          <form
            className="grid grid-cols-2 gap-3"
            onSubmit={(e) => void submit(e)}
          >
            {!form.item && (
              <div className="col-span-2 flex flex-col gap-1.5">
                <Label htmlFor="ml-code">{t('marketing.form.code')}</Label>
                <Input
                  id="ml-code"
                  value={form.code}
                  aria-invalid={codeInvalid}
                  autoComplete="off"
                  autoCapitalize="off"
                  spellCheck={false}
                  onChange={(e) => {
                    const code = e.target.value.toLowerCase();
                    setForm((prev) => ({ ...prev, code }));
                  }}
                />
                <p
                  className={cn(
                    'text-xs',
                    codeInvalid ? 'text-destructive' : 'text-muted-foreground'
                  )}
                >
                  {t('marketing.form.codeHint')}
                </p>
              </div>
            )}
            <div className="col-span-2 flex flex-col gap-1.5">
              <Label htmlFor="ml-channel">
                {t('marketing.form.channel')}
                <span className="text-muted-foreground font-normal">
                  {t('marketing.form.optional')}
                </span>
              </Label>
              <Input
                id="ml-channel"
                value={form.channel}
                maxLength={120}
                onChange={(e) => {
                  const channel = e.target.value;
                  setForm((prev) => ({ ...prev, channel }));
                }}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="ml-price">{t('marketing.form.price')}</Label>
              <Input
                id="ml-price"
                type="number"
                min={0}
                step={1}
                inputMode="numeric"
                value={form.price}
                onChange={(e) => {
                  const price = e.target.value;
                  setForm((prev) => ({ ...prev, price }));
                }}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="ml-published">
                {t('marketing.form.publishedOn')}
              </Label>
              <Input
                id="ml-published"
                type="date"
                value={form.publishedOn}
                onChange={(e) => {
                  const publishedOn = e.target.value;
                  setForm((prev) => ({ ...prev, publishedOn }));
                }}
              />
            </div>
            <DialogDescription className="col-span-2 text-xs">
              {t('marketing.form.paybackHint')}
            </DialogDescription>
            <DialogFooter className="col-span-2">
              {form.item?.registered && (
                <Button
                  type="button"
                  variant="ghost"
                  className="sm:mr-auto"
                  disabled={isSaving}
                  onClick={() => void toggleArchived()}
                >
                  {form.item.is_archived ? (
                    <ArchiveRestore className="h-4 w-4" />
                  ) : (
                    <Archive className="h-4 w-4" />
                  )}
                  {form.item.is_archived
                    ? t('marketing.actions.unarchive')
                    : t('marketing.actions.archive')}
                </Button>
              )}
              <Button type="button" variant="outline" onClick={closeForm}>
                {t('marketing.form.cancel')}
              </Button>
              <Button type="submit" disabled={!canSubmit || isSaving}>
                {isSaving && <Loader2 className="h-4 w-4 animate-spin" />}
                {t('marketing.form.save')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
