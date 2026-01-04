<script setup lang="ts">
import { computed } from 'vue';
import { User, LogOut, LogIn } from 'lucide-vue-next';
import { useI18n } from 'vue-i18n';
import { RouterLink } from 'vue-router';
import { useGetCurrentUserUsersMeGet } from '@/gen/hooks';
import { useLogout } from '@app/composables/useLogout';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';

const { t } = useI18n();

const { data: user } = useGetCurrentUserUsersMeGet();
const { mutate: logout } = useLogout();

const isLoggedIn = computed(() => user.value && user.value.user_type !== 'GUEST');

const getInitials = () => {
  if (!user.value) return 'U';

  if (user.value.tg_first_name && user.value.tg_last_name) {
    return `${user.value.tg_first_name[0]}${user.value.tg_last_name[0]}`.toUpperCase();
  }
  if (user.value.tg_first_name) {
    return user.value.tg_first_name.substring(0, 2).toUpperCase();
  }
  if (user.value.username || user.value.tg_username) {
    const username = user.value.username || user.value.tg_username || '';
    return username.substring(0, 2).toUpperCase();
  }
  return 'U';
};

const getDisplayName = () => {
  if (!user.value) return 'User';

  if (user.value.display_name) {
    return user.value.display_name;
  }
  if (user.value.tg_first_name && user.value.tg_last_name) {
    return `${user.value.tg_first_name} ${user.value.tg_last_name}`;
  }
  if (user.value.tg_first_name) {
    return user.value.tg_first_name;
  }
  const username = user.value.username || user.value.tg_username;
  if (username) {
    return `@${username}`;
  }
  return 'User';
};

const handleLogout = () => {
  logout();
};
</script>

<template>
  <!-- Not logged in - show login icon linking to /login -->
  <RouterLink v-if="!isLoggedIn" to="/login">
    <Button variant="outline" size="icon">
      <LogIn class="h-[1.2rem] w-[1.2rem]" />
      <span class="sr-only">Login</span>
    </Button>
  </RouterLink>

  <!-- Logged in - show dropdown with user info -->
  <DropdownMenu v-else>
    <DropdownMenuTrigger as-child>
      <Button variant="ghost" class="relative h-8 w-8 rounded-full">
        <Avatar class="h-8 w-8">
          <AvatarImage
            :src="user?.avatar_url ?? user?.tg_photo_url ?? ''"
            :alt="getDisplayName()"
          />
          <AvatarFallback>{{ getInitials() }}</AvatarFallback>
        </Avatar>
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" class="w-56">
      <DropdownMenuLabel>
        <div class="flex flex-col space-y-1">
          <p class="text-sm font-medium leading-none">{{ getDisplayName() }}</p>
          <p v-if="user?.username" class="text-xs leading-none text-muted-foreground">
            @{{ user.username }}
          </p>
        </div>
      </DropdownMenuLabel>
      <DropdownMenuSeparator />
      <DropdownMenuItem as-child>
        <RouterLink to="/profile" class="cursor-pointer flex items-center">
          <User class="mr-2 h-4 w-4" />
          <span>{{ t('nav.profile') }}</span>
        </RouterLink>
      </DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem
        class="cursor-pointer text-destructive focus:text-destructive"
        @click="handleLogout"
      >
        <LogOut class="mr-2 h-4 w-4" />
        <span>{{ t('logout') }}</span>
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
