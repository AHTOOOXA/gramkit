<script setup lang="ts">
import { useGetCurrentUserUsersMeGet } from '@/gen/hooks';

const { data: user, isLoading, error, refetch } = useGetCurrentUserUsersMeGet();
</script>

<template>
  <div class="test-generation p-4">
    <h2 class="text-2xl font-bold mb-4">Test Generated Hook</h2>

    <div v-if="isLoading">Loading user...</div>

    <div v-else-if="error">
      Error: {{ error.message }}
      <button class="ml-2 px-4 py-2 bg-blue-500 text-white rounded" @click="() => refetch()">
        Retry
      </button>
    </div>

    <div v-else-if="user">
      <h3 class="text-xl font-semibold mb-2">User Data:</h3>
      <pre class="bg-gray-100 p-4 rounded overflow-auto">{{ JSON.stringify(user, null, 2) }}</pre>
    </div>
  </div>
</template>
