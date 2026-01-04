'use client';

import * as React from 'react';
import { Eye, EyeOff } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export interface PasswordInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  /** Show password requirements hint below input */
  showRequirements?: boolean;
  /** Custom requirements text */
  requirementsText?: string;
}

/**
 * Password input with show/hide toggle
 *
 * Replaces confirm password pattern - research shows 56% conversion increase
 * when users can see their password instead of typing it twice.
 */
const PasswordInput = React.forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ className, showRequirements, requirementsText, ...props }, ref) => {
    const [showPassword, setShowPassword] = React.useState(false);

    return (
      <div className="space-y-1">
        <div className="relative">
          <Input
            type={showPassword ? 'text' : 'password'}
            className={cn('pr-10', className)}
            ref={ref}
            {...props}
          />
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
            onClick={() => setShowPassword(!showPassword)}
            tabIndex={-1}
          >
            {showPassword ? (
              <EyeOff className="h-4 w-4 text-muted-foreground" />
            ) : (
              <Eye className="h-4 w-4 text-muted-foreground" />
            )}
            <span className="sr-only">
              {showPassword ? 'Hide password' : 'Show password'}
            </span>
          </Button>
        </div>
        {showRequirements && (
          <p className="text-xs text-muted-foreground">
            {requirementsText ?? 'At least 8 characters'}
          </p>
        )}
      </div>
    );
  }
);
PasswordInput.displayName = 'PasswordInput';

export { PasswordInput };
