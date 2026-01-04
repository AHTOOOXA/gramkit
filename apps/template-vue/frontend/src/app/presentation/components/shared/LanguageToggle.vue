<script setup lang="ts">
import { Globe, Check } from 'lucide-vue-next';
import { useLanguageService, type SupportedLocale } from '@app/composables/useLanguageService';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

const { currentLocale, supportedLocales, changeLanguage } = useLanguageService();

const languageNames: Record<string, string> = {
  en: 'English',
  ru: 'Русский',
};

const handleLanguageChange = (lang: SupportedLocale) => {
  void changeLanguage(lang);
};
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button variant="outline" size="icon">
        <Globe class="h-[1.2rem] w-[1.2rem]" />
        <span class="sr-only">Toggle language</span>
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end">
      <DropdownMenuItem
        v-for="lang in supportedLocales"
        :key="lang"
        class="flex items-center justify-between gap-2"
        @click="handleLanguageChange(lang)"
      >
        <span>{{ languageNames[lang] }}</span>
        <Check v-if="currentLocale === lang" class="h-4 w-4" />
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
