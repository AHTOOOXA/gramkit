import { useMemo } from 'react';
import { useTranslations } from 'next-intl';

export interface AdminLabels {
  roleLabel: (role: string) => string;
  userTypeLabel: (userType: string) => string;
  /** Broadcast time slot ('MORNING' / 'EVENING' from the API, or the request's lowercase values). */
  broadcastSlotLabel: (slot: string) => string;
  broadcastTypeLabel: (messageType: string) => string;
  broadcastKeyboardLabel: (keyboardType: string | null | undefined) => string;
  /** Button labels a broadcast keyboard shows, as the preview chips render them. */
  broadcastKeyboardButtons: (
    keyboardType: string | null | undefined,
    buttonText: string | null | undefined
  ) => string[];
  /** Overview card label: `admin.overview.kpi.<key>`, else the card's English `label`. */
  cardLabel: (card: { key: string; label: string }) => string;
  /** Overview section title: `admin.overview.sections.<section>`, else the raw section. */
  sectionLabel: (section: string) => string;
  /** Overview card caveat: `admin.overview.caveats.<key>`, else the raw key. */
  caveatLabel: (caveat: string) => string;
}

/**
 * Translated labels for the enum-ish strings the admin API returns (role,
 * user type, broadcast slot / message type / keyboard, Overview cards). Unknown
 * values fall back to the raw string (or the card's English label), so a new
 * backend value shows up as-is instead of as a missing-key path (next-intl
 * would render the key path, hence the `t.has` checks).
 *
 * Port of template-vue's `app/admin/useAdminLabels.ts`.
 */
export function useAdminLabels(): AdminLabels {
  const t = useTranslations('admin');

  return useMemo(() => {
    const translate = (key: string, fallback: string) =>
      t.has(key) ? t(key) : fallback;

    const keyboardKeys: Record<string, string> = {
      none: 'broadcasts.composer.keyboardNone',
      main: 'broadcasts.composer.keyboardMain',
      daily: 'broadcasts.composer.keyboardDaily',
    };

    return {
      roleLabel: (role) => translate(`users.role.${role}`, role),
      userTypeLabel: (userType) =>
        translate(`users.type.${userType.toLowerCase()}`, userType),
      broadcastSlotLabel: (slot) =>
        translate(`broadcasts.slot.${slot.toLowerCase()}`, slot),
      broadcastTypeLabel: (messageType) =>
        translate(`broadcasts.type.${messageType}`, messageType),
      broadcastKeyboardLabel: (keyboardType) => {
        const type = keyboardType ?? 'none';
        const key = keyboardKeys[type];
        return key ? t(key) : type;
      },
      broadcastKeyboardButtons: (keyboardType, buttonText) => {
        if (keyboardType === 'main') {
          // An empty label falls back to the default button text too.
          if (buttonText) return [buttonText];
          return [t('broadcasts.composer.defaultButton')];
        }
        if (keyboardType === 'daily')
          return [t('broadcasts.composer.dailyButton')];
        return [];
      },
      cardLabel: (card) => translate(`overview.kpi.${card.key}`, card.label),
      sectionLabel: (section) =>
        translate(`overview.sections.${section}`, section),
      caveatLabel: (caveat) => translate(`overview.caveats.${caveat}`, caveat),
    };
  }, [t]);
}
