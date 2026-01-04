import { User } from 'lucide-react';

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';

interface UserAvatarProps {
  src?: string | null;
  alt?: string;
  fallback?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function UserAvatar({
  src,
  alt = 'User avatar',
  fallback,
  size = 'md',
}: UserAvatarProps) {
  const sizeClasses = {
    sm: 'h-8 w-8',
    md: 'h-10 w-10',
    lg: 'h-12 w-12',
  };

  const getFallback = () => {
    if (fallback) return fallback;
    if (alt) return alt.charAt(0).toUpperCase();
    return <User className="h-4 w-4" />;
  };

  return (
    <Avatar className={sizeClasses[size]}>
      {src && <AvatarImage src={src} alt={alt} />}
      <AvatarFallback>{getFallback()}</AvatarFallback>
    </Avatar>
  );
}
