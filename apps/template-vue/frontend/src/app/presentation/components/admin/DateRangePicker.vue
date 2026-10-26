<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export interface DateRange {
  from?: string;
  to?: string;
}

/**
 * DateRangePicker — two native date inputs emitting a `{ from, to }` pair of
 * ISO (YYYY-MM-DD) strings via v-model. SSG-safe: no `window`/`Date` access at
 * module scope; native `<input type="date">` avoids pulling in a calendar dep
 * and gives the platform picker inside Telegram on phones.
 *
 * TODO: extract to core when a third Vue app needs this (each Vue app keeps
 * its own copy for now, built on its own `ui/*` kit).
 */
const props = withDefaults(defineProps<{ modelValue?: DateRange }>(), {
  modelValue: () => ({}),
});

const emit = defineEmits<{ 'update:modelValue': [value: DateRange] }>();

const { t } = useI18n();

const from = computed({
  get: () => props.modelValue?.from ?? '',
  set: (value: string) => emit('update:modelValue', { ...props.modelValue, from: value || undefined }),
});

const to = computed({
  get: () => props.modelValue?.to ?? '',
  set: (value: string) => emit('update:modelValue', { ...props.modelValue, to: value || undefined }),
});
</script>

<template>
  <div class="grid w-full grid-cols-2 gap-3 sm:flex sm:w-auto sm:items-end">
    <div class="flex min-w-0 flex-col gap-1">
      <Label class="text-xs text-muted-foreground">{{ t('admin.filters.dateFrom') }}</Label>
      <Input
        v-model="from"
        type="date"
        class="w-full sm:w-auto"
      />
    </div>
    <div class="flex min-w-0 flex-col gap-1">
      <Label class="text-xs text-muted-foreground">{{ t('admin.filters.dateTo') }}</Label>
      <Input
        v-model="to"
        type="date"
        class="w-full sm:w-auto"
      />
    </div>
  </div>
</template>
