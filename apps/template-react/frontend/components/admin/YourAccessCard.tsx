import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Check, X } from 'lucide-react';

interface Props {
  permissions?: {
    role: string;
    is_owner_in_config: boolean;
    permissions: string[];
  };
}

const ALL_PERMISSIONS = [
  'view_admin_panel',
  'view_stats',
  'view_aggregate_data',
  'change_roles',
  'protected_actions',
];

export function YourAccessCard({ permissions }: Props) {
  if (!permissions) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your Access</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-4">
          <div>
            <div className="text-sm text-muted-foreground">Role</div>
            <div className="text-lg font-semibold">{permissions.role}</div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Config Owner</div>
            <div className="text-lg font-semibold">
              {permissions.is_owner_in_config ? 'Yes' : 'No'}
            </div>
          </div>
        </div>

        <div>
          <div className="text-sm text-muted-foreground mb-2">Permissions</div>
          <div className="space-y-1">
            {ALL_PERMISSIONS.map((perm) => {
              const has = permissions.permissions.includes(perm);
              return (
                <div key={perm} className="flex items-center gap-2 text-sm">
                  {has ? (
                    <Check className="h-4 w-4 text-green-500" />
                  ) : (
                    <X className="h-4 w-4 text-red-500" />
                  )}
                  <span className={has ? '' : 'text-muted-foreground'}>{perm}</span>
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
