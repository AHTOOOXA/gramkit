<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

type KeyboardType = 'none' | 'main' | 'daily';

/**
 * KeyboardBuilder — inline-keyboard config for a broadcast: pick a keyboard
 * type and, for `main`, a custom button label. The types are the backend's
 * `KeyboardType` (`core.schemas.broadcasts`): `main` is core's open-app button,
 * `daily` is the one this app registers in
 * `tgbot/keyboards/notification_keyboards.py`. No arbitrary URL buttons.
 *
 * TODO: extract to core when a third Vue app needs this (each Vue app keeps
 * its own copy for now, built on its own `ui/*` kit).
 */
const props = defineProps<{
  keyboardType: KeyboardType;
  buttonText: string | null;
}>();

const emit = defineEmits<{
  'update:keyboardType': [value: KeyboardType];
  'update:buttonText': [value: string | null];
}>();

const { t } = useI18n();

const typeModel = computed<KeyboardType>({
  get: () => props.keyboardType,
  set: (v) => emit('update:keyboardType', v),
});

const buttonModel = computed<string>({
  get: () => props.buttonText ?? '',
  set: (v) => emit('update:buttonText', v || null),
});

const showButtonText = computed(() => props.keyboardType === 'main');
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <Label>{{ t('admin.broadcasts.composer.keyboard') }}</Label>
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
      <Select v-model="typeModel">
        <SelectTrigger class="w-full sm:w-72">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="none">{{ t('admin.broadcasts.composer.keyboardNone') }}</SelectItem>
          <SelectItem value="main">{{ t('admin.broadcasts.composer.keyboardMain') }}</SelectItem>
          <SelectItem value="daily">{{ t('admin.broadcasts.composer.keyboardDaily') }}</SelectItem>
        </SelectContent>
      </Select>

      <div
        v-if="showButtonText"
        class="flex flex-col gap-1.5"
      >
        <Label
          for="broadcast-button-text"
          class="text-xs font-normal text-muted-foreground"
        >
          {{ t('admin.broadcasts.composer.buttonText') }}
        </Label>
        <Input
          id="broadcast-button-text"
          v-model="buttonModel"
          class="w-full sm:w-56"
          :placeholder="t('admin.broadcasts.composer.buttonTextPlaceholder')"
        />
      </div>
    </div>
  </div>
</template>
