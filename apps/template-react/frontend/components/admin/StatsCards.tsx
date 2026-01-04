import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface Props {
  stats?: {
    total_users: number;
    users_by_role: Record<string, number>;
  };
}

export function StatsCards({ stats }: Props) {
  if (!stats) return null;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Total Users
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold">{stats.total_users.toLocaleString()}</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Users by Role
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-1">
            {Object.entries(stats.users_by_role).map(([role, count]) => (
              <div key={role} className="flex justify-between">
                <span className="text-muted-foreground">{role}</span>
                <span className="font-medium">{count.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
