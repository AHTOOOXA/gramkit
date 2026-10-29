import { useI18n } from 'vue-i18n';

/**
 * Read a list (or a single string) from the locale files raw, without vue-i18n's message compiler.
 *
 * The landing copy is full of literal `@handles`, `<app>` placeholders and code, which the compiler
 * would treat as linked messages, HTML (a dev warning) or interpolation. Raw values render exactly as
 * written in the JSON, so don't escape anything (`{'@'}`) inside the keys read this way. Strings read
 * with `t()` still go through the compiler and do need escaping.
 */
export function useMessageList() {
  const { tm } = useI18n();

  const list = <T = string>(key: string): T[] => {
    const value = tm(key) as unknown;
    return Array.isArray(value) ? (value as T[]) : [];
  };
  const raw = (key: string): string => {
    const value = tm(key) as unknown;
    return typeof value === 'string' ? value : key;
  };

  return { list, raw };
}
