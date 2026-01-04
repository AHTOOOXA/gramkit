<script setup lang="ts">
import { computed } from 'vue';
import type { Component } from 'vue';

const props = defineProps<{
  loading: boolean;
  error?: Error | null;
  empty?: boolean;
  loadingComponent?: Component;
  errorComponent?: Component;
  emptyComponent?: Component;
}>();

const emit = defineEmits<{
  retry: [];
}>();

const showLoading = computed(() => props.loading);
const showError = computed(() => !props.loading && props.error);
const showEmpty = computed(() => !props.loading && !props.error && props.empty);
const showContent = computed(() => !props.loading && !props.error && !props.empty);
</script>

<template>
  <!-- Loading State -->
  <div v-if="showLoading">
    <component v-if="loadingComponent" :is="loadingComponent" />
    <slot v-else name="loading">
      <div class="content-state__loading">
        <div class="spinner" />
        <p>Loading...</p>
      </div>
    </slot>
  </div>

  <!-- Error State -->
  <div v-else-if="showError" class="content-state__error">
    <component v-if="errorComponent" :is="errorComponent" :error="error" />
    <slot v-else name="error" :error="error">
      <div class="error-card">
        <h3>Something went wrong</h3>
        <p>{{ error?.message || 'An error occurred' }}</p>
        <button @click="emit('retry')" class="btn-retry">
          Try Again
        </button>
      </div>
    </slot>
  </div>

  <!-- Empty State -->
  <div v-else-if="showEmpty">
    <component v-if="emptyComponent" :is="emptyComponent" />
    <slot v-else name="empty">
      <div class="empty-state">
        <p>No data available</p>
      </div>
    </slot>
  </div>

  <!-- Content -->
  <div v-else>
    <slot />
  </div>
</template>

<style scoped>
.content-state__loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-card {
  text-align: center;
  padding: 48px;
}

.btn-retry {
  margin-top: 16px;
  padding: 8px 16px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.empty-state {
  text-align: center;
  padding: 48px;
  color: #999;
}
</style>
