<script setup lang="ts">
import { Moon, Sun } from 'lucide-vue-next';
import { computed } from 'vue';
import { mode } from '@app/store/theme';
import { Button } from '@/components/ui/button';

const resolvedTheme = computed(() => mode.state.value);

const toggleTheme = () => {
  mode.value = resolvedTheme.value === 'dark' ? 'light' : 'dark';
};
</script>

<template>
  <Button variant="outline" size="icon" @click="toggleTheme">
    <Sun class="h-[1.2rem] w-[1.2rem] scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
    <Moon class="absolute h-[1.2rem] w-[1.2rem] scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0" />
    <span class="sr-only">Toggle theme</span>
  </Button>
</template>
