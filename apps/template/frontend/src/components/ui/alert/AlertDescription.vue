<script setup lang="ts">
import type { HTMLAttributes } from "vue"
import { cn } from "@/lib/utils"

interface Props {
  class?: HTMLAttributes["class"]
}

const props = defineProps<Props>()
</script>

<template>
  <div
    :class="cn('text-sm [&_p]:leading-relaxed', props.class)"
  >
    <slot />
  </div>
</template>
