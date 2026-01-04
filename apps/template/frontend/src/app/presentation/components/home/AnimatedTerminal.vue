<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue';
import { RotateCcw } from 'lucide-vue-next';
import { Button } from '@/components/ui/button';

const COMMANDS = [
  { text: '$ ', color: 'text-green-500', delay: 0 },
  { text: 'pnpm install', color: 'text-white', delay: 0 },
  { text: '\n$ ', color: 'text-green-500', delay: 800 },
  { text: 'make up APP=template', color: 'text-white', delay: 0 },
  { text: '\n\n✓ ', color: 'text-green-500', delay: 1200 },
  { text: 'Localhost  ', color: 'text-gray-400', delay: 0 },
  { text: 'http://localhost:5174/template', color: 'text-blue-400', delay: 0 },
  { text: '\n  ', color: 'text-gray-400', delay: 400 },
  { text: 'Tunnel     ', color: 'text-gray-500', delay: 0 },
  { text: 'https://local.yourdomain.com/template', color: 'text-gray-500', delay: 0 },
] as const;

const currentIndex = ref(0);
const charIndex = ref(0);
const isComplete = ref(false);
const hasStarted = ref(false);
const containerRef = ref<HTMLDivElement | null>(null);
let observer: IntersectionObserver | null = null;
let typingTimeout: ReturnType<typeof setTimeout> | null = null;
let delayTimeout: ReturnType<typeof setTimeout> | null = null;

const resetAnimation = () => {
  currentIndex.value = 0;
  charIndex.value = 0;
  isComplete.value = false;
  hasStarted.value = true;
};

onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting && !hasStarted.value) {
        hasStarted.value = true;
      }
    },
    { threshold: 0.2 }
  );

  if (containerRef.value) {
    observer.observe(containerRef.value);
  }
});

onUnmounted(() => {
  if (observer) {
    observer.disconnect();
  }
  if (typingTimeout) {
    clearTimeout(typingTimeout);
  }
  if (delayTimeout) {
    clearTimeout(delayTimeout);
  }
});

watch([currentIndex, charIndex, hasStarted], () => {
  if (!hasStarted.value) return;

  if (currentIndex.value >= COMMANDS.length) {
    isComplete.value = true;
    return;
  }

  const currentCommand = COMMANDS[currentIndex.value];
  if (!currentCommand) return;

  if (charIndex.value === 0 && currentCommand.delay > 0) {
    delayTimeout = setTimeout(() => {
      charIndex.value = 1;
    }, currentCommand.delay);
    return;
  }

  if (charIndex.value < currentCommand.text.length) {
    const typingSpeed = currentCommand.text.startsWith('\n') ? 0 : 50;
    typingTimeout = setTimeout(() => {
      charIndex.value++;
    }, typingSpeed);
  } else {
    currentIndex.value++;
    charIndex.value = 0;
  }
});

const renderText = () => {
  const result: { key: number; text: string; color: string }[] = [];

  for (let i = 0; i <= currentIndex.value && i < COMMANDS.length; i++) {
    const cmd = COMMANDS[i];
    if (!cmd) continue;

    const isCurrentCommand = i === currentIndex.value;
    const text = isCurrentCommand
      ? cmd.text.slice(0, charIndex.value)
      : cmd.text;

    if (text) {
      result.push({
        key: i,
        text,
        color: cmd.color,
      });
    }
  }

  return result;
};
</script>

<template>
  <div ref="containerRef" class="relative group">
    <!-- Terminal Window -->
    <div class="bg-gray-900 rounded-lg shadow-2xl overflow-hidden border border-gray-800">
      <!-- Title Bar -->
      <div class="bg-gray-800 px-4 py-3 flex items-center justify-between border-b border-gray-700">
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full bg-red-500" />
          <div class="w-3 h-3 rounded-full bg-yellow-500" />
          <div class="w-3 h-3 rounded-full bg-green-500" />
        </div>
        <div class="text-gray-400 text-xs font-medium">terminal</div>
        <div class="w-16" />
      </div>

      <!-- Terminal Content -->
      <div class="p-6 font-mono text-sm min-h-[180px] relative">
        <div class="whitespace-pre-wrap">
          <span
            v-for="item in renderText()"
            :key="item.key"
            :class="item.color"
          >{{ item.text }}</span>
          <span
            v-if="!isComplete && hasStarted"
            class="inline-block w-2 h-4 bg-white ml-0.5 animate-pulse"
          />
        </div>
      </div>
    </div>

    <!-- Replay Button -->
    <div
      v-if="isComplete"
      class="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity"
    >
      <Button
        variant="outline"
        size="sm"
        class="bg-gray-800/90 border-gray-700 hover:bg-gray-700 text-white"
        @click="resetAnimation"
      >
        <RotateCcw class="w-3 h-3 mr-2" />
        Replay
      </Button>
    </div>
  </div>
</template>
