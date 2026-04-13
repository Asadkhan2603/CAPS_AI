import { describe, expect, it } from 'vitest';
import { getVisibleNavigationGroups, getWorkspaceHomeItemPath } from './navigationGroups';

function flattenPaths(groups) {
  return groups.flatMap((group) => group.items.map((item) => item.to));
}

function mapGroupsByKey(groups) {
  return Object.fromEntries(groups.map((group) => [group.key, group]));
}

describe('admin navigation visibility', () => {
  it('shows the full admin control cluster for super admins', () => {
    const user = { role: 'admin', admin_type: 'super_admin' };
    const groups = getVisibleNavigationGroups(user);
    const paths = flattenPaths(groups);
    const keys = groups.map((group) => group.key);
    const groupsByKey = mapGroupsByKey(groups);

    expect(paths).toContain('/admin/dashboard');
    expect(paths).toContain('/admin/onboarding');
    expect(paths).toContain('/admin/rbac');
    expect(paths).toContain('/admin/governance');
    expect(paths).toContain('/admin/analytics');
    expect(paths).toContain('/admin/system');
    expect(paths).toContain('/admin/recovery');
    expect(paths).toContain('/admin/developer');
    expect(paths).toContain('/audit-logs');
    expect(paths).toContain('/developer-panel');
    expect(paths).toContain('/students/bulk-import');
    expect(paths).toContain('/sections');
    expect(paths).toContain('/grievances/fallback');
    expect(paths).toContain('/grievances/assigned');
    expect(paths).toContain('/help');
    expect(paths).not.toContain('/dashboard');
    expect(paths).not.toContain('/analytics');
    expect(keys).toEqual(['adminPanel', 'academics', 'communication', 'clubs', 'administration', 'system', 'profile']);
    expect(groupsByKey.adminPanel.label).toBe('Control Center');
    expect(groupsByKey.academics.label).toBe('Students & Academics');
    expect(groupsByKey.administration.label).toBe('Administration');
    expect(groupsByKey.system.label).toBe('System & Compliance');
    expect(keys).not.toContain('operations');
    expect(keys).not.toContain('setup');
    expect(getWorkspaceHomeItemPath(user)).toBe('/workspace/adminPanel/admin/dashboard');
  });

  it('hides developer tools from regular admins while keeping governance surfaces', () => {
    const user = { role: 'admin', admin_type: 'admin' };
    const groups = getVisibleNavigationGroups(user);
    const paths = flattenPaths(groups);
    const keys = groups.map((group) => group.key);

    expect(paths).toContain('/admin/dashboard');
    expect(paths).toContain('/admin/onboarding');
    expect(paths).not.toContain('/admin/rbac');
    expect(paths).toContain('/admin/governance');
    expect(paths).toContain('/admin/analytics');
    expect(paths).toContain('/admin/system');
    expect(paths).toContain('/admin/recovery');
    expect(paths).toContain('/audit-logs');
    expect(paths).toContain('/help');
    expect(paths).not.toContain('/admin/developer');
    expect(paths).not.toContain('/developer-panel');
    expect(keys).toContain('administration');
    expect(keys).toContain('system');
    expect(keys).not.toContain('operations');
    expect(keys).not.toContain('setup');
    expect(getWorkspaceHomeItemPath(user)).toBe('/workspace/adminPanel/admin/dashboard');
  });

  it('limits academic admins to academic admin surfaces and setup workflows', () => {
    const user = { role: 'admin', admin_type: 'academic_admin' };
    const groups = getVisibleNavigationGroups(user);
    const paths = flattenPaths(groups);
    const keys = groups.map((group) => group.key);

    expect(paths).toContain('/admin/dashboard');
    expect(paths).toContain('/admin/onboarding');
    expect(paths).toContain('/admin/analytics');
    expect(paths).toContain('/students/bulk-import');
    expect(paths).toContain('/universities');
    expect(paths).toContain('/faculties');
    expect(paths).toContain('/departments');
    expect(paths).toContain('/programs');
    expect(paths).toContain('/specializations');
    expect(paths).toContain('/batches');
    expect(paths).toContain('/semesters');
    expect(paths).toContain('/sections');
    expect(paths).toContain('/grievances/fallback');
    expect(paths).toContain('/grievances/assigned');
    expect(paths).toContain('/help');
    expect(paths).not.toContain('/admin/governance');
    expect(paths).not.toContain('/admin/system');
    expect(paths).not.toContain('/admin/recovery');
    expect(paths).not.toContain('/admin/developer');
    expect(paths).not.toContain('/audit-logs');
    expect(paths).not.toContain('/developer-panel');
    expect(keys).toContain('academics');
    expect(keys).toContain('administration');
    expect(keys).not.toContain('system');
    expect(getWorkspaceHomeItemPath(user)).toBe('/workspace/adminPanel/admin/dashboard');
  });

  it('limits compliance admins to compliance-facing admin pages', () => {
    const user = { role: 'admin', admin_type: 'compliance_admin' };
    const groups = getVisibleNavigationGroups(user);
    const paths = flattenPaths(groups);
    const keys = groups.map((group) => group.key);

    expect(paths).toContain('/admin/dashboard');
    expect(paths).toContain('/admin/analytics');
    expect(paths).toContain('/admin/system');
    expect(paths).toContain('/audit-logs');
    expect(paths).toContain('/help');
    expect(paths).not.toContain('/admin/onboarding');
    expect(paths).not.toContain('/admin/governance');
    expect(paths).not.toContain('/admin/recovery');
    expect(paths).not.toContain('/admin/developer');
    expect(paths).not.toContain('/students/bulk-import');
    expect(paths).not.toContain('/universities');
    expect(paths).not.toContain('/faculties');
    expect(paths).not.toContain('/developer-panel');
    expect(keys).toContain('system');
    expect(keys).not.toContain('administration');
    expect(getWorkspaceHomeItemPath(user)).toBe('/workspace/adminPanel/admin/dashboard');
  });
});

