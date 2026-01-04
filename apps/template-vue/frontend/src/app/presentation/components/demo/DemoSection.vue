<script setup lang="ts">
defineProps<{
  icon: string
  title: string
}>()
</script>

<template>
  <!-- Card hover lift (#5) and hover glow (#19) -->
  <section
    class="group h-full flex flex-col bg-card rounded-xl border p-4 transition-all duration-300 ease-out hover:shadow-2xl hover:shadow-primary/10 hover:-translate-y-1.5 hover:scale-[1.01] hover:border-primary/30 hover:bg-gradient-to-br hover:from-card hover:to-primary/[0.02] motion-reduce:transition-none motion-reduce:hover:transform-none"
  >
    <h2 class="text-lg font-semibold mb-4 flex items-center gap-2">
      <!-- Floating icon (#11) -->
      <span class="inline-block motion-preset-oscillate-sm motion-duration-[3s] motion-loop-infinite transition-transform duration-200 group-hover:scale-110 group-hover:motion-duration-[1.5s]">
        {{ icon }}
      </span>
      <span>{{ title }}</span>
    </h2>
    <div class="flex-1">
      <slot />
    </div>
  </section>
</template>
