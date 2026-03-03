import { describe, expect, it } from 'vitest';
import { canAccessFeature } from './permissions';

describe('canAccessFeature', () => {
  it('allows only configured admin subtypes', () => {
    const allowed = canAccessFeature(
      { role: 'admin', admin_type: 'super_admin' },
      { allowedRoles: ['admin'], requiredAdminTypes: ['super_admin', 'admin'] }
    );
    const blocked = canAccessFeature(
      { role: 'admin', admin_type: 'academic_admin' },
      { allowedRoles: ['admin'], requiredAdminTypes: ['super_admin', 'admin'] }
    );

    expect(allowed).toBe(true);
    expect(blocked).toBe(false);
  });

  it('requires matching teacher extension roles when configured', () => {
    const allowed = canAccessFeature(
      { role: 'teacher', extended_roles: ['year_head'] },
      { allowedRoles: ['teacher'], requiredTeacherExtensions: ['year_head', 'class_coordinator'] }
    );
    const blocked = canAccessFeature(
      { role: 'teacher', extended_roles: ['club_coordinator'] },
      { allowedRoles: ['teacher'], requiredTeacherExtensions: ['year_head', 'class_coordinator'] }
    );

    expect(allowed).toBe(true);
    expect(blocked).toBe(false);
  });
});
