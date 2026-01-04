import { expect, test } from '@playwright/test';

test.describe('Platform behavior', () => {
  test('should allow web users to access demo and profile pages', async ({
    page,
    context,
  }) => {
    // Step 1: Go to app with mock OFF (web user)
    await context.clearCookies();
    await page.goto('https://local.gramkit.dev/template-react/en');

    // Ensure mock is disabled
    await page.evaluate(() => {
      localStorage.setItem('telegram-platform-mock', 'false');
      localStorage.removeItem('telegram-platform-mock-user');
    });

    // Reload to trigger PlatformDetector with mock OFF
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Debug: check state after reload
    const stateAfterReload = await page.evaluate(() => {
      const cookies = document.cookie;
      const platformCookie = cookies
        .split(';')
        .find((c) => c.trim().startsWith('platform='));

      return {
        mockEnabled: localStorage.getItem('telegram-platform-mock'),
        platformCookie: platformCookie?.split('=')[1],
        hasTelegramObject: typeof window.Telegram?.WebApp !== 'undefined',
      };
    });
    console.log('State after reload:', stateAfterReload);

    // Platform cookie should be 'web' when mock is OFF
    expect(stateAfterReload.platformCookie).toBe('web');

    // Step 2: Navigate to demo page - should work for web users
    await page.goto('https://local.gramkit.dev/template-react/en/demo');
    await page.waitForLoadState('networkidle');

    // Should stay on demo page (no redirect)
    expect(page.url()).toContain('/demo');

    // Step 3: Navigate to profile page - should work for web users
    await page.goto('https://local.gramkit.dev/template-react/en/profile');
    await page.waitForLoadState('networkidle');

    // Should stay on profile page (no redirect)
    expect(page.url()).toContain('/profile');
  });

  test('should work when mock is ON (Telegram user)', async ({
    page,
    context,
  }) => {
    // Clear and enable mock
    await context.clearCookies();
    await page.goto('https://local.gramkit.dev/template-react/en');

    await page.evaluate(() => {
      localStorage.setItem('telegram-platform-mock', 'true');
    });

    // Reload to trigger PlatformDetector with mock ON
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Debug: check state
    const state = await page.evaluate(() => {
      const cookies = document.cookie;
      const platformCookie = cookies
        .split(';')
        .find((c) => c.trim().startsWith('platform='));
      return {
        mockEnabled: localStorage.getItem('telegram-platform-mock'),
        platformCookie: platformCookie?.split('=')[1],
      };
    });
    console.log('State with mock ON:', state);

    // Platform cookie should be 'telegram' when mock is ON
    expect(state.platformCookie).toBe('telegram');

    // Navigate to demo - should work
    await page.goto('https://local.gramkit.dev/template-react/en/demo');
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/demo');

    // Navigate to profile - should work
    await page.goto('https://local.gramkit.dev/template-react/en/profile');
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/profile');
  });
});
