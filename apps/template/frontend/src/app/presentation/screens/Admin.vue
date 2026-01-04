<script setup lang="ts">
import { computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useGetCurrentUserUsersMeGet } from '@gen/hooks';
import { useGetMyPermissionsAdminMeGet } from '@gen/hooks/useGetMyPermissionsAdminMeGet';
import { useGetStatsAdminStatsGet } from '@gen/hooks/useGetStatsAdminStatsGet';
import YourAccessCard from '@app/presentation/components/admin/YourAccessCard.vue';
import StatsCards from '@app/presentation/components/admin/StatsCards.vue';
import ProtectedActionDemo from '@app/presentation/components/admin/ProtectedActionDemo.vue';

const router = useRouter();
const { data: user, isLoading } = useGetCurrentUserUsersMeGet();

const isAdmin = computed(() => !!user.value && ['admin', 'owner'].includes(user.value.role ?? ''));

const { data: permissions } = useGetMyPermissionsAdminMeGet({
  query: {
    enabled: () => isAdmin.value,
  }
});
const { data: stats } = useGetStatsAdminStatsGet({
  query: {
    enabled: () => isAdmin.value,
  }
});

// Redirect non-admins
watch([user, isLoading], ([currentUser, loading]) => {
  if (!loading && currentUser && !['admin', 'owner'].includes(currentUser.role ?? '')) {
    router.replace('/demo');
  }
});
</script>

<template>
  <div class="container py-6 space-y-6 max-w-4xl mx-auto">
    <div v-if="isLoading" class="p-6">
      Loading...
    </div>
    <template v-else-if="isAdmin">
      <!-- Header with blur-in effect -->
      <div class="text-center mb-8">
        <h1
          class="text-2xl font-bold mb-2 motion-blur-in-[6px] motion-scale-in-[0.95] motion-opacity-in-[0%] motion-duration-[0.5s] motion-duration-[0.7s]/blur motion-ease-spring-smooth"
        >
          RBAC Demo
        </h1>
        <p
          class="text-muted-foreground motion-blur-in-[4px] motion-opacity-in-[0%] motion-duration-[0.4s] motion-delay-[0.15s] motion-ease-spring-smooth"
        >
          This page demonstrates role-based access control
        </p>
      </div>

      <!-- Your role and permissions -->
      <div
        class="motion-opacity-in-[0%] motion-translate-y-in-[20px] motion-blur-in-[3px] motion-duration-[0.4s] motion-duration-[0.6s]/blur motion-delay-[0.2s] motion-ease-spring-smooth"
      >
        <YourAccessCard :permissions="permissions" />
      </div>

      <!-- Safe aggregate stats -->
      <div
        class="motion-opacity-in-[0%] motion-translate-y-in-[20px] motion-blur-in-[3px] motion-duration-[0.4s] motion-duration-[0.6s]/blur motion-delay-[0.3s] motion-ease-spring-smooth"
      >
        <StatsCards :stats="stats" />
      </div>

      <!-- Try protected action -->
      <div
        class="motion-opacity-in-[0%] motion-translate-y-in-[20px] motion-blur-in-[3px] motion-duration-[0.4s] motion-duration-[0.6s]/blur motion-delay-[0.4s] motion-ease-spring-smooth"
      >
        <ProtectedActionDemo :can-execute="permissions?.permissions.includes('protected_actions') ?? false" />
      </div>

      <!-- CTA card with bounce entrance and hover glow -->
      <div
        class="group bg-muted/50 rounded-xl p-4 text-center motion-scale-in-[0.9] motion-opacity-in-[0%] motion-duration-[0.5s] motion-delay-[0.5s] motion-ease-spring-bouncy transition-all duration-300 hover:bg-muted/70 hover:shadow-lg hover:shadow-primary/10"
      >
        <p class="text-sm text-muted-foreground mb-2">
          {{ $t('admin.ctaText') }}
        </p>
        <router-link
          to="/demo"
          class="text-primary hover:underline font-medium inline-flex items-center gap-1"
        >
          {{ $t('admin.ctaLink') }}
          <!-- CTA arrow wiggle -->
          <span
            class="inline-block transition-transform duration-200 group-hover:translate-x-1 group-hover:motion-preset-wiggle-sm"
          >
            &rarr;
          </span>
        </router-link>
      </div>
    </template>
  </div>
</template>
