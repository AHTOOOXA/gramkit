<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watchEffect } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Toaster, type ToasterProps } from 'vue-sonner';
import { usePlatform } from '@core/platform';
import { useGetCurrentUserUsersMeGet } from '@gen/hooks';
import { i18n } from '@app/i18n';
import { mode } from '@app/store/theme';
import { useAppInit } from '@app/composables/useAppInit';
import AppShell from '@app/presentation/components/AppShell.vue';
import { HOME_ROUTE } from '@app/router/router';
import DebugPanel from '@app/presentation/components/DebugPanel.vue';
import ErrorScreen from '@app/presentation/components/shared/ErrorScreen.vue';
import LoadingScreen from '@app/presentation/components/shared/LoadingScreen.vue';

const platform = usePlatform();
const { showBackButton, hideBackButton } = platform;
const route = useRoute();
const router = useRouter();

// App initialization state
const { isLoading, error } = useAppInit();

// Responsive toast position: top-center on mobile, bottom-right on desktop
const toastPosition = ref<ToasterProps['position']>('top-center');
const DESKTOP_BREAKPOINT = 768;

// Resolved theme for Sonner (light/dark only, not 'auto')
const toastTheme = computed(() => {
  const resolved = mode.state.value;
  return resolved === 'dark' ? 'dark' : 'light';
});

function updateToastPosition() {
  toastPosition.value = window.innerWidth >= DESKTOP_BREAKPOINT ? 'bottom-right' : 'top-center';
}

onMounted(() => {
  updateToastPosition();
  window.addEventListener('resize', updateToastPosition);
});

onUnmounted(() => {
  window.removeEventListener('resize', updateToastPosition);
});

// Language sync: Watch user data and update i18n locale
// Skip for guests - they use localStorage preference instead
const { data: user } = useGetCurrentUserUsersMeGet();
watchEffect(() => {
  const newUser = user.value;
  // Don't override locale for guest users - they manage via localStorage
  if (newUser?.user_type === 'GUEST') {
    return;
  }
  if (newUser?.language_code) {
    const lang = newUser.language_code.toLowerCase();
    const supportedLocales = ['en', 'ru'];
    if (supportedLocales.includes(lang)) {
      i18n.global.locale.value = lang as 'en' | 'ru';
    }
  }
});


// Handle back button
function setupBackButton() {
  const isHomePage = route.path === HOME_ROUTE;

  if (isHomePage) {
    hideBackButton();
  } else if (router.options.history.state.back) {
    showBackButton(() => router.back());
  } else {
    hideBackButton();
  }
}

// Watch for route changes
router.afterEach(() => {
  setupBackButton();
});

// Theme is managed by theme store
// No need to set it here

function onBeforeSegue(): void {
  requestAnimationFrame(() => {
    window.scrollTo(0, 0);
  });
}
</script>

<template>
  <div class="min-h-dvh flex flex-col bg-background text-foreground">
    <!-- Error state -->
    <ErrorScreen v-if="error" :error="error" />

    <!-- Loading state -->
    <LoadingScreen v-else-if="isLoading" />

    <!-- Ready state -->
    <template v-else>
      <Toaster
        :position="toastPosition"
        :theme="toastTheme"
        :toast-options="{ duration: 4000 }"
      />
      <DebugPanel />
      <AppShell>
        <RouterView v-slot="{ Component }">
          <transition
            name="default-segue"
            @before-enter="onBeforeSegue"
          >
            <div
              :key="$route.fullPath"
              class="h-full flex flex-col"
            >
              <component :is="Component" />
            </div>
          </transition>
        </RouterView>
      </AppShell>
    </template>
  </div>
</template>

<style>
/* Base styles */
html,
body {
  margin: 0;
  padding: 0;
  min-height: 100dvh;
  min-height: 100vh; /* fallback */
}

#app {
  min-height: 100dvh;
  min-height: 100vh; /* fallback */
  width: 100%;
}

/* Transition styles */
.default-segue-leave-active {
  visibility: hidden;
  height: 0;
  overflow: hidden;
}

.default-segue-enter-active {
  transition: opacity 500ms ease;
  will-change: opacity;
}

.default-segue-enter-from,
.default-segue-leave-to {
  opacity: 0;
}

</style>
