import { onBeforeUnmount, ref } from 'vue';
import { toast } from 'vue-sonner';

/**
 * Copy text to the clipboard; `copied` flips back after 2 s. On failure it
 * toasts `failedMessage()` (clipboard access can be denied, e.g. in some WebViews).
 */
export function useCopyText(failedMessage: () => string) {
  const copied = ref(false);
  let timer: ReturnType<typeof setTimeout> | undefined;

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      copied.value = true;
      clearTimeout(timer);
      timer = setTimeout(() => {
        copied.value = false;
      }, 2000);
    } catch {
      toast.error(failedMessage());
    }
  };

  onBeforeUnmount(() => {
    clearTimeout(timer);
  });

  return { copied, copy };
}
