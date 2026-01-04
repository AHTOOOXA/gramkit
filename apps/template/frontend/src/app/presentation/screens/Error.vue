<script setup lang="ts">
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { AlertCircle } from 'lucide-vue-next';
import { useI18n } from 'vue-i18n';
import { useNavigation } from '@app/composables/useNavigation';

const { goHome } = useNavigation();
const { t } = useI18n();

const handleClick = () => {
  goHome();
};

const handleSupportClick = () => {
  window.open('https://t.me/ReallyCoolSupport', '_blank');
};
</script>

<template>
  <div class="h-screen flex flex-col items-center justify-center p-6 bg-background">
    <Card class="max-w-md w-full shadow-lg">
      <CardContent class="pt-6 pb-8 px-6">
        <div class="text-center">
          <div class="w-24 h-24 mx-auto mb-6 flex items-center justify-center bg-destructive/10 rounded-full">
            <AlertCircle class="size-12 text-destructive" />
          </div>
          <h1 class="text-3xl font-bold text-foreground mb-3">
            {{ t('error.title') }}
          </h1>
          <p class="text-base text-muted-foreground mb-6">
            {{ t('error.caption') }}
            <a
              href="https://t.me/ReallyCoolSupport"
              target="_blank"
              class="text-primary hover:underline transition-colors"
              @click.prevent="handleSupportClick"
            >
              @ReallyCoolSupport
            </a>
          </p>
          <Button
            class="w-full"
            @click="handleClick"
          >
            {{ t('error.button') }}
          </Button>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
