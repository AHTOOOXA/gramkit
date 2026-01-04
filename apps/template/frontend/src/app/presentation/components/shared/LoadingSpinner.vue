<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next';
import { computed } from 'vue';
import { cn } from '@/lib/utils';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const props = withDefaults(defineProps<LoadingSpinnerProps>(), {
  size: 'md',
  className: '',
});

const sizeClasses = {
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-8 w-8',
};

const spinnerClass = computed(() =>
  cn('animate-spin', sizeClasses[props.size], props.className)
);
</script>

<template>
  <Loader2 :class="spinnerClass" />
</template>
