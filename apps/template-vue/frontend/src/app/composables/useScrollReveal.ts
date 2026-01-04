import { ref, onMounted, onBeforeUnmount } from 'vue';

export interface UseScrollRevealOptions {
  threshold?: number;
  rootMargin?: string;
  triggerOnce?: boolean;
}

/**
 * Composable for scroll-triggered reveal animations using IntersectionObserver.
 * Returns a ref to attach to the element and whether it's visible.
 *
 * @example
 * const { ref: elementRef, isVisible } = useScrollReveal();
 * <div :ref="elementRef" :class="isVisible ? 'motion-preset-fade' : 'opacity-0'">
 */
export function useScrollReveal<T extends HTMLElement = HTMLDivElement>({
  threshold = 0.1,
  rootMargin = '0px 0px 100px 0px',
  triggerOnce = true,
}: UseScrollRevealOptions = {}) {
  const elementRef = ref<T | null>(null);
  const isVisible = ref(false);
  let observer: IntersectionObserver | null = null;

  onMounted(() => {
    const element = elementRef.value;
    if (!element) return;

    observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          isVisible.value = true;
          if (triggerOnce && observer) {
            observer.disconnect();
          }
        } else if (!triggerOnce) {
          isVisible.value = false;
        }
      },
      { threshold, rootMargin }
    );

    observer.observe(element);
  });

  onBeforeUnmount(() => {
    if (observer) {
      observer.disconnect();
    }
  });

  return { ref: elementRef, isVisible };
}
