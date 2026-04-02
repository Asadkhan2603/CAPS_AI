import { test, expect } from '@playwright/test';

const baseUrl = 'http://localhost:5173';
const password = 'VerifyAdmin@123';

const cases = [
  {
    name: 'super_admin',
    email: 'verify.superadmin@capsai.local',
    allowed: ['/admin/dashboard','/admin/governance','/admin/analytics','/admin/system','/admin/recovery','/admin/developer','/audit-logs','/developer-panel'],
    denied: []
  },
  {
    name: 'admin',
    email: 'verify.admin@capsai.local',
    allowed: ['/admin/dashboard','/admin/governance','/admin/analytics','/admin/system','/admin/recovery','/audit-logs'],
    denied: ['/admin/developer','/developer-panel']
  },
  {
    name: 'academic_admin',
    email: 'verify.academic@capsai.local',
    allowed: ['/admin/dashboard','/admin/analytics','/students/bulk-import','/students/section-mapping','/universities','/faculties','/departments','/programs','/specializations','/batches','/semesters','/sections'],
    denied: ['/admin/governance','/admin/system','/admin/recovery','/admin/developer','/audit-logs','/developer-panel']
  },
  {
    name: 'compliance_admin',
    email: 'verify.compliance@capsai.local',
    allowed: ['/admin/dashboard','/admin/analytics','/admin/system','/audit-logs'],
    denied: ['/admin/governance','/admin/recovery','/admin/developer','/students/bulk-import','/universities','/developer-panel']
  }
];

async function login(page, email) {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'domcontentloaded' });
  await page.locator('input[name="email"]').fill(email);
  await page.locator('input[name="password"]').fill(password);
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL(/workspace\/adminPanel\/admin\/dashboard/, { timeout: 20000 });
  await expect(page.getByText('Admin Dashboard')).toBeVisible();
}

function routeRegex(route) {
  return new RegExp(route.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
}

async function go(page, route) {
  await page.goto(`${baseUrl}${route}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(800);
}

async function assertRouteAccessible(page, route) {
  await go(page, route);
  await expect(page).toHaveURL(routeRegex(route));
}

async function assertRouteRedirected(page, route) {
  await go(page, route);
  await expect(page).toHaveURL(/workspace\/adminPanel\/admin\/dashboard/);
  await expect(page.url()).not.toContain(route);
}

for (const entry of cases) {
  test(`admin UI access matrix: ${entry.name}`, async ({ page }) => {
    await login(page, entry.email);

    for (const route of entry.allowed) {
      await assertRouteAccessible(page, route);
    }

    for (const route of entry.denied) {
      await assertRouteRedirected(page, route);
    }
  });
}
