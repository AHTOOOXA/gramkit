<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGetCurrentUserUsersMeGet } from '@/gen/hooks'

import UserInfoSection from '@app/presentation/components/profile/UserInfoSection.vue'
import FriendsSection from '@app/presentation/components/profile/FriendsSection.vue'
import NotificationSection from '@app/presentation/components/profile/NotificationSection.vue'
import TelegramSection from '@app/presentation/components/profile/TelegramSection.vue'
import LoginPrompt from '@app/presentation/components/profile/LoginPrompt.vue'
import AuthRequired from '@app/presentation/components/profile/AuthRequired.vue'
import RbacDemo from '@app/presentation/components/profile/RbacDemo.vue'

const { t } = useI18n()

const { data: user, isLoading } = useGetCurrentUserUsersMeGet()
// User is authenticated if they have a registered account (not a guest)
const isAuthenticated = computed(() => user.value?.user_type === 'REGISTERED')
</script>

<template>
  <div class="py-6 space-y-6">
    <!-- Header with blur-in effect (#1, #2) -->
    <div class="text-center mb-8">
      <h1
        class="text-2xl font-bold mb-2 motion-blur-in-[6px] motion-scale-in-[0.95] motion-opacity-in-[0%] motion-duration-[0.5s] motion-duration-[0.7s]/blur motion-ease-spring-smooth"
      >
        {{ t('profile.title') }}
      </h1>
      <p
        class="text-muted-foreground motion-blur-in-[4px] motion-opacity-in-[0%] motion-duration-[0.4s] motion-delay-[0.15s] motion-ease-spring-smooth"
      >
        {{ t('profile.subtitle') }}
      </p>
    </div>

    <!-- Loading state with pulse (#10) -->
    <div v-if="isLoading" class="text-center py-8">
      <p class="text-muted-foreground motion-preset-pulse motion-duration-[1.5s] motion-loop-infinite">
        {{ t('common.loading') }}
      </p>
    </div>

    <template v-else>
      <!-- User Info - shows login prompt or user data (#14) -->
      <Transition
        enter-active-class="motion-scale-in-[0.95] motion-blur-in-[2px] motion-opacity-in-[0%] motion-duration-[0.3s] motion-ease-spring-smooth"
        leave-active-class="motion-opacity-out-[0%] motion-duration-[0.2s]"
        mode="out-in"
      >
        <div v-if="isAuthenticated && user" key="user-info">
          <UserInfoSection :user="user" />
        </div>
        <div v-else key="login-prompt">
          <LoginPrompt />
        </div>
      </Transition>

      <!-- Platform section - available for all (#3, #4) -->
      <div
        class="motion-opacity-in-[0%] motion-translate-y-in-[20px] motion-blur-in-[3px] motion-duration-[0.4s] motion-duration-[0.6s]/blur motion-delay-[0.1s] motion-ease-spring-smooth"
      >
        <TelegramSection />
      </div>

      <!-- Auth-required sections with staggered animations (#3, #15) -->
      <div
        class="motion-opacity-in-[0%] motion-translate-y-in-[20px] motion-blur-in-[3px] motion-duration-[0.4s] motion-duration-[0.6s]/blur motion-delay-[0.18s] motion-ease-spring-smooth"
      >
        <AuthRequired :locked="!isAuthenticated">
          <FriendsSection />
        </AuthRequired>
      </div>

      <div
        class="motion-opacity-in-[0%] motion-translate-y-in-[20px] motion-blur-in-[3px] motion-duration-[0.4s] motion-duration-[0.6s]/blur motion-delay-[0.26s] motion-ease-spring-smooth"
      >
        <AuthRequired :locked="!isAuthenticated">
          <NotificationSection />
        </AuthRequired>
      </div>

      <!-- RBAC Demo -->
      <div
        class="motion-opacity-in-[0%] motion-translate-y-in-[20px] motion-blur-in-[3px] motion-duration-[0.4s] motion-duration-[0.6s]/blur motion-delay-[0.34s] motion-ease-spring-smooth"
      >
        <RbacDemo />
      </div>
    </template>

    <!-- CTA card with bounce entrance (#12) and hover glow (#19) -->
    <div
      class="group bg-muted/50 rounded-xl p-4 text-center motion-scale-in-[0.9] motion-opacity-in-[0%] motion-duration-[0.5s] motion-delay-[0.37s] motion-ease-spring-bouncy transition-all duration-300 hover:bg-muted/70 hover:shadow-lg hover:shadow-primary/10"
    >
      <p class="text-sm text-muted-foreground mb-2">
        {{ t('profile.ctaText') }}
      </p>
      <router-link
        to="/demo"
        class="text-primary hover:underline font-medium inline-flex items-center gap-1"
      >
        {{ t('profile.ctaLink') }}
        <!-- CTA arrow wiggle (#6) -->
        <span class="inline-block transition-transform duration-200 group-hover:translate-x-1 group-hover:motion-preset-wiggle-sm">
          &rarr;
        </span>
      </router-link>
    </div>
  </div>
</template>
