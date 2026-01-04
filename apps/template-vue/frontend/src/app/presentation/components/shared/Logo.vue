<script setup lang="ts">
import { FlaskConical } from 'lucide-vue-next';
import { computed } from 'vue';
import { RouterLink } from 'vue-router';

interface LogoProps {
  size?: 'sm' | 'md';
  showText?: boolean;
}

const props = withDefaults(defineProps<LogoProps>(), {
  size: 'md',
  showText: true,
});

const iconSize = computed(() => props.size === 'sm' ? 'h-5 w-5' : 'h-6 w-6');
const textSize = computed(() => props.size === 'sm' ? 'text-base' : 'text-lg');
</script>

<template>
  <RouterLink
    to="/"
    class="flex items-center gap-2 transition-opacity hover:opacity-80"
  >
    <FlaskConical :class="[iconSize, 'text-primary']" />
    <span v-if="showText" :class="[textSize, 'font-semibold text-foreground']">
      Template
    </span>
  </RouterLink>
</template>
