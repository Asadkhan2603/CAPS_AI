import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ProtectedRoute from './ProtectedRoute';

const useAuthMock = vi.fn();

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => useAuthMock()
}));

function renderProtectedRoute(options = {}, initialEntry = '/protected') {
  return renderToStaticMarkup(
    <MemoryRouter initialEntries={[initialEntry]}>
      <ProtectedRoute {...options}>
        <div>Secret page</div>
      </ProtectedRoute>
    </MemoryRouter>
  );
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    useAuthMock.mockReset();
  });

  it('renders children for an allowed admin type', () => {
    useAuthMock.mockReturnValue({
      isAuthenticated: true,
      checking: false,
      user: { role: 'admin', admin_type: 'super_admin' }
    });

    const html = renderProtectedRoute(
      { allowedRoles: ['admin'], requiredAdminTypes: ['super_admin'] },
      '/admin/rbac'
    );

    expect(html).toContain('Secret page');
  });

  it('renders children when an admin falls back to the default admin type', () => {
    useAuthMock.mockReturnValue({
      isAuthenticated: true,
      checking: false,
      user: { role: 'admin' }
    });

    const html = renderProtectedRoute(
      { allowedRoles: ['admin'], requiredAdminTypes: ['super_admin', 'admin'] },
      '/users'
    );

    expect(html).toContain('Secret page');
  });

  it('renders children for a teacher with the required extension', () => {
    useAuthMock.mockReturnValue({
      isAuthenticated: true,
      checking: false,
      user: { role: 'teacher', extended_roles: ['class_coordinator'] }
    });

    const html = renderProtectedRoute(
      { allowedRoles: ['teacher'], requiredTeacherExtensions: ['class_coordinator'] },
      '/students/section-mapping'
    );

    expect(html).toContain('Secret page');
  });

  it('renders a visible access denied state when a teacher extension is missing', () => {
    useAuthMock.mockReturnValue({
      isAuthenticated: true,
      checking: false,
      user: { role: 'teacher', extended_roles: [] }
    });

    const html = renderProtectedRoute(
      { allowedRoles: ['teacher'], requiredTeacherExtensions: ['class_coordinator'] },
      '/students/section-mapping'
    );

    expect(html).toContain('You do not have access to this page');
    expect(html).toContain('/students/section-mapping');
    expect(html).toContain('Teacher');
    expect(html).toContain('Teacher Extensions: None');
    expect(html).toContain('Class Coordinator');
  });

  it('renders a visible access denied state instead of redirecting silently for mismatched admin types', () => {
    useAuthMock.mockReturnValue({
      isAuthenticated: true,
      checking: false,
      user: { role: 'admin', admin_type: 'compliance_admin' }
    });

    const html = renderProtectedRoute(
      { allowedRoles: ['admin'], requiredAdminTypes: ['super_admin'] },
      '/admin/rbac'
    );

    expect(html).toContain('You do not have access to this page');
    expect(html).toContain('/admin/rbac');
    expect(html).toContain('Compliance Admin');
    expect(html).toContain('Super Admin');
  });

  it('renders children for a student with the required extension', () => {
    useAuthMock.mockReturnValue({
      isAuthenticated: true,
      checking: false,
      user: { role: 'student', extended_roles: ['class_representative'] }
    });

    const html = renderProtectedRoute(
      { allowedRoles: ['student'], requiredStudentExtensions: ['class_representative'] },
      '/section-representative'
    );

    expect(html).toContain('Secret page');
  });
});
