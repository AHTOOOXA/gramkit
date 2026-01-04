import { ref, nextTick, watch, Ref, type ComponentPublicInstance } from 'vue';

export function usePlaceholderHeight() {
  const placeholderRef = ref<ComponentPublicInstance | null>(null);
  const placeholderHeight = ref<number | null>(null);

  const calculateFullHeight = (element: HTMLElement) => {
    if (!element) return 0;

    const style = window.getComputedStyle(element);
    const margin = parseFloat(style.marginTop) + parseFloat(style.marginBottom);
    const padding = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
    const height = element.getBoundingClientRect().height + margin + padding;
    placeholderHeight.value = height;
    return height;
  };

  // Update height calculation when the watched value changes
  const setupHeightWatcher = <T>(watchedRef: Ref<T>) => {
    watch(watchedRef, async () => {
      await nextTick();
      if (placeholderRef.value?.$el) {
        calculateFullHeight(placeholderRef.value.$el);
      }
    });
  };

  // Initialize height calculation
  const initPlaceholderHeight = async () => {
    await nextTick();
    if (placeholderRef.value?.$el) {
      calculateFullHeight(placeholderRef.value.$el);
    }
  };

  return {
    placeholderRef,
    placeholderHeight,
    calculateFullHeight,
    setupHeightWatcher,
    initPlaceholderHeight,
  };
}
