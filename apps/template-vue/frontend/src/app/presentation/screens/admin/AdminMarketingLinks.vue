<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { toast } from 'vue-sonner';
import { useQueryClient } from '@tanstack/vue-query';
import { Archive, ArchiveRestore, Copy, Ellipsis, Loader2, Pencil, Plus } from '@lucide/vue';
import { getErrorMessage } from '@core/errors';
import { useAuth } from '@app/composables/useAuth';
import { listMarketingLinksQueryKey, useListMarketingLinks } from '@gen/hooks/useListMarketingLinks';
import { useCreateMarketingLink } from '@gen/hooks/useCreateMarketingLink';
import { useUpdateMarketingLink } from '@gen/hooks/useUpdateMarketingLink';
import type { MarketingLinkItem } from '@gen/models/MarketingLinkItem';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import AdminDataTable, { type AdminColumn } from '@app/presentation/components/admin/AdminDataTable.vue';

/**
 * AdminMarketingLinks — one acquisition code per external placement (post, ad,
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
 */
const { t, locale } = useI18n();
const { isAdminOrOwner } = useAuth();
const queryClient = useQueryClient();

const { data, isLoading, error, refetch } = useListMarketingLinks({
  query: { enabled: () => isAdminOrOwner.value, staleTime: 30 * 1000 },
});
const create = useCreateMarketingLink();
const update = useUpdateMarketingLink();

const showArchived = ref(false);

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
const sortBy = ref<SortKey>('start');
const sortDir = ref<'asc' | 'desc'>('desc');
const onSort = (column: string) => {
  if (sortBy.value === column) {
    sortDir.value = sortDir.value === 'desc' ? 'asc' : 'desc';
  } else {
    sortBy.value = column as SortKey;
    sortDir.value = 'desc';
  }
};

const rows = computed<MarketingLinkItem[]>(() => {
  const value = SORT_VALUE[sortBy.value];
  const sign = sortDir.value === 'desc' ? -1 : 1;
  return (data.value?.items ?? [])
    .filter((item) => showArchived.value || !item.is_archived)
    .sort((x, y) => {
      const [a, b] = [value(x), value(y)];
      if (a === null || b === null) return a === b ? 0 : a === null ? 1 : -1;
      return (a - b) * sign;
    });
});

const NUM = 'text-right whitespace-nowrap tabular-nums';
const columns = computed<AdminColumn[]>(() => {
  const col = (key: string, extra: Partial<AdminColumn> = {}): AdminColumn => ({
    key,
    label: t(`admin.marketing.columns.${key}`),
    ...extra,
  });
  const sorted = (key: SortKey, withHint = false): AdminColumn =>
    col(key, { sortable: true, class: NUM, hint: withHint ? t(`admin.marketing.hints.${key}`) : undefined });
  return [
    col('code'),
    sorted('start', true),
    sorted('price'),
    sorted('users'),
    sorted('activated', true),
    sorted('returned', true),
    sorted('payers', true),
    sorted('cac', true),
    sorted('revenueD14', true),
    sorted('revenue', true),
    sorted('purchases', true),
    sorted('ltv', true),
    sorted('roas', true),
    // Empty label: the actions column (next to the card title on phones).
    col('actions', { class: 'text-right' }),
  ];
});

// ── Form: a new code, or an existing one (saved on first edit if it predates the registry) ──
const CODE_PATTERN = /^[a-z0-9_]{2,40}$/;
const form = reactive({
  open: false,
  item: null as MarketingLinkItem | null,
  code: '',
  channel: '',
  price: '' as string | number,
  publishedOn: '',
});
const codeInvalid = computed(() => !form.item && form.code !== '' && !CODE_PATTERN.test(form.code));
const canSubmit = computed(() => form.item !== null || CODE_PATTERN.test(form.code));
const isSaving = computed(() => create.isPending.value || update.isPending.value);

const openForm = (item?: MarketingLinkItem) => {
  Object.assign(form, {
    open: true,
    item: item ?? null,
    code: item?.code ?? '',
    channel: item?.channel ?? '',
    price: item?.price_rub ?? '',
    publishedOn: item?.published_on ?? '',
  });
};

const refresh = () => queryClient.invalidateQueries({ queryKey: listMarketingLinksQueryKey() });

// Plain buttons that close the dialog only on success, so an error keeps the form.
const submit = async () => {
  if (!canSubmit.value || isSaving.value) return;
  const fields = {
    channel: form.channel || null,
    price_rub: form.price === '' ? null : Number(form.price),
    published_on: form.publishedOn || null,
  };
  try {
    if (form.item?.id != null) {
      await update.mutateAsync({ link_id: form.item.id, data: fields });
    } else {
      await create.mutateAsync({ data: { code: form.item?.code ?? form.code, ...fields } });
    }
    toast.success(t('admin.marketing.saved'));
    form.open = false;
    await refresh();
  } catch (e) {
    toast.error(getErrorMessage(e));
  }
};

