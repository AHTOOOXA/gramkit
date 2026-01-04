<script setup lang="ts">
import { Check, X } from 'lucide-vue-next';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface Props {
  permissions?: {
    role: string;
    is_owner_in_config: boolean;
    permissions: string[];
  };
}

defineProps<Props>();

const ALL_PERMISSIONS = [
  'view_admin_panel',
  'view_stats',
  'view_aggregate_data',
  'change_roles',
  'protected_actions',
];
</script>

<template>
  <Card v-if="permissions">
    <CardHeader>
      <CardTitle>Your Access</CardTitle>
    </CardHeader>
    <CardContent class="space-y-4">
      <div class="flex gap-4">
        <div>
          <div class="text-sm text-muted-foreground">
            Role
          </div>
          <div class="text-lg font-semibold">
            {{ permissions.role }}
          </div>
        </div>
        <div>
          <div class="text-sm text-muted-foreground">
            Config Owner
          </div>
          <div class="text-lg font-semibold">
            {{ permissions.is_owner_in_config ? 'Yes' : 'No' }}
          </div>
        </div>
      </div>

      <div>
        <div class="text-sm text-muted-foreground mb-2">
          Permissions
        </div>
        <div class="space-y-1">
          <div
            v-for="perm in ALL_PERMISSIONS"
            :key="perm"
            class="flex items-center gap-2 text-sm"
          >
            <Check v-if="permissions.permissions.includes(perm)" class="h-4 w-4 text-green-500" />
            <X v-else class="h-4 w-4 text-red-500" />
            <span :class="permissions.permissions.includes(perm) ? '' : 'text-muted-foreground'">
              {{ perm }}
            </span>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>
