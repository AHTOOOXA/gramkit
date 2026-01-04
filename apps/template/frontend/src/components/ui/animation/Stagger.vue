<script setup lang="ts">
import type { PrimitiveProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { Primitive } from 'reka-ui'
import { computed, useSlots, type VNode } from 'vue'
import { cn } from '@/lib/utils'

interface Props extends PrimitiveProps {
  staggerDelay?: number
  class?: HTMLAttributes['class']
}

const props = withDefaults(defineProps<Props>(), {
  as: 'div',
  staggerDelay: 50,
})

const slots = useSlots()

// Process children and apply stagger delays
const staggeredChildren = computed(() => {
  const defaultSlot = slots.default?.()
  if (!defaultSlot) return []

  return defaultSlot.map((child: VNode, index: number) => {
    const delayMs = index * props.staggerDelay
    const delaySec = delayMs / 1000

    // Clone the child and add delay class
    const delayClass = `motion-delay-[${delaySec}s]`

    // If child has props, merge the class
    if (child.props) {
      child.props.class = cn(child.props.class, delayClass)
    } else {
      child.props = { class: delayClass }
    }

    return child
  })
})
</script>

<template>
  <Primitive
    :as="as"
    :as-child="asChild"
    :class="cn(props.class)"
  >
    <template v-for="(child, index) in staggeredChildren" :key="index">
      <component :is="child" />
    </template>
  </Primitive>
</template>
