'use client';

import { useEffect, useState } from 'react';
import { User, LogOut, LogIn } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { useAuth, useLogout } from '@/hooks';
import { Link } from '@/i18n/navigation';
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

export function ProfileDropdown() {
  const { user, isGuest } = useAuth();
  const { mutate: logout } = useLogout();
  const t = useTranslations();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  // Not logged in or guest - show login icon
  if (isGuest || !user) {
    return (
      <Link href="/login">
        <Button variant="outline" size="icon">
          <LogIn className="h-[1.2rem] w-[1.2rem]" />
          <span className="sr-only">Login</span>
        </Button>
      </Link>
    );
  }

  // At this point, user is guaranteed to be non-null and authenticated
  // Get user initials for avatar fallback
  const getInitials = () => {
    if (user.tg_first_name && user.tg_last_name) {
      return `${user.tg_first_name[0] ?? ''}${user.tg_last_name[0] ?? ''}`.toUpperCase();
    }
    if (user.tg_first_name) {
      return user.tg_first_name.substring(0, 2).toUpperCase();
    }
    const username = user.username ?? user.tg_username;
    if (username) {
      return username.substring(0, 2).toUpperCase();
    }
    return 'U';
  };

  // Get user display name
  const getDisplayName = () => {
    // Prefer display_name if set
    if (user.display_name) {
      return user.display_name;
    }
    // Fall back to Telegram name
    if (user.tg_first_name && user.tg_last_name) {
      return `${user.tg_first_name} ${user.tg_last_name}`;
    }
    if (user.tg_first_name) {
      return user.tg_first_name;
    }
    // Fall back to username
    const username = user.username ?? user.tg_username;
    if (username) {
      return `@${username}`;
    }
    return 'User';
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="relative h-8 w-8 rounded-full">
          <Avatar className="h-8 w-8">
            <AvatarImage src={user.avatar_url ?? user.tg_photo_url ?? undefined} alt={getDisplayName()} />
            <AvatarFallback>{getInitials()}</AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium leading-none">{getDisplayName()}</p>
            {user.username && (
              <p className="text-xs leading-none text-muted-foreground">
                @{user.username}
              </p>
            )}
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/profile" className="cursor-pointer">
            <User className="mr-2 h-4 w-4" />
            <span>{t('nav.profile')}</span>
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => { logout(); }}
          className="cursor-pointer text-destructive focus:text-destructive"
        >
          <LogOut className="mr-2 h-4 w-4" />
          <span>{t('logout')}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
