<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { useGetFriendsFriendsGet, useCreateInviteCreateInviteGet } from '@/gen/hooks'
import { getErrorMessage } from '@core/errors'
import ProfileSection from './ProfileSection.vue'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Copy, Check, UserPlus } from 'lucide-vue-next'

const { t } = useI18n()

const { data: friends, isPending, error, refetch } = useGetFriendsFriendsGet()
const { refetch: createInvite, isFetching: isCreatingInvite } = useCreateInviteCreateInviteGet({
  query: { enabled: false },
})

const inviteLink = ref<string | null>(null)
const copied = ref(false)

const handleCreateInvite = async () => {
  try {
    const { data } = await createInvite()
    if (data) {
      inviteLink.value = data
    }
  } catch (err) {
    toast.error(getErrorMessage(err))
  }
}

const copyInvite = async () => {
  if (!inviteLink.value) return
  await navigator.clipboard.writeText(inviteLink.value)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}
</script>

<template>
  <ProfileSection icon="&#128101;" :title="t('profile.friends.title')">
    <!-- Error state -->
    <Alert v-if="error" variant="destructive">
      <AlertDescription class="flex items-center justify-between gap-2">
        <span class="text-sm">{{ getErrorMessage(error) }}</span>
        <Button size="sm" variant="outline" @click="refetch()">
          {{ t('common.retry', 'Retry') }}
        </Button>
      </AlertDescription>
    </Alert>

    <div v-else class="space-y-4">
      <!-- Friends count -->
      <p class="text-sm text-muted-foreground">
        {{ t('profile.friends.count', { count: friends?.length ?? 0 }) }}
      </p>

      <!-- Friends list -->
      <div v-if="friends?.length" class="space-y-2">
        <div
          v-for="(friend, index) in friends.slice(0, 5)"
          :key="friend.id ?? index"
          class="flex items-center gap-3 p-2 bg-muted rounded-lg"
        >
          <Avatar class="h-8 w-8">
            <AvatarFallback class="text-xs">
              {{ (friend.display_name || 'U')[0].toUpperCase() }}
            </AvatarFallback>
          </Avatar>
          <span class="text-sm">
            {{ friend.display_name || 'User' }}
          </span>
        </div>
        <p v-if="friends.length > 5" class="text-xs text-muted-foreground text-center">
          {{ t('profile.friends.andMore', { count: friends.length - 5 }) }}
        </p>
      </div>

      <div v-else-if="!isPending" class="text-sm text-muted-foreground">
        {{ t('profile.friends.noFriends') }}
      </div>

      <!-- Invite section -->
      <div class="pt-2 border-t space-y-2">
        <Button
          :disabled="isCreatingInvite"
          variant="outline"
          class="w-full"
          @click="handleCreateInvite"
        >
          <UserPlus class="w-4 h-4 mr-2" />
          {{ t('profile.friends.createInvite') }}
        </Button>

        <div v-if="inviteLink" class="flex gap-2">
          <input
            :value="inviteLink"
            readonly
            class="flex-1 px-3 py-2 text-xs bg-muted rounded-lg font-mono"
          />
          <Button size="icon" variant="outline" @click="copyInvite">
            <Check v-if="copied" class="w-4 h-4 text-green-500" />
            <Copy v-else class="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  </ProfileSection>
</template>
