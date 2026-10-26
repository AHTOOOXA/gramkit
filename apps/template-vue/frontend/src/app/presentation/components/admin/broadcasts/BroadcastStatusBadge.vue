<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { Badge } from '@/components/ui/badge';

/**
 * BroadcastStatusBadge — active / completed status pill for a broadcast. The
 * backend reports an expired row as inactive, so it reads "Completed".
 *
 * TODO: extract to core when a third Vue app needs this (each Vue app keeps
 * its own copy for now, built on its own `ui/*` kit).
 */
const props = defineProps<{ isActive: boolean }>();

const { t } = useI18n();

const variant = computed<'default' | 'secondary'>(() => (props.isActive ? 'default' : 'secondary'));
const label = computed(() =>
  props.isActive ? t('admin.broadcasts.status.active') : t('admin.broadcasts.status.completed'),
);
</script>

<template>
  <Badge :variant="variant">{{ label }}</Badge>
</template>
