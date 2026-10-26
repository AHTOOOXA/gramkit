import { useEffect, useState } from 'react';

/**
 * useDebouncedValue — the value, updated only after it stopped changing for
 * `ms` milliseconds. Used by the admin search box so a list refetches once per
 * typing pause, not once per keystroke.
 *
 * @example
 * const debounced = useDebouncedValue(search, 300);
 */
export function useDebouncedValue<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const id = setTimeout(() => {
      setDebounced(value);
    }, ms);
    return () => {
      clearTimeout(id);
    };
  }, [value, ms]);

  return debounced;
}
