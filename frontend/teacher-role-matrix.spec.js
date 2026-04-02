import { test, expect } from '@playwright/test';

const baseUrl = 'http://localhost:5173';
const password = 'VerifyTeacher@123';

test.setTimeout(120000);

const cases = [
  {
    name: 'teacher',
    email: 'verify.teacher@capsai.local',
    allowed: [
      '/dashboard',
      '/analytics',
      '/history',
      '/timetable',
      '/academic-structure',
      '/students',
      '/sections',
      '/groups',
      '/subjects',
      '/course-offerings',
      '/class-slots',
      '/attendance-records',
      '/assignments',
      '/submissions',
      '/ai-operations',
      '/review-tickets',
      '/evaluations',
      '/communication/feed',
      '/communication/announcements',
      '/clubs',
      '/club-events',
      '/event-registrations',
      '/audit-logs'
    ],
    denied: [
      '/students/bulk-import',
      '/students/section-mapping',
      '/enrollments',
      '/users',
      '/developer-panel',
      '/universities',
      '/faculties',
      '/departments',
      '/programs',
      '/specializations',
      '/batches',
      '/semesters',
      '/admin/dashboard'
    ]
  },
  {
    name: 'class_coordinator',
    email: 'verify.coordinator@capsai.local',
    allowed: [
      '/dashboard',
      '/analytics',
      '/students/section-mapping',
      '/enrollments',
      '/students',
      '/sections',
      '/attendance-records',
      '/course-offerings',
      '/class-slots',
      '/audit-logs'
    ],
    denied: ['/students/bulk-import', '/users', '/developer-panel', '/universities', '/admin/dashboard']
  },
  {
    name: 'year_head',
    email: 'verify.yearhead@capsai.local',
    allowed: ['/dashboard', '/analytics', '/students', '/enrollments', '/audit-logs'],
    denied: ['/students/bulk-import', '/students/section-mapping', '/users', '/developer-panel', '/universities', '/admin/dashboard']
  },
  {
    name: 'club_coordinator',
    email: 'verify.club@capsai.local',
    allowed: ['/dashboard', '/analytics', '/clubs', '/club-events', '/event-registrations', '/audit-logs'],
    denied: ['/students/bulk-import', '/students/section-mapping', '/enrollments', '/users', '/developer-panel', '/universities', '/admin/dashboard']
  }
];

async function login(page, email) {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'domcontentloaded' });
  await page.locator('input[name="email"]').fill(email);
  await page.locator('input[name="password"]').fill(password);
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL(/workspace\/overview\/dashboard/, { timeout: 20000 });
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
  await expect(page).toHaveURL(/workspace\/overview\/dashboard/);
  await expect(page.url()).not.toContain(route);
}

for (const entry of cases) {
  test(`teacher UI access matrix: ${entry.name}`, async ({ page }) => {
    await login(page, entry.email);

    for (const route of entry.allowed) {
      await assertRouteAccessible(page, route);
    }

    for (const route of entry.denied) {
      await assertRouteRedirected(page, route);
    }
  });
}
