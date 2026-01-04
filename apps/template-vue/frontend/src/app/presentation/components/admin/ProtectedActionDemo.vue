<script setup lang="ts">
import { ref } from 'vue';
import { Lock, CheckCircle, XCircle } from 'lucide-vue-next';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useDemoProtectedActionAdminDemoActionPost } from '@gen/hooks/useDemoProtectedActionAdminDemoActionPost';

interface Props {
  canExecute: boolean;
}

defineProps<Props>();

const result = ref<{ success: boolean; message: string } | null>(null);

const { mutate, isPending } = useDemoProtectedActionAdminDemoActionPost({
  mutation: {
    onSuccess: (data) => {
      result.value = { success: true, message: data.message };
    },
    onError: () => {
      result.value = { success: false, message: 'Access denied - owner role required' };
    },
  },
});

const handleExecute = () => {
  mutate();
};
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>Try Protected Action</CardTitle>
    </CardHeader>
    <CardContent class="space-y-4">
      <p class="text-sm text-muted-foreground">
        This action requires <strong>owner</strong> role. Click to see what happens with your current role.
      </p>

      <Button
        :disabled="isPending"
        :variant="canExecute ? 'default' : 'secondary'"
        @click="handleExecute"
      >
        <Lock class="h-4 w-4 mr-2" />
        Execute Protected Action
      </Button>

      <div
        v-if="result"
        :class="[
          'flex items-center gap-2 p-3 rounded-lg',
          result.success
            ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400'
            : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'
        ]"
      >
        <CheckCircle v-if="result.success" class="h-5 w-5" />
        <XCircle v-else class="h-5 w-5" />
        <span>{{ result.message }}</span>
      </div>
    </CardContent>
  </Card>
</template>
