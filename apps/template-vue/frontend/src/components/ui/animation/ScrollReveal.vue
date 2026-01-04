<script setup lang="ts">
import type { PrimitiveProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { Primitive } from 'reka-ui'
import { ref, computed } from 'vue'
import { useIntersectionObserver } from '@vueuse/core'
import { cn } from '@/lib/utils'

interface Props extends PrimitiveProps {
  threshold?: number
  rootMargin?: string
  triggerOnce?: boolean
  delay?: number
  class?: HTMLAttributes['class']
}

const props = withDefaults(defineProps<Props>(), {
  as: 'div',
  threshold: 0.1,
  rootMargin: '0px 0px 100px 0px',
  triggerOnce: true,
  delay: 0,
})

const targetRef = ref<HTMLElement | null>(null)
const hasBeenVisible = ref(false)

const { stop } = useIntersectionObserver(
  targetRef,
  ([{ isIntersecting }]) => {
    if (isIntersecting) {
      hasBeenVisible.value = true
      if (props.triggerOnce) {
        stop()
      }
    } else if (!props.triggerOnce) {
      hasBeenVisible.value = false
    }
  },
  {
    threshold: props.threshold,
    rootMargin: props.rootMargin,
  }
)

const visibilityClass = computed(() => {
  return hasBeenVisible.value ? 'motion-visible' : 'motion-hidden'
})
</script>

<template>
  <Primitive
    ref="targetRef"
    :as="as"
    :as-child="asChild"
    :class="cn(visibilityClass, props.class)"
    :style="{ transitionDelay: hasBeenVisible ? `${delay}ms` : '0ms' }"
  >
    <slot />
  </Primitive>
</template>

<style scoped>
.motion-hidden {
  opacity: 0;
  transform: translateY(20px);
}

.motion-visible {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 0.5s ease-out, transform 0.5s ease-out;
}
</style>