describe('teacher navigation visibility', () => {
  it('keeps sections in academics and removes the admin setup group for plain teachers', () => {
    const user = { role: 'teacher', extended_roles: [] };
    const groups = getVisibleNavigationGroups(user);
    const keys = groups.map((group) => group.key);
    const academicsGroup = groups.find((group) => group.key === 'academics');
    const academicPaths = flattenPaths([academicsGroup]);

    expect(keys[0]).toBe('overview');
    expect(keys).not.toContain('setup');
    expect(academicPaths).toContain('/sections');
    expect(academicPaths).not.toContain('/students/section-mapping');
    expect(academicPaths).toContain('/grievances/assigned');
    expect(academicPaths).not.toContain('/grievances/coordinator');
    expect(academicPaths).not.toContain('/enrollments');
    expect(flattenPaths(groups)).toContain('/help');
  });

  it('surfaces coordinator-only tools only for class coordinators', () => {
    const user = { role: 'teacher', extended_roles: ['class_coordinator'] };
    const paths = flattenPaths(getVisibleNavigationGroups(user));

    expect(paths).toContain('/sections');
    expect(paths).toContain('/grievances/coordinator');
    expect(paths).toContain('/grievances/assigned');
    expect(paths).toContain('/enrollments');
    expect(paths).not.toContain('/students/bulk-import');
  });

  it('lets year heads manage enrollments without exposing coordinator-only section mapping', () => {
    const user = { role: 'teacher', extended_roles: ['year_head'] };
    const paths = flattenPaths(getVisibleNavigationGroups(user));

    expect(paths).toContain('/sections');
    expect(paths).toContain('/grievances/assigned');
    expect(paths).not.toContain('/grievances/coordinator');
    expect(paths).toContain('/enrollments');
    expect(paths).not.toContain('/students/section-mapping');
  });

  it('shows student grievance tracking in the student profile group', () => {
    const user = { role: 'student' };
    const groups = getVisibleNavigationGroups(user);
    const paths = flattenPaths(groups);
    const academicsGroup = groups.find((group) => group.key === 'academics');

    expect(paths).toContain('/grievances');
    expect(paths).not.toContain('/academic-structure');
    expect(academicsGroup.items.some((item) => item.to === '/attendance-records' && item.label === 'Attendance Logs')).toBe(true);
  });
});
