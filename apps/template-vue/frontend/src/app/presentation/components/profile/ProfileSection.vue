<script setup lang="ts">
defineProps<{
  icon: string
  title: string
}>()
</script>

<template>
  <!-- Card hover lift (#5) and hover glow (#19) -->
  <section
    class="bg-card rounded-xl border p-4 transition-all duration-300 ease-out hover:shadow-xl hover:shadow-primary/5 hover:-translate-y-1 hover:border-primary/20 motion-reduce:transition-none motion-reduce:hover:transform-none"
  >
    <h2 class="text-lg font-semibold mb-4 flex items-center gap-2">
      <!-- Floating icon (#11) -->
      <span class="inline-block motion-preset-oscillate-sm motion-duration-[3s] motion-loop-infinite">
        {{ icon }}
      </span>
      <span>{{ title }}</span>
    </h2>
    <slot />
  </section>
</template>
