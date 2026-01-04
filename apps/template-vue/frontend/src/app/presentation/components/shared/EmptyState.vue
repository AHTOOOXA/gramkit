<script setup lang="ts">
import { InboxIcon } from 'lucide-vue-next';
import { computed } from 'vue';
import { cn } from '@/lib/utils';

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: object;
  action?: object;
  className?: string;
}

const props = defineProps<EmptyStateProps>();

const containerClass = computed(() =>
  cn('flex flex-col items-center justify-center py-12 text-center', props.className)
);
</script>

<template>
  <div :class="containerClass">
    <div class="text-muted-foreground mb-4">
      <component :is="icon" v-if="icon" class="h-12 w-12" />
      <InboxIcon v-else class="h-12 w-12" />
    </div>
    <h3 class="mb-2 text-lg font-semibold">{{ title }}</h3>
    <p v-if="description" class="text-muted-foreground mb-4 text-sm">
      {{ description }}
    </p>
    <div v-if="action">
      <component :is="action" />
    </div>
  </div>
</template>
