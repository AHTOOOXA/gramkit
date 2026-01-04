'use client';

import { useState } from 'react';
import { Shield, Check, X, Loader2 } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  useGetRbacMeDemoRbacMeGet,
  useSetDemoRoleDemoRbacSetRolePost,
  useDemoProtectedActionDemoRbacProtectedActionPost,
} from '@/src/gen/hooks';

const roles = ['user', 'admin', 'owner'] as const;

const roleColors: Record<string, 'secondary' | 'default' | 'destructive'> = {
  user: 'secondary',
  admin: 'default',
  owner: 'destructive',
};

export function RbacDemo() {
  const queryClient = useQueryClient();
  const [actionResult, setActionResult] = useState<{ success: boolean; message: string } | null>(null);

  const { data: rbacMe, isLoading } = useGetRbacMeDemoRbacMeGet();
  const setRoleMutation = useSetDemoRoleDemoRbacSetRolePost();
  const protectedActionMutation = useDemoProtectedActionDemoRbacProtectedActionPost();

  const currentRole = rbacMe?.role ?? 'user';

  async function setRole(role: string) {
    setActionResult(null);
    await setRoleMutation.mutateAsync({ data: { role } });
    // Invalidate queries to refresh user data
    void queryClient.invalidateQueries({ queryKey: [{ url: '/demo/rbac/me' }] });
    void queryClient.invalidateQueries({ queryKey: [{ url: '/users/me' }] });
  }

  async function tryProtectedAction() {
    setActionResult(null);
    try {
      const result = await protectedActionMutation.mutateAsync();
      setActionResult({ success: true, message: result.message });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setActionResult({
        success: false,
        message: err.response?.data?.detail ?? 'Action failed',
      });
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-primary" />
          <CardTitle>RBAC Demo</CardTitle>
        </div>
        <CardDescription>
          Test role-based access control. Switch roles and try protected actions.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Loading state */}
        {isLoading && (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {!isLoading && rbacMe && (
          <>
            {/* Current Role */}
            <div>
              <div className="text-sm text-muted-foreground mb-2">Current Role</div>
              <Badge variant={roleColors[currentRole] ?? 'secondary'} className="text-sm">
                {currentRole}
              </Badge>
            </div>

            {/* Role Switcher */}
            <div>
              <div className="text-sm text-muted-foreground mb-2">Switch Role (Demo)</div>
              <div className="flex gap-2">
                {roles.map((role) => (
                  <Button
                    key={role}
                    variant={currentRole === role ? 'default' : 'outline'}
                    size="sm"
                    disabled={setRoleMutation.isPending}
                    onClick={() => setRole(role)}
                  >
                    {role}
                  </Button>
                ))}
              </div>
            </div>

            {/* Permissions */}
            <div>
              <div className="text-sm text-muted-foreground mb-2">Your Permissions</div>
              <div className="flex flex-wrap gap-1">
                {rbacMe.permissions.map((perm) => (
                  <Badge key={perm} variant="outline" className="text-xs">
                    {perm}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Protected Action */}
            <div className="pt-2 border-t">
              <div className="text-sm text-muted-foreground mb-2">Test Protected Action</div>
              <Button
                variant="destructive"
                size="sm"
                disabled={protectedActionMutation.isPending}
                onClick={tryProtectedAction}
              >
                {protectedActionMutation.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                )}
                Try Owner-Only Action
              </Button>

              {/* Result */}
              {actionResult && (
                <div className="mt-2 flex items-center gap-2 text-sm">
                  {actionResult.success ? (
                    <Check className="h-4 w-4 text-green-500" />
                  ) : (
                    <X className="h-4 w-4 text-red-500" />
                  )}
                  <span className={actionResult.success ? 'text-green-600' : 'text-red-600'}>
                    {actionResult.message}
                  </span>
                </div>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
