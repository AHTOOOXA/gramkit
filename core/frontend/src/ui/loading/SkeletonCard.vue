<script setup lang="ts">
import Skeleton from './Skeleton.vue';

defineProps<{
  showImage?: boolean;
  showActions?: boolean;
}>();
</script>

<template>
  <div class="skeleton-card">
    <Skeleton
      v-if="showImage"
      variant="rectangular"
      width="100%"
      height="200px"
      class="skeleton-card__image"
    />

    <div class="skeleton-card__content">
      <Skeleton width="60%" height="24px" class="skeleton-card__title" />
      <Skeleton width="100%" height="16px" class="skeleton-card__line" />
      <Skeleton width="80%" height="16px" class="skeleton-card__line" />
    </div>

    <div v-if="showActions" class="skeleton-card__actions">
      <Skeleton width="80px" height="36px" />
      <Skeleton width="80px" height="36px" />
    </div>
  </div>
</template>

<style scoped>
.skeleton-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
}

.skeleton-card__content {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-card__actions {
  padding: 16px;
  display: flex;
  gap: 8px;
  border-top: 1px solid #e0e0e0;
}
</style>
