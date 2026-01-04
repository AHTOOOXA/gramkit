<script setup lang="ts">
import type { PrimitiveProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { Primitive } from 'reka-ui'
import { computed } from 'vue'
import { cn } from '@/lib/utils'
import { animationVariants, type AnimationVariant } from '@/lib/animations'

interface Props extends PrimitiveProps {
  variant?: AnimationVariant
  delay?: number
  duration?: number
  class?: HTMLAttributes['class']
}

const props = withDefaults(defineProps<Props>(), {
  as: 'div',
  variant: 'fadeIn',
})

const animationClasses = computed(() => {
  let classes = props.variant ? animationVariants[props.variant] : ''

  // Override duration if specified
  if (props.duration) {
    // Remove existing duration classes and add new one
    classes = classes.replace(/motion-duration-\[[^\]]+\]/g, '')
    classes += ` motion-duration-[${props.duration}s]`
  }

  // Add delay if specified
  if (props.delay) {
    classes += ` motion-delay-[${props.delay}s]`
  }

  return classes
})
</script>

<template>
  <Primitive
    :as="as"
    :as-child="asChild"
    :class="cn(animationClasses, props.class)"
  >
    <slot />
  </Primitive>
</template>
