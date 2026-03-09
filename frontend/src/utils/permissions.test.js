import { describe, expect, it } from 'vitest';
import { canAccessFeature } from './permissions';
import { FEATURE_ACCESS } from '../config/featureAccess';

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

  it('matches backend admin policy for central academic setup modules', () => {
    const superAdmin = { role: 'admin', admin_type: 'super_admin' };
    const academicAdmin = { role: 'admin', admin_type: 'academic_admin' };
    const departmentAdmin = { role: 'admin', admin_type: 'department_admin' };

    expect(canAccessFeature(superAdmin, FEATURE_ACCESS.faculties)).toBe(true);
    expect(canAccessFeature(academicAdmin, FEATURE_ACCESS.departments)).toBe(true);
    expect(canAccessFeature(departmentAdmin, FEATURE_ACCESS.departments)).toBe(false);
    expect(canAccessFeature(departmentAdmin, FEATURE_ACCESS.courses)).toBe(false);
    expect(canAccessFeature(departmentAdmin, FEATURE_ACCESS.years)).toBe(false);
    expect(canAccessFeature(departmentAdmin, FEATURE_ACCESS.branches)).toBe(false);
  });

  it('matches backend admin policy for canonical lower-hierarchy setup modules', () => {
    const departmentAdmin = { role: 'admin', admin_type: 'department_admin' };
    const complianceAdmin = { role: 'admin', admin_type: 'compliance_admin' };

    expect(canAccessFeature(departmentAdmin, FEATURE_ACCESS.programs)).toBe(true);
    expect(canAccessFeature(departmentAdmin, FEATURE_ACCESS.specializations)).toBe(true);
    expect(canAccessFeature(departmentAdmin, FEATURE_ACCESS.batches)).toBe(true);
    expect(canAccessFeature(departmentAdmin, FEATURE_ACCESS.semesters)).toBe(true);
    expect(canAccessFeature(departmentAdmin, FEATURE_ACCESS.sections)).toBe(true);
    expect(canAccessFeature(complianceAdmin, FEATURE_ACCESS.programs)).toBe(false);
  });

  it('keeps teacher read access for sections while restricting admin subtypes correctly', () => {
    const teacher = { role: 'teacher', extended_roles: [] };
    const complianceAdmin = { role: 'admin', admin_type: 'compliance_admin' };

    expect(canAccessFeature(teacher, FEATURE_ACCESS.sections)).toBe(true);
    expect(canAccessFeature(complianceAdmin, FEATURE_ACCESS.sections)).toBe(false);
  });
});
