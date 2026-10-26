import { useI18n } from 'vue-i18n';

/**
 * Translated labels for the enum-ish strings the admin API returns (role,
 * user type, broadcast slot / message type / keyboard, Overview cards). Unknown
 * values fall back to the raw string (or the card's English label), so a new
 * backend value shows up as-is instead of as a missing-key path.
 */
export function useAdminLabels(): {
  roleLabel: (role: string) => string;
  userTypeLabel: (userType: string) => string;
  /** Broadcast time slot ('MORNING' / 'EVENING' from the API, or the request's lowercase values). */
  broadcastSlotLabel: (slot: string) => string;
  broadcastTypeLabel: (messageType: string) => string;
  broadcastKeyboardLabel: (keyboardType: string | null | undefined) => string;
  /** Button labels a broadcast keyboard shows, as the preview chips render them. */
  broadcastKeyboardButtons: (keyboardType: string | null | undefined, buttonText: string | null | undefined) => string[];
  /** Overview card label: `admin.overview.kpi.<key>`, else the card's English `label`. */
  cardLabel: (card: { key: string; label: string }) => string;
  /** Overview section title: `admin.overview.sections.<section>`, else the raw section. */
  sectionLabel: (section: string) => string;
  /** Overview card caveat: `admin.overview.caveats.<key>`, else the raw key. */
  caveatLabel: (caveat: string) => string;
} {
  const { t, te } = useI18n();

  const translate = (key: string, fallback: string) => (te(key) ? t(key) : fallback);

  const keyboardKeys: Record<string, string> = {
    none: 'admin.broadcasts.composer.keyboardNone',
    main: 'admin.broadcasts.composer.keyboardMain',
    daily: 'admin.broadcasts.composer.keyboardDaily',
  };

  return {
    roleLabel: (role) => translate(`admin.users.role.${role}`, role),
    userTypeLabel: (userType) => translate(`admin.users.type.${userType.toLowerCase()}`, userType),
    broadcastSlotLabel: (slot) => translate(`admin.broadcasts.slot.${slot.toLowerCase()}`, slot),
    broadcastTypeLabel: (messageType) => translate(`admin.broadcasts.type.${messageType}`, messageType),
    broadcastKeyboardLabel: (keyboardType) => {
      const type = keyboardType ?? 'none';
      return keyboardKeys[type] ? t(keyboardKeys[type]) : type;
    },
    broadcastKeyboardButtons: (keyboardType, buttonText) => {
      if (keyboardType === 'main') return [buttonText || t('admin.broadcasts.composer.defaultButton')];
      if (keyboardType === 'daily') return [t('admin.broadcasts.composer.dailyButton')];
      return [];
    },
    cardLabel: (card) => translate(`admin.overview.kpi.${card.key}`, card.label),
    sectionLabel: (section) => translate(`admin.overview.sections.${section}`, section),
    caveatLabel: (caveat) => translate(`admin.overview.caveats.${caveat}`, caveat),
  };
}
