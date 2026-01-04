<script setup lang="ts">
interface Props {
  error: Error;
}

defineProps<Props>();

const handleReload = () => {
  window.location.reload();
};
</script>

<template>
  <div class="flex h-screen w-screen items-center justify-center bg-background p-4">
    <div class="flex flex-col items-center gap-4 text-center">
      <div class="text-6xl">⚠️</div>

      <h1 class="text-xl font-bold text-foreground">
        Initialization Failed
      </h1>

      <p class="text-sm text-muted-foreground">
        {{ error.message }}
      </p>

      <button
        class="rounded-lg bg-primary px-6 py-3 text-primary-foreground transition hover:opacity-80"
        @click="handleReload"
      >
        Reload App
      </button>
    </div>
  </div>
</template>