const toggleArchived = async () => {
  const item = form.item;
  if (item?.id == null || isSaving.value) return;
  try {
    await update.mutateAsync({ link_id: item.id, data: { is_archived: !item.is_archived } });
    toast.success(t('admin.marketing.saved'));
    form.open = false;
    await refresh();
  } catch (e) {
    toast.error(getErrorMessage(e));
  }
};

// ── Links ──────────────────────────────────────────────────────────────────
const copy = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text);
    toast.success(t('admin.marketing.copied'));
  } catch {
    // No clipboard access (e.g. some webviews): show the link so it can be copied by hand.
    toast.error(text);
  }
};

// ── Numbers ────────────────────────────────────────────────────────────────
const rub = (amount: number | null | undefined): string =>
  amount == null
    ? '—'
    : new Intl.NumberFormat(locale.value, {
        style: 'currency',
        currency: 'RUB',
        currencyDisplay: 'narrowSymbol',
        maximumFractionDigits: 0,
      }).format(amount);

const pct = (part = 0, total = 0): string => (total ? `${Math.round((part / total) * 100)}%` : '—');

// Dates come as 'YYYY-MM-DD': parse them as local days, not UTC midnight.
const formatDay = (iso: string): string =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(locale.value, { day: 'numeric', month: 'short', year: 'numeric' });

const RETENTION_DAYS = [1, 7, 30] as const;

