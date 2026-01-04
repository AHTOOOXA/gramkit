'use client';

import { useRouter } from 'next/navigation';
import { useAppInit } from '@/providers/AppInitProvider';
import { useGetMyPermissionsAdminMeGet } from '@/src/gen/hooks/useGetMyPermissionsAdminMeGet';
import { useGetStatsAdminStatsGet } from '@/src/gen/hooks/useGetStatsAdminStatsGet';
import { YourAccessCard } from '@/components/admin/YourAccessCard';
import { StatsCards } from '@/components/admin/StatsCards';
import { ProtectedActionDemo } from '@/components/admin/ProtectedActionDemo';

export default function AdminPage() {
  const { user, isLoading } = useAppInit();
  const router = useRouter();

  const { data: permissions } = useGetMyPermissionsAdminMeGet();
  const { data: stats } = useGetStatsAdminStatsGet();

  // Redirect non-admins
  if (!isLoading && user && !['admin', 'owner'].includes(user.role ?? '')) {
    router.replace('/');
    return null;
  }

  if (isLoading) return <div className="p-6 animate-pulse">Loading...</div>;

  return (
    <div className="container py-6 space-y-6 max-w-4xl mx-auto">
      {/* Header - Hero moment */}
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold mb-2 motion-blur-in-[10px] motion-scale-in-[0.95] motion-opacity-in-[0%] motion-duration-[0.7s] motion-duration-[1s]/blur motion-ease-spring-smooth">
          RBAC Demo
        </h1>
        <p className="text-muted-foreground motion-blur-in-[5px] motion-opacity-in-[0%] motion-translate-y-in-[10px] motion-duration-[0.5s] motion-delay-[0.25s] motion-ease-spring-smooth">
          This page demonstrates role-based access control
        </p>
      </div>

      {/* Your role and permissions */}
      <div className="motion-opacity-in-[0%] motion-translate-y-in-[30px] motion-blur-in-[4px] motion-duration-[0.5s] motion-delay-[0.35s] motion-ease-spring-smooth">
        <YourAccessCard permissions={permissions} />
      </div>

      {/* Safe aggregate stats */}
      <div className="motion-opacity-in-[0%] motion-translate-y-in-[30px] motion-blur-in-[4px] motion-duration-[0.5s] motion-delay-[0.5s] motion-ease-spring-smooth">
        <StatsCards stats={stats} />
      </div>

      {/* Try protected action */}
      <div className="motion-opacity-in-[0%] motion-translate-y-in-[30px] motion-blur-in-[4px] motion-duration-[0.5s] motion-delay-[0.65s] motion-ease-spring-smooth">
        <ProtectedActionDemo canExecute={permissions?.permissions.includes('protected_actions') ?? false} />
      </div>
    </div>
  );
}
