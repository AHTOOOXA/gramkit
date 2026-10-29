// The production app built on gramkit, linked from the landing hero.
// The sync to the public repo skips this one file in its scrub and leak guard,
// so the link survives there (scripts/sync-to-oss.sh). Keep it here, not in the
// locale files.
export const PRODUCTION_SITE = {
  label: 'tarotmeow.ru',
  url: 'https://tarotmeow.ru',
} as const;
