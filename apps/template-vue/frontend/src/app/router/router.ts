import { type RouteRecordRaw, createRouter, createWebHistory } from 'vue-router';
import { usePostHog } from '@core/analytics';
import Profile from '@app/presentation/screens/Profile.vue';
import NotFound from '@app/presentation/screens/NotFound.vue';
import TestGeneration from '@app/presentation/screens/TestGeneration.vue';
import Marketing from '@app/presentation/screens/Marketing.vue';
import Login from '@app/presentation/screens/Login.vue';
import { adminSections } from '@app/admin/sections';

declare module 'vue-router' {
  interface RouteMeta {
    shellVariant?: 'default' | 'wide' | 'narrow' | 'full';
  }
}

export const HOME_ROUTE = '/demo';
const { posthog } = usePostHog();

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'marketing',
    component: Marketing,
  },
  {
    path: '/login',
    name: 'login',
    component: Login,
  },
  {
    path: '/demo',
    name: 'demo',
    component: () => import('@app/presentation/screens/Demo.vue'),
  },
  {
    path: '/profile',
    name: 'profile',
    component: Profile,
  },
  {
    // Admin panel: AdminShell (guard, title, tabs) with one child route per
    // section in `@app/admin/sections` (core sections + app-sections.ts).
    path: '/admin',
    component: () => import('@app/presentation/screens/admin/AdminShell.vue'),
    meta: { shellVariant: 'wide' },
    children: [
      { path: '', name: 'admin', redirect: { name: 'admin-overview' } },
      ...adminSections.map((s) => ({ path: s.path, name: s.name, component: s.loader })),
    ],
  },
  {
    path: '/test-gen',
    name: 'test-gen',
    component: TestGeneration,
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: NotFound,
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

router.afterEach(() => {
  posthog.capture('$pageview');
});

export default router;