// The stock badge has no success / warning colours.
const PAYBACK_VARIANT = { paid_back: 'default', in_progress: 'secondary', not_paid_back: 'destructive' } as const;
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <p class="max-w-2xl text-sm text-muted-foreground">{{ t('admin.marketing.description') }}</p>
      <Button
        class="w-fit shrink-0"
        @click="openForm()"
      >
        <Plus class="h-4 w-4" />
        {{ t('admin.marketing.new') }}
      </Button>
    </div>

    <label class="flex w-fit items-center gap-2 text-sm text-muted-foreground">
      <Checkbox
        :model-value="showArchived"
        @update:model-value="showArchived = $event === true"
      />
      {{ t('admin.marketing.showArchived') }}
    </label>

    <AdminDataTable
      :columns="columns"
      :rows="rows"
      :row-key="(row: MarketingLinkItem) => row.code"
      :is-loading="isLoading"
      :error="error"
      :sort-by="sortBy"
      :sort-dir="sortDir"
      dense
      hide-pagination
      @sort="onSort"
      @retry="refetch()"
    >
      <template #cell-code="{ row }">
        <div class="flex min-w-32 flex-col">
          <span class="flex flex-wrap items-center gap-1.5">
            <code class="font-mono">{{ row.code }}</code>
            <Badge
              v-if="row.is_archived"
              variant="outline"
              class="text-muted-foreground"
            >
              {{ t('admin.marketing.badge.archived') }}
            </Badge>
          </span>
          <span
            v-if="row.channel"
            class="text-xs font-normal text-muted-foreground"
          >{{ row.channel }}</span>
        </div>
      </template>
      <template #cell-start="{ row }">
        <span
          v-if="row.start_date"
          :class="!row.published_on && 'text-muted-foreground'"
        >{{ formatDay(row.start_date) }}</span>
        <span v-else>—</span>
      </template>
      <template #cell-price="{ row }">{{ rub(row.price_rub) }}</template>
      <template #cell-users="{ row }">{{ row.stats.users }}</template>
      <template #cell-activated="{ row }">
        <span :title="String(row.stats.activated)">{{ pct(row.stats.activated, row.stats.users) }}</span>
      </template>
      <template #cell-returned="{ row }">
        <span
          v-for="(day, i) in RETENTION_DAYS"
          :key="day"
          :title="t('admin.marketing.retentionTitle', {
            days: day,
            returned: row.stats[`returned_d${day}`] ?? 0,
            eligible: row.stats[`eligible_d${day}`] ?? 0,
          })"
        >{{ i ? ' · ' : '' }}{{ pct(row.stats[`returned_d${day}`], row.stats[`eligible_d${day}`]) }}</span>
      </template>
      <template #cell-payers="{ row }">
        <span :title="String(row.stats.payers)">{{ pct(row.stats.payers, row.stats.users) }}</span>
      </template>
      <template #cell-cac="{ row }">{{ rub(row.cac_rub) }}</template>
      <template #cell-revenueD14="{ row }">{{ rub(row.stats.revenue_d14_rub) }}</template>
      <template #cell-revenue="{ row }">{{ rub(row.stats.revenue_rub) }}</template>
      <template #cell-purchases="{ row }">{{ rub(row.stats.revenue_purchases_rub) }}</template>
      <template #cell-ltv="{ row }">{{ rub(row.ltv_rub) }}</template>
      <template #cell-roas="{ row }">
        <span
          v-if="row.payback"
          class="inline-flex items-center gap-2"
        >
          ×{{ row.roas?.toFixed(2) }}
          <Badge :variant="PAYBACK_VARIANT[row.payback]">
            {{ t(`admin.marketing.payback.${row.payback}`, { days: row.payback_days }) }}
          </Badge>
        </span>
        <span v-else>—</span>
      </template>
      <template #cell-actions="{ row }">
        <div class="flex justify-end">
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button
                size="icon-sm"
                variant="ghost"
                :aria-label="t('admin.marketing.actions.menu')"
              >
                <Ellipsis class="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem @select="copy(row.app_link)">
                <Copy class="h-4 w-4" />
                {{ t('admin.marketing.actions.copyApp') }}
              </DropdownMenuItem>
              <DropdownMenuItem @select="copy(row.bot_link)">
                <Copy class="h-4 w-4" />
                {{ t('admin.marketing.actions.copyBot') }}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem @select="openForm(row)">
                <Pencil class="h-4 w-4" />
                {{ t('admin.marketing.actions.edit') }}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </template>
      <template #empty>
        <div
          class="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-12 text-center text-sm text-muted-foreground"
        >
          {{ t('admin.marketing.empty') }}
        </div>
      </template>
    </AdminDataTable>

    <Dialog
      :open="form.open"
      @update:open="(value: boolean) => (form.open = value)"
    >
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {{ form.item ? t('admin.marketing.form.editTitle', { code: form.item.code }) : t('admin.marketing.new') }}
          </DialogTitle>
        </DialogHeader>
        <form
          class="grid grid-cols-2 gap-3"
          @submit.prevent="submit"
        >
          <div
            v-if="!form.item"
            class="col-span-2 flex flex-col gap-1.5"
          >
            <Label for="ml-code">{{ t('admin.marketing.form.code') }}</Label>
            <Input
              id="ml-code"
              :model-value="form.code"
              :aria-invalid="codeInvalid"
              autocomplete="off"
              autocapitalize="off"
              spellcheck="false"
              @update:model-value="(v: string | number) => (form.code = String(v).toLowerCase())"
            />
            <p
              class="text-xs"
              :class="codeInvalid ? 'text-destructive' : 'text-muted-foreground'"
            >
              {{ t('admin.marketing.form.codeHint') }}
            </p>
          </div>
          <div class="col-span-2 flex flex-col gap-1.5">
            <Label for="ml-channel">
              {{ t('admin.marketing.form.channel') }}
              <span class="font-normal text-muted-foreground">{{ t('admin.marketing.form.optional') }}</span>
            </Label>
            <Input
              id="ml-channel"
              v-model="form.channel"
              maxlength="120"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <Label for="ml-price">{{ t('admin.marketing.form.price') }}</Label>
            <Input
              id="ml-price"
              v-model="form.price"
              type="number"
              min="0"
              step="1"
              inputmode="numeric"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <Label for="ml-published">{{ t('admin.marketing.form.publishedOn') }}</Label>
            <Input
              id="ml-published"
              v-model="form.publishedOn"
              type="date"
            />
          </div>
          <DialogDescription class="col-span-2 text-xs">{{ t('admin.marketing.form.paybackHint') }}</DialogDescription>
          <DialogFooter class="col-span-2">
            <Button
              v-if="form.item?.registered"
              type="button"
              variant="ghost"
              class="sm:mr-auto"
              :disabled="isSaving"
              @click="toggleArchived"
            >
              <ArchiveRestore
                v-if="form.item.is_archived"
                class="h-4 w-4"
              />
              <Archive
                v-else
                class="h-4 w-4"
              />
              {{ form.item.is_archived ? t('admin.marketing.actions.unarchive') : t('admin.marketing.actions.archive') }}
            </Button>
            <Button
              type="button"
              variant="outline"
              @click="form.open = false"
            >
              {{ t('admin.marketing.form.cancel') }}
            </Button>
            <Button
              type="submit"
              :disabled="!canSubmit || isSaving"
            >
              <Loader2
                v-if="isSaving"
                class="h-4 w-4 animate-spin"
              />
              {{ t('admin.marketing.form.save') }}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  </div>
</template>
