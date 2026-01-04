<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlatform } from '@core/platform'
import { useLogoutAuthLogoutPost, getCurrentUserUsersMeGetQueryKey } from '@/gen/hooks'
import { useQueryClient } from '@tanstack/vue-query'
import ProfileSection from './ProfileSection.vue'
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import {
  LogOut,
  Smartphone,
  Mail,
  ChevronDown,
  ChevronUp,
  Flame,
  Trophy,
  Calendar,
  Check,
  Plus
} from 'lucide-vue-next'
import LinkTelegramModal from './LinkTelegramModal.vue'
import AddEmailModal from './AddEmailModal.vue'
import type { UserSchema } from '@/gen/models'

const props = defineProps<{
  user: UserSchema
}>()

const { t } = useI18n()
const platform = usePlatform()
const queryClient = useQueryClient()

const showLinkTelegramModal = ref(false)
const showAddEmailModal = ref(false)
const showTelegramDetails = ref(false)
const showEmailDetails = ref(false)

const displayName = computed(() => props.user.display_name || 'User')

const initials = computed(() => {
  const first = props.user.display_name?.[0] ?? props.user.username?.[0] ?? 'U'
  return first.toUpperCase()
})

const authMethod = computed(() => platform.isTelegram ? 'telegram' : 'web')
const hasTelegram = computed(() => !!props.user.telegram_id)
const hasEmail = computed(() => !!props.user.email)

const memberSince = computed(() => {
  if (!props.user.created_at) return null
  return new Date(props.user.created_at).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })
})

const formatGender = (male: boolean | null | undefined) => {
  if (male === null || male === undefined) return '—'
  return male ? t('profile.user.gender.male') : t('profile.user.gender.female')
}

const formatDetailValue = (value: unknown): string => {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? t('common.yes') : t('common.no')
  return String(value)
}

const { mutate: logout, isPending: isLoggingOut } = useLogoutAuthLogoutPost({
  mutation: {
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getCurrentUserUsersMeGetQueryKey() })
    }
  }
})

const handleLogout = () => {
  logout()
}

const handleLinkSuccess = () => {
  queryClient.invalidateQueries({ queryKey: getCurrentUserUsersMeGetQueryKey() })
}
</script>

