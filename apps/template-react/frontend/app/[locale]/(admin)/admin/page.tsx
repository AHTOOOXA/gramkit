import { redirect } from '@/i18n/navigation';

/**
 * `/admin` opens Overview, like template-vue's `/admin` redirect (by route
 * name, not "the first tab", so reordering the tabs doesn't move it).
 */
export default async function AdminIndexPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  redirect({ href: '/admin/overview', locale });
}
