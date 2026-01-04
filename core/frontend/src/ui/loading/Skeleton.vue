<script setup lang="ts">
defineProps<{
  variant?: 'text' | 'rectangular' | 'circular';
  width?: string | number;
  height?: string | number;
  className?: string;
}>();
</script>

<template>
  <div
    :class="[
      'skeleton',
      `skeleton--${variant || 'rectangular'}`,
      className
    ]"
    :style="{
      width: typeof width === 'number' ? `${width}px` : width,
      height: typeof height === 'number' ? `${height}px` : height,
    }"
  />
</template>

<style scoped>
.skeleton {
  background: linear-gradient(
    90deg,
    #e0e0e0 25%,
    #f0f0f0 50%,
    #e0e0e0 75%
  );
  background-size: 200% 100%;
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

.skeleton--text {
  height: 1em;
  border-radius: 4px;
  transform: scale(1, 0.6);
}

.skeleton--rectangular {
  border-radius: 4px;
}

.skeleton--circular {
  border-radius: 50%;
}

@keyframes skeleton-pulse {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
  .skeleton {
    background: linear-gradient(
      90deg,
      #2a2a2a 25%,
      #3a3a3a 50%,
      #2a2a2a 75%
    );
  }
}
</style>