<template>
  <ProfileSection icon="&#128100;" :title="t('profile.user.title')">
    <div class="space-y-6">
      <!-- Header -->
      <div class="flex items-center gap-4">
        <Avatar class="h-16 w-16">
          <AvatarImage v-if="props.user.avatar_url" :src="props.user.avatar_url" :alt="displayName" />
          <AvatarFallback class="text-xl">{{ initials }}</AvatarFallback>
        </Avatar>
        <div class="flex-1">
          <p class="font-semibold text-lg">{{ displayName }}</p>
          <p class="text-sm text-muted-foreground">@{{ props.user.username || 'user' }}</p>
          <p v-if="memberSince" class="text-xs text-muted-foreground">
            {{ t('profile.user.memberSince', { date: memberSince }) }}
          </p>
        </div>
      </div>

      <!-- Activity Stats -->
      <div>
        <p class="text-xs font-semibold text-muted-foreground mb-3">{{ t('profile.user.sections.activity') }}</p>
        <div class="grid grid-cols-3 gap-2">
          <div class="bg-muted rounded-lg p-3 text-center">
            <Flame class="h-4 w-4 mx-auto mb-1 text-muted-foreground" />
            <p class="text-2xl font-bold">{{ props.user.current_streak ?? 0 }}</p>
            <p class="text-xs text-muted-foreground">{{ t('profile.user.stats.currentStreak') }}</p>
          </div>
          <div class="bg-muted rounded-lg p-3 text-center">
            <Trophy class="h-4 w-4 mx-auto mb-1 text-muted-foreground" />
            <p class="text-2xl font-bold">{{ props.user.best_streak ?? 0 }}</p>
            <p class="text-xs text-muted-foreground">{{ t('profile.user.stats.bestStreak') }}</p>
          </div>
          <div class="bg-muted rounded-lg p-3 text-center">
            <Calendar class="h-4 w-4 mx-auto mb-1 text-muted-foreground" />
            <p class="text-2xl font-bold">{{ props.user.total_active_days ?? 0 }}</p>
            <p class="text-xs text-muted-foreground">{{ t('profile.user.stats.totalDays') }}</p>
          </div>
        </div>
      </div>

      <!-- Preferences -->
      <div>
        <p class="text-xs font-semibold text-muted-foreground mb-2">{{ t('profile.user.sections.preferences') }}</p>
        <div class="divide-y">
          <div class="flex items-center justify-between py-2">
            <span class="text-sm text-muted-foreground">{{ t('profile.user.prefs.language') }}</span>
            <span class="text-sm">{{ props.user.language_code || '—' }}</span>
          </div>
          <div class="flex items-center justify-between py-2">
            <span class="text-sm text-muted-foreground">{{ t('profile.user.prefs.timezone') }}</span>
            <span class="text-sm">{{ props.user.timezone || '—' }}</span>
          </div>
          <div class="flex items-center justify-between py-2">
            <span class="text-sm text-muted-foreground">{{ t('profile.user.prefs.birthDate') }}</span>
            <span class="text-sm">{{ props.user.birth_date || '—' }}</span>
          </div>
          <div class="flex items-center justify-between py-2">
            <span class="text-sm text-muted-foreground">{{ t('profile.user.prefs.gender') }}</span>
            <span class="text-sm">{{ formatGender(props.user.male) }}</span>
          </div>
        </div>
      </div>

      <!-- Auth Methods -->
      <div>
        <p class="text-xs font-semibold text-muted-foreground mb-3">{{ t('profile.user.sections.authMethods') }}</p>
        <div class="space-y-2">
          <!-- Telegram Auth -->
          <div class="border rounded-lg p-3">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="bg-muted rounded-full p-2">
                  <Smartphone class="h-4 w-4" />
                </div>
                <div>
                  <p class="text-sm font-medium">Telegram</p>
                  <p class="text-xs text-muted-foreground">
                    {{ hasTelegram ? (props.user.tg_username ? `@${props.user.tg_username}` : props.user.tg_first_name) : t('common.notConnected') }}
                  </p>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <template v-if="hasTelegram">
                  <Check class="h-4 w-4 text-green-500" />
                  <Button variant="ghost" size="sm" @click="showTelegramDetails = !showTelegramDetails">
                    <ChevronUp v-if="showTelegramDetails" class="h-4 w-4" />
                    <ChevronDown v-else class="h-4 w-4" />
                  </Button>
                </template>
                <Button v-else variant="outline" size="sm" @click="showLinkTelegramModal = true">
                  <Plus class="h-3 w-3 mr-1" />
                  {{ t('common.link') }}
                </Button>
              </div>
            </div>
            <div v-if="showTelegramDetails && hasTelegram" class="mt-3 pt-3 border-t space-y-1">
              <div class="flex items-center justify-between text-xs">
                <span class="text-muted-foreground">ID</span>
                <span class="font-mono">{{ props.user.telegram_id }}</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-muted-foreground">{{ t('profile.user.tg.firstName') }}</span>
                <span>{{ formatDetailValue(props.user.tg_first_name) }}</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-muted-foreground">{{ t('profile.user.tg.lastName') }}</span>
                <span>{{ formatDetailValue(props.user.tg_last_name) }}</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-muted-foreground">{{ t('profile.user.tg.username') }}</span>
                <span>{{ formatDetailValue(props.user.tg_username) }}</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-muted-foreground">{{ t('profile.user.tg.languageCode') }}</span>
                <span>{{ formatDetailValue(props.user.tg_language_code) }}</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-muted-foreground">{{ t('profile.user.tg.isPremium') }}</span>
                <span>{{ formatDetailValue(props.user.tg_is_premium) }}</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-muted-foreground">{{ t('profile.user.tg.isBot') }}</span>
                <span>{{ formatDetailValue(props.user.tg_is_bot) }}</span>
              </div>
            </div>
          </div>

          <!-- Email Auth -->
          <div class="border rounded-lg p-3">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="bg-muted rounded-full p-2">
                  <Mail class="h-4 w-4" />
                </div>
                <div>
                  <p class="text-sm font-medium">Email</p>
                  <p class="text-xs text-muted-foreground">
                    {{ hasEmail ? props.user.email : t('common.notConnected') }}
                  </p>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <template v-if="hasEmail">
                  <Check class="h-4 w-4 text-green-500" />
                  <Button variant="ghost" size="sm" @click="showEmailDetails = !showEmailDetails">
                    <ChevronUp v-if="showEmailDetails" class="h-4 w-4" />
                    <ChevronDown v-else class="h-4 w-4" />
                  </Button>
                </template>
                <Button v-else variant="outline" size="sm" @click="showAddEmailModal = true">
                  <Plus class="h-3 w-3 mr-1" />
                  {{ t('common.link') }}
                </Button>
              </div>
            </div>
            <div v-if="showEmailDetails && hasEmail" class="mt-3 pt-3 border-t space-y-1">
              <div class="flex items-center justify-between text-xs">
                <span class="text-muted-foreground">{{ t('profile.user.email.address') }}</span>
                <span>{{ props.user.email }}</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-muted-foreground">{{ t('profile.user.email.verified') }}</span>
                <span>{{ formatDetailValue(props.user.email_verified) }}</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-muted-foreground">{{ t('profile.user.email.verifiedAt') }}</span>
                <span>{{ formatDetailValue(props.user.email_verified_at) }}</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-muted-foreground">{{ t('profile.user.email.lastLogin') }}</span>
                <span>{{ formatDetailValue(props.user.last_login_at) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Logout button (only for web auth) -->
      <Button
        v-if="authMethod === 'web'"
        variant="outline"
        class="w-full text-destructive hover:text-destructive hover:bg-destructive/10"
        :disabled="isLoggingOut"
        @click="handleLogout"
      >
        <LogOut class="w-4 h-4 mr-2" />
        {{ isLoggingOut ? t('profile.user.loggingOut') : t('profile.user.logout') }}
      </Button>
    </div>

    <LinkTelegramModal
      v-model:open="showLinkTelegramModal"
      @success="handleLinkSuccess"
    />

    <AddEmailModal
      v-model:open="showAddEmailModal"
      @success="handleLinkSuccess"
    />
  </ProfileSection>
</template>
