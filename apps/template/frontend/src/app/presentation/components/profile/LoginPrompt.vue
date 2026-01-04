<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import { LogIn, Lock } from 'lucide-vue-next'
import ProfileSection from './ProfileSection.vue'

const { t } = useI18n()
</script>

<template>
  <ProfileSection icon="&#128274;" :title="t('profile.login.title')">
    <div class="space-y-4">
      <!-- Lock icon with subtle animation -->
      <div class="flex justify-center">
        <Lock class="w-12 h-12 text-muted-foreground/50 motion-preset-pulse motion-duration-[3s] motion-loop-infinite" />
      </div>

      <!-- Description -->
      <div class="text-center">
        <p class="text-muted-foreground mb-4">{{ t('profile.login.description') }}</p>
      </div>

      <!-- Login button - links to login page -->
      <router-link to="/login">
        <Button
          class="w-full active:scale-95 hover:scale-[1.02] hover:-translate-y-1 hover:shadow-lg hover:shadow-primary/25 transition-all duration-200"
        >
          <LogIn class="w-4 h-4 mr-2" />
          {{ t('profile.login.button') }}
        </Button>
      </router-link>
    </div>
  </ProfileSection>
</template>
