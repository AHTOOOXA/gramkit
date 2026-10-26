'use client';

import { useTranslations } from 'next-intl';

import { useAdminLabels } from '@/hooks/useAdminLabels';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  broadcastCreateRequestKeyboardTypeEnum,
  type BroadcastCreateRequestKeyboardTypeEnum,
} from '@/src/gen/models/BroadcastCreateRequest';

export type KeyboardType = BroadcastCreateRequestKeyboardTypeEnum;

/**
 * KeyboardBuilder — inline-keyboard config for a broadcast: pick a keyboard
 * type and, for `main`, a custom button label. The types are the backend's
 * `KeyboardType` (`core.schemas.broadcasts`), read from the generated enum:
 * `main` is core's open-app button, `daily` is the one this app registers in
 * `tgbot/keyboards/notification_keyboards.py`. No arbitrary URL buttons.
 *
 * Port of template-vue's `KeyboardBuilder.vue`.
 */
export function KeyboardBuilder({
  keyboardType,
  buttonText,
  onKeyboardTypeChange,
  onButtonTextChange,
}: {
  keyboardType: KeyboardType;
  buttonText: string | null;
  onKeyboardTypeChange: (value: KeyboardType) => void;
  onButtonTextChange: (value: string | null) => void;
}) {
  const t = useTranslations('admin');
  const { broadcastKeyboardLabel } = useAdminLabels();

  return (
    <div className="flex flex-col gap-1.5">
      <Label>{t('broadcasts.composer.keyboard')}</Label>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <Select
          value={keyboardType}
          onValueChange={(value) => {
            onKeyboardTypeChange(value as KeyboardType);
          }}
        >
          <SelectTrigger className="w-full sm:w-72">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.values(broadcastCreateRequestKeyboardTypeEnum).map(
              (value) => (
                <SelectItem key={value} value={value}>
                  {broadcastKeyboardLabel(value)}
                </SelectItem>
              )
            )}
          </SelectContent>
        </Select>

        {keyboardType === 'main' && (
          <div className="flex flex-col gap-1.5">
            <Label
              htmlFor="broadcast-button-text"
              className="text-muted-foreground text-xs font-normal"
            >
              {t('broadcasts.composer.buttonText')}
            </Label>
            <Input
              id="broadcast-button-text"
              className="w-full sm:w-56"
              value={buttonText ?? ''}
              placeholder={t('broadcasts.composer.buttonTextPlaceholder')}
              onChange={(e) => {
                onButtonTextChange(e.target.value || null);
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
