<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface Props {
  stats?: {
    total_users: number;
    users_by_role: Record<string, number>;
  };
}

defineProps<Props>();
</script>

<template>
  <div v-if="stats" class="grid gap-4 md:grid-cols-2">
    <Card>
      <CardHeader class="pb-2">
        <CardTitle class="text-sm font-medium text-muted-foreground">
          Total Users
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div class="text-3xl font-bold">
          {{ stats.total_users.toLocaleString() }}
        </div>
      </CardContent>
    </Card>

    <Card>
      <CardHeader class="pb-2">
        <CardTitle class="text-sm font-medium text-muted-foreground">
          Users by Role
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div class="space-y-1">
          <div
            v-for="([role, count]) in Object.entries(stats.users_by_role)"
            :key="role"
            class="flex justify-between"
          >
            <span class="text-muted-foreground">{{ role }}</span>
            <span class="font-medium">{{ count.toLocaleString() }}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
