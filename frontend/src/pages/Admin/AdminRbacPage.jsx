import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Card from '../../components/ui/Card';
import Table from '../../components/ui/Table';
import Modal from '../../components/ui/Modal';
import FormInput from '../../components/ui/FormInput';
import EmptyState from '../../components/ui/EmptyState';
import AdminDomainNav from '../../components/admin/AdminDomainNav';
import { useToast } from '../../hooks/useToast';
import { apiClient } from '../../services/apiClient';
import {
  createAdminUser,
  createRbacRole,
  deleteAdminUser,
  deleteRbacRole,
  fetchAdminUser,
  fetchAdminUsers,
  fetchRbacDesign,
  fetchRbacPermissions,
  fetchRbacRoles,
  updateAdminUser,
  updateAdminUserStatus,
  updateRbacRole,
} from '../../services/adminRbacApi';
import { formatApiError } from '../../utils/apiError';

const emptyAdmin = () => ({
  id: '',
  full_name: '',
  email: '',
  password: '',
  role_code: '',
  is_active: true,
  allow_permission_keys: [],
  deny_permission_keys: [],
  scopes: [],
});

const emptyRole = () => ({
  id: '',
  code: '',
  name: '',
  description: '',
  permission_keys: [],
  is_active: true,
  is_system: false,
});

const cleanScopes = (scopes = []) =>
  scopes
    .map((scope) => ({
      department_id: String(scope?.department_id || '').trim(),
      year_id: String(scope?.year_id || '').trim(),
    }))
    .filter((scope) => scope.department_id || scope.year_id);

export default function AdminRbacPage() {
  const { pushToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [design, setDesign] = useState({ roles: [], permission_groups: [], scope_fields: [] });
  const [permissions, setPermissions] = useState([]);
  const [roles, setRoles] = useState([]);
  const [admins, setAdmins] = useState([]);
  const [auditRows, setAuditRows] = useState([]);
  const [adminQuery, setAdminQuery] = useState('');
  const [adminStatus, setAdminStatus] = useState('');
  const [adminRole, setAdminRole] = useState('');
  const [roleQuery, setRoleQuery] = useState('');
  const [adminModalOpen, setAdminModalOpen] = useState(false);
  const [roleModalOpen, setRoleModalOpen] = useState(false);
  const [savingAdmin, setSavingAdmin] = useState(false);
  const [savingRole, setSavingRole] = useState(false);
  const [adminForm, setAdminForm] = useState(emptyAdmin());
  const [roleForm, setRoleForm] = useState(emptyRole());

  const permissionGroups = useMemo(() => {
    const groups = new Map();
    permissions.forEach((permission) => {
      const key = permission.module_key || 'other';
      if (!groups.has(key)) {
        groups.set(key, { key, label: permission.module || key, permissions: [] });
      }
      groups.get(key).permissions.push(permission);
    });
    return Array.from(groups.values());
  }, [permissions]);

  const availableRoles = useMemo(() => {
    if (roles.length) {
      return roles;
    }
    return (design.roles || []).map((role) => ({
      id: role.code,
      code: role.code,
      name: role.name,
      is_active: true,
      is_system: true,
    }));
  }, [design.roles, roles]);

  const roleOptions = useMemo(
    () => availableRoles
      .filter((role) => role.is_active !== false)
      .map((role) => ({ value: role.code, label: `${role.name} (${role.code})` })),
    [availableRoles]
  );

  const summary = useMemo(() => [
    { label: 'Admins', value: admins.length },
    { label: 'Active Admins', value: admins.filter((admin) => admin.status === 'active').length },
    { label: 'Roles', value: roles.length },
    { label: 'Custom Roles', value: roles.filter((role) => !role.is_system && !role.deleted_at).length },
    { label: 'Permissions', value: permissions.length },
    { label: 'Audit Events', value: auditRows.length },
  ], [admins, roles, permissions, auditRows]);

  const filteredAdmins = useMemo(() => {
    const query = adminQuery.trim().toLowerCase();
    return admins.filter((admin) => {
      if (adminStatus && admin.status !== adminStatus) return false;
      if (adminRole && admin.admin_role?.code !== adminRole) return false;
      if (!query) return true;
      return [admin.full_name, admin.email, admin.admin_role?.code, admin.admin_role?.name]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
        .includes(query);
    });
  }, [admins, adminQuery, adminStatus, adminRole]);

  const filteredRoles = useMemo(() => {
    const query = roleQuery.trim().toLowerCase();
    return roles.filter((role) => !query || [role.code, role.name, role.description].filter(Boolean).join(' ').toLowerCase().includes(query));
  }, [roles, roleQuery]);

  useEffect(() => {
    void loadData(false);
  }, []);

  async function loadData(silent) {
    if (silent) setRefreshing(true);
    else {
      setLoading(true);
      setError('');
    }
    try {
      const [designResult, permissionResult, roleResult, adminResult, auditResult] = await Promise.allSettled([
        fetchRbacDesign(),
        fetchRbacPermissions(),
        fetchRbacRoles(),
        fetchAdminUsers({ includeDeleted: true }),
        apiClient.get('/audit-logs/', { params: { limit: 40 } }),
      ]);

      const failures = [];

      if (designResult.status === 'fulfilled') {
        setDesign(designResult.value || { roles: [], permission_groups: [], scope_fields: [] });
      } else {
        setDesign({ roles: [], permission_groups: [], scope_fields: [] });
        failures.push(`design: ${formatApiError(designResult.reason, 'Failed to load RBAC design')}`);
      }

      if (permissionResult.status === 'fulfilled') {
        setPermissions(permissionResult.value || []);
      } else {
        setPermissions([]);
        failures.push(`permissions: ${formatApiError(permissionResult.reason, 'Failed to load permissions')}`);
      }

      if (roleResult.status === 'fulfilled') {
        setRoles(roleResult.value || []);
      } else {
        setRoles([]);
        failures.push(`roles: ${formatApiError(roleResult.reason, 'Failed to load roles')}`);
      }

      if (adminResult.status === 'fulfilled') {
        setAdmins(adminResult.value || []);
      } else {
        setAdmins([]);
        failures.push(`admins: ${formatApiError(adminResult.reason, 'Failed to load admins')}`);
      }

      if (auditResult.status === 'fulfilled') {
        const logs = Array.isArray(auditResult.value?.data) ? auditResult.value.data : [];
        setAuditRows(
          logs.filter(
            (row) =>
              row?.entity_type === 'admin_user' ||
              row?.entity_type === 'rbac_role' ||
              String(row?.action_type || '').startsWith('rbac_')
          )
        );
      } else {
        setAuditRows([]);
        failures.push(`audit: ${formatApiError(auditResult.reason, 'Failed to load audit logs')}`);
      }

      if (failures.length) {
        const message = `Some RBAC data could not be loaded: ${failures.join(' | ')}`;
        setError(message);
      } else {
        setError('');
      }
    } catch (err) {
      const message = formatApiError(err, 'Failed to load RBAC control panel');
      setError(message);
      pushToast({ type: 'error', message });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  async function refreshWithToast(message) {
    await loadData(true);
    pushToast({ type: 'success', message });
  }

  function updateAdminField(field, value) {
    setAdminForm((prev) => ({ ...prev, [field]: value }));
  }

  function updateRoleField(field, value) {
    setRoleForm((prev) => ({ ...prev, [field]: value }));
  }

  function openCreateAdmin() {
    setAdminForm({ ...emptyAdmin(), role_code: roleOptions[0]?.value || '' });
    setAdminModalOpen(true);
  }

  async function openEditAdmin(id) {
    try {
      const admin = await fetchAdminUser(id);
      setAdminForm({
        id: admin.id,
        full_name: admin.full_name || '',
        email: admin.email || '',
        password: '',
        role_code: admin.admin_role?.code || admin.rbac_role_code || '',
        is_active: admin.is_active !== false,
        allow_permission_keys: admin.permission_overrides?.allow_permission_keys || [],
        deny_permission_keys: admin.permission_overrides?.deny_permission_keys || [],
        scopes: cleanScopes(admin.scopes),
      });
      setAdminModalOpen(true);
    } catch (err) {
      pushToast({ type: 'error', message: formatApiError(err, 'Failed to load admin details') });
    }
  }

  function openCreateRole() {
    setRoleForm(emptyRole());
    setRoleModalOpen(true);
  }

  function openEditRole(role) {
    setRoleForm({
      id: role.id,
      code: role.code || '',
      name: role.name || '',
      description: role.description || '',
      permission_keys: role.permission_keys || [],
      is_active: role.is_active !== false,
      is_system: Boolean(role.is_system),
    });
    setRoleModalOpen(true);
  }

  function closeAdminModal() {
    setAdminModalOpen(false);
    setAdminForm(emptyAdmin());
  }

  function closeRoleModal() {
    setRoleModalOpen(false);
    setRoleForm(emptyRole());
  }

  function addScopeRow() {
    setAdminForm((prev) => ({ ...prev, scopes: [...prev.scopes, { department_id: '', year_id: '' }] }));
  }

  function updateScopeRow(index, field, value) {
    setAdminForm((prev) => ({
      ...prev,
      scopes: prev.scopes.map((scope, idx) => (idx === index ? { ...scope, [field]: value } : scope)),
    }));
  }

  function removeScopeRow(index) {
    setAdminForm((prev) => ({ ...prev, scopes: prev.scopes.filter((_, idx) => idx !== index) }));
  }

  function toggleAdminPermission(target, permissionKey, checked) {
    setAdminForm((prev) => {
      const allow = new Set(prev.allow_permission_keys);
      const deny = new Set(prev.deny_permission_keys);
      if (target === 'allow') {
        if (checked) {
          allow.add(permissionKey);
          deny.delete(permissionKey);
        } else allow.delete(permissionKey);
      } else if (checked) {
        deny.add(permissionKey);
        allow.delete(permissionKey);
      } else deny.delete(permissionKey);
      return {
        ...prev,
        allow_permission_keys: Array.from(allow).sort(),
        deny_permission_keys: Array.from(deny).sort(),
      };
    });
  }

  function toggleRolePermission(permissionKey, checked) {
    setRoleForm((prev) => {
      const keys = new Set(prev.permission_keys);
      if (checked) keys.add(permissionKey);
      else keys.delete(permissionKey);
      return { ...prev, permission_keys: Array.from(keys).sort() };
    });
  }

  async function submitAdmin(event) {
    event.preventDefault();
    setSavingAdmin(true);
    try {
      const payload = {
        full_name: adminForm.full_name.trim(),
        role_code: adminForm.role_code,
        is_active: Boolean(adminForm.is_active),
        allow_permission_keys: adminForm.allow_permission_keys,
        deny_permission_keys: adminForm.deny_permission_keys,
        scopes: cleanScopes(adminForm.scopes),
      };
      if (adminForm.id) {
        await updateAdminUser(adminForm.id, payload);
        await refreshWithToast('Admin account updated.');
      } else {
        await createAdminUser({
          ...payload,
          email: adminForm.email.trim(),
          password: adminForm.password,
        });
        await refreshWithToast('Admin account created.');
      }
      closeAdminModal();
    } catch (err) {
      pushToast({ type: 'error', message: formatApiError(err, 'Failed to save admin account') });
    } finally {
      setSavingAdmin(false);
    }
  }

  async function submitRole(event) {
    event.preventDefault();
    setSavingRole(true);
    try {
      const payload = {
        code: roleForm.code.trim().toUpperCase(),
        name: roleForm.name.trim(),
        description: roleForm.description.trim() || null,
        permission_keys: roleForm.permission_keys,
        is_active: Boolean(roleForm.is_active),
      };
      if (roleForm.id) {
        await updateRbacRole(roleForm.id, {
          name: payload.name,
          description: payload.description,
          permission_keys: payload.permission_keys,
          is_active: payload.is_active,
        });
        await refreshWithToast('Role updated.');
      } else {
        await createRbacRole(payload);
        await refreshWithToast('Role created.');
      }
      closeRoleModal();
    } catch (err) {
      pushToast({ type: 'error', message: formatApiError(err, 'Failed to save role') });
    } finally {
      setSavingRole(false);
    }
  }

  async function toggleAdminStatus(admin) {
    try {
      await updateAdminUserStatus(admin.id, { is_active: !admin.is_active });
      await refreshWithToast(!admin.is_active ? 'Admin activated.' : 'Admin deactivated.');
    } catch (err) {
      pushToast({ type: 'error', message: formatApiError(err, 'Failed to update admin status') });
    }
  }

  async function removeAdmin(admin) {
    if (!window.confirm(`Soft delete admin ${admin.email}?`)) return;
    try {
      await deleteAdminUser(admin.id);
      await refreshWithToast('Admin soft deleted.');
    } catch (err) {
      pushToast({ type: 'error', message: formatApiError(err, 'Failed to delete admin') });
    }
  }

  async function removeRole(role) {
    if (role.is_system) {
      pushToast({ type: 'error', message: 'System roles cannot be deleted.' });
      return;
    }
    if (!window.confirm(`Delete role ${role.code}?`)) return;
    try {
      await deleteRbacRole(role.id);
      await refreshWithToast('Role deleted.');
    } catch (err) {
      pushToast({ type: 'error', message: formatApiError(err, 'Failed to delete role') });
    }
  }

  const adminColumns = [
    { key: 'full_name', label: 'Admin' },
    { key: 'email', label: 'Email' },
    {
      key: 'admin_details',
      label: 'Admin Details',
      render: (row) => <AdminDetailsCell row={row} />,
    },
    {
      key: 'admin_role',
      label: 'Role',
      render: (row) => (
        <div>
          <div className="font-medium text-slate-900 dark:text-white">{row.admin_role?.name || row.rbac_role_code || '-'}</div>
          <div className="text-xs text-slate-500">{row.admin_role?.code || row.admin_type || '-'}</div>
        </div>
      ),
    },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
    { key: 'scopes', label: 'Scopes', render: (row) => <ScopeSummary scopes={row.scopes} /> },
    { key: 'permissions', label: 'Permissions', render: (row) => `${row.permissions?.length || 0}` },
    {
      key: 'overrides',
      label: 'Overrides',
      render: (row) => `${row.permission_overrides?.allow_permission_keys?.length || 0} allow / ${row.permission_overrides?.deny_permission_keys?.length || 0} deny`,
    },
  ];

  const roleColumns = [
    { key: 'name', label: 'Role Name' },
    { key: 'code', label: 'Code' },
    { key: 'permission_groups', label: 'Groups', render: (row) => (row.permission_groups?.length ? row.permission_groups.join(', ') : '-') },
    { key: 'permission_count', label: 'Permissions', render: (row) => `${row.permission_keys?.length || 0}` },
    { key: 'type', label: 'Type', render: (row) => <span className="text-xs font-medium uppercase tracking-wide text-slate-500">{row.is_system ? 'System' : 'Custom'}</span> },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.deleted_at ? 'deleted' : row.is_active === false ? 'inactive' : 'active'} /> },
  ];

  const auditColumns = [
    { key: 'action', label: 'Action' },
    { key: 'entity_type', label: 'Entity' },
    { key: 'detail', label: 'Detail' },
    { key: 'actor_user_id', label: 'Actor' },
    { key: 'created_at', label: 'Created', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') },
  ];

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-3">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold">RBAC &amp; Role Control</h1>
            <p className="text-sm text-slate-500">
              Super Admin workspace for admin accounts, dynamic roles, permission overrides, scoped access, and RBAC audit visibility.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-secondary" onClick={() => void loadData(true)}>
              {refreshing ? 'Refreshing...' : 'Refresh'}
            </button>
            <button type="button" className="btn-primary" onClick={openCreateAdmin}>
              Create Admin
            </button>
            <button type="button" className="btn-secondary" onClick={openCreateRole}>
              Create Role
            </button>
          </div>
        </div>
      </Card>

      <AdminDomainNav />

      {error ? <Card><p className="text-sm text-rose-600">{error}</p></Card> : null}

      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        {summary.map((item) => <Metric key={item.label} label={item.label} value={loading ? '...' : item.value} />)}
      </div>

      <Card className="space-y-3">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Access Design Snapshot</h2>
            <p className="text-sm text-slate-500">Canonical system roles, permission groups, and scope fields seeded from the backend RBAC catalog.</p>
          </div>
          <div className="text-xs text-slate-500">Scope fields: {(design.scope_fields || []).join(', ') || '-'}</div>
        </div>
        <div className="grid gap-3 xl:grid-cols-3">
          {(design.roles || []).map((role) => (
            <div key={role.code} className="rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold">{role.name}</p>
                  <p className="text-xs uppercase tracking-wide text-slate-500">{role.code}</p>
                </div>
                <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {role.permissions?.length || 0} perms
                </span>
              </div>
              <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">{role.description}</p>
              <div className="mt-3 text-xs text-slate-500">Scope required: {role.scope_required ? 'Yes' : 'No'}</div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="space-y-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Admin Management</h2>
            <p className="text-sm text-slate-500">Search admins, assign roles, apply permission overrides, and activate, deactivate, or soft delete accounts.</p>
          </div>
          <button type="button" className="btn-primary" onClick={openCreateAdmin}>New Admin</button>
        </div>
        <div className="grid gap-3 md:grid-cols-4">
          <FormInput label="Search" value={adminQuery} placeholder="Name, email, role" onChange={(event) => setAdminQuery(event.target.value)} />
          <FormInput as="select" label="Status" value={adminStatus} onChange={(event) => setAdminStatus(event.target.value)}>
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="deleted">Deleted</option>
          </FormInput>
          <FormInput as="select" label="Role" value={adminRole} onChange={(event) => setAdminRole(event.target.value)}>
            <option value="">All roles</option>
            {availableRoles.map((role) => <option key={role.id || role.code} value={role.code}>{role.name} ({role.code})</option>)}
          </FormInput>
          <div className="flex items-end">
            <button type="button" className="btn-secondary w-full" onClick={() => { setAdminQuery(''); setAdminStatus(''); setAdminRole(''); }}>
              Reset Filters
            </button>
          </div>
        </div>
        {filteredAdmins.length ? (
          <Table
            columns={adminColumns}
            data={filteredAdmins}
            rowActions={[
              { key: 'edit', label: 'Edit', onClick: (row) => openEditAdmin(row.id) },
              { key: 'status', label: 'Toggle Status', onClick: (row) => toggleAdminStatus(row) },
              { key: 'delete', label: 'Soft Delete', className: 'text-rose-700 dark:text-rose-300', onClick: (row) => removeAdmin(row) },
            ]}
          />
        ) : (
          <EmptyState title="No admins found" description="Create the first scoped admin or widen the current filters." />
        )}
      </Card>

      <Card className="space-y-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Role Management</h2>
            <p className="text-sm text-slate-500">Create new roles, tune permission bundles, and keep system roles separate from custom ones.</p>
          </div>
          <button type="button" className="btn-primary" onClick={openCreateRole}>New Role</button>
        </div>
        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_220px]">
          <FormInput label="Search Roles" value={roleQuery} placeholder="Code, name, description" onChange={(event) => setRoleQuery(event.target.value)} />
          <div className="flex items-end">
            <button type="button" className="btn-secondary w-full" onClick={() => setRoleQuery('')}>Clear Search</button>
          </div>
        </div>
        {filteredRoles.length ? (
          <Table
            columns={roleColumns}
            data={filteredRoles}
            rowActions={[
              { key: 'edit', label: 'Edit', onClick: (row) => openEditRole(row) },
              { key: 'delete', label: 'Delete', className: 'text-rose-700 dark:text-rose-300', onClick: (row) => removeRole(row) },
            ]}
          />
        ) : (
          <EmptyState title="No roles found" description="Create a custom role or clear the current search query." />
        )}
      </Card>

      <Card className="space-y-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Audit Logs</h2>
            <p className="text-sm text-slate-500">Recent RBAC mutations and admin lifecycle changes before drilling into the full compliance explorer.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link className="btn-secondary" to="/audit-logs">Open Audit Logs</Link>
            <Link className="btn-secondary" to="/admin/governance">Open Governance</Link>
          </div>
        </div>
        {auditRows.length ? <Table columns={auditColumns} data={auditRows.slice(0, 12)} /> : <EmptyState title="No RBAC audit events yet" description="RBAC and admin management actions will appear here after the first mutation." />}
      </Card>

      <AdminModal
        open={adminModalOpen}
        form={adminForm}
        roleOptions={roleOptions}
        groups={permissionGroups}
        saving={savingAdmin}
        onClose={closeAdminModal}
        onSubmit={submitAdmin}
        onField={updateAdminField}
        onAddScope={addScopeRow}
        onScope={updateScopeRow}
        onRemoveScope={removeScopeRow}
        onPermission={toggleAdminPermission}
      />

      <RoleModal
        open={roleModalOpen}
        form={roleForm}
        groups={permissionGroups}
        saving={savingRole}
        onClose={closeRoleModal}
        onSubmit={submitRole}
        onField={updateRoleField}
        onPermission={toggleRolePermission}
      />
    </div>
  );
}

function AdminModal({ open, form, roleOptions, groups, saving, onClose, onSubmit, onField, onAddScope, onScope, onRemoveScope, onPermission }) {
  return (
    <Modal open={open} title={form.id ? 'Edit Admin Account' : 'Create Admin Account'} onClose={onClose} size="large">
      <form className="space-y-5" onSubmit={onSubmit}>
        <div className="grid gap-3 md:grid-cols-2">
          <FormInput label="Full Name" value={form.full_name} required onChange={(event) => onField('full_name', event.target.value)} />
          <FormInput as="select" label="Role" value={form.role_code} required onChange={(event) => onField('role_code', event.target.value)}>
            <option value="">Select role</option>
            {roleOptions.map((role) => <option key={role.value} value={role.value}>{role.label}</option>)}
          </FormInput>
          <FormInput label="Email" type="email" value={form.email} required={!form.id} disabled={Boolean(form.id)} onChange={(event) => onField('email', event.target.value)} />
          <FormInput label="Password" type="password" value={form.password} required={!form.id} disabled={Boolean(form.id)} placeholder={form.id ? 'Managed during creation' : 'Minimum 8 characters'} onChange={(event) => onField('password', event.target.value)} />
          <FormInput as="select" label="Status" value={form.is_active ? 'active' : 'inactive'} onChange={(event) => onField('is_active', event.target.value === 'active')}>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </FormInput>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold">Scope Assignments</h3>
              <p className="text-xs text-slate-500">Assign `department_id` and `year_id` rows for scoped roles like HOD and Year Admin. Use `year_id` as the batch start year or cohort, for example `2027`.</p>
            </div>
            <button type="button" className="btn-secondary" onClick={onAddScope}>Add Scope</button>
          </div>
          {form.scopes.length ? (
            <div className="space-y-3">
              {form.scopes.map((scope, index) => (
                <div key={`${scope.department_id}-${scope.year_id}-${index}`} className="grid gap-3 rounded-2xl border border-slate-200 p-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_140px] dark:border-slate-700">
                  <FormInput label="Department ID" value={scope.department_id} placeholder="dep-cse" onChange={(event) => onScope(index, 'department_id', event.target.value)} />
                  <FormInput label="Year ID" value={scope.year_id} placeholder="2027 cohort" onChange={(event) => onScope(index, 'year_id', event.target.value)} />
                  <div className="flex items-end">
                    <button type="button" className="btn-secondary w-full text-rose-700 dark:text-rose-300" onClick={() => onRemoveScope(index)}>Remove</button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No scope rows yet" description="Leave empty for unrestricted roles like Super Admin, Academic Admin, or Compliance Admin." />
          )}
        </div>

        <PermissionEditor
          title="Allow Overrides"
          description="Grant extra permissions beyond the role baseline."
          groups={groups}
          selectedKeys={form.allow_permission_keys}
          opposingKeys={form.deny_permission_keys}
          onToggle={(permissionKey, checked) => onPermission('allow', permissionKey, checked)}
        />

        <PermissionEditor
          title="Deny Overrides"
          description="Explicitly remove permissions from the role baseline."
          groups={groups}
          selectedKeys={form.deny_permission_keys}
          opposingKeys={form.allow_permission_keys}
          onToggle={(permissionKey, checked) => onPermission('deny', permissionKey, checked)}
        />

        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Saving...' : form.id ? 'Update Admin' : 'Create Admin'}</button>
        </div>
      </form>
    </Modal>
  );
}

function RoleModal({ open, form, groups, saving, onClose, onSubmit, onField, onPermission }) {
  return (
    <Modal open={open} title={form.id ? 'Edit Role' : 'Create Role'} onClose={onClose} size="large">
      <form className="space-y-5" onSubmit={onSubmit}>
        <div className="grid gap-3 md:grid-cols-2">
          <FormInput label="Role Code" value={form.code} required disabled={Boolean(form.id)} placeholder="REPORT_REVIEWER" onChange={(event) => onField('code', event.target.value.toUpperCase())} />
          <FormInput label="Role Name" value={form.name} required placeholder="Report Reviewer" onChange={(event) => onField('name', event.target.value)} />
          <div className="md:col-span-2">
            <FormInput label="Description" value={form.description} placeholder="Describe the responsibility of this role" onChange={(event) => onField('description', event.target.value)} />
          </div>
          <FormInput as="select" label="Status" value={form.is_active ? 'active' : 'inactive'} onChange={(event) => onField('is_active', event.target.value === 'active')}>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </FormInput>
        </div>
        <PermissionEditor
          title="Role Permissions"
          description="Select the permission bundle granted by this role."
          groups={groups}
          selectedKeys={form.permission_keys}
          opposingKeys={[]}
          onToggle={onPermission}
        />
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Saving...' : form.id ? 'Update Role' : 'Create Role'}</button>
        </div>
      </form>
    </Modal>
  );
}

function PermissionEditor({ title, description, groups, selectedKeys, opposingKeys, onToggle }) {
  const selected = new Set(selectedKeys || []);
  const opposing = new Set(opposingKeys || []);
  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="text-xs text-slate-500">{description}</p>
      </div>
      {groups.map((group) => (
        <div key={group.key} className="rounded-2xl border border-slate-200 p-3 dark:border-slate-700">
          <p className="text-sm font-semibold">{group.label}</p>
          <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
            {group.permissions.map((permission) => {
              const checked = selected.has(permission.key);
              const disabled = opposing.has(permission.key);
              return (
                <label key={permission.key} className={`flex items-start gap-3 rounded-xl border px-3 py-3 text-sm ${checked ? 'border-slate-900 bg-slate-900 text-white dark:border-white dark:bg-white dark:text-slate-900' : 'border-slate-200 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200'} ${disabled ? 'opacity-50' : ''}`}>
                  <input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onToggle(permission.key, event.target.checked)} />
                  <div>
                    <div className="font-medium">{permission.key}</div>
                    <div className={`text-xs ${checked ? 'text-slate-200 dark:text-slate-700' : 'text-slate-500'}`}>{permission.description || 'Permission'}</div>
                  </div>
                </label>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

function ScopeSummary({ scopes }) {
  if (!Array.isArray(scopes) || scopes.length === 0) return <span className="text-slate-500">Global</span>;
  return (
    <div className="space-y-1">
      {scopes.slice(0, 2).map((scope, index) => (
        <div key={`${scope.department_id || ''}-${scope.year_id || ''}-${index}`} className="text-xs text-slate-600 dark:text-slate-300">
          {scope.department_id || 'Any dept'} | {scope.year_id || 'Any year'}
        </div>
      ))}
      {scopes.length > 2 ? <div className="text-xs text-slate-500">+{scopes.length - 2} more</div> : null}
    </div>
  );
}

function AdminDetailsCell({ row }) {
  const createdAt = row.created_at ? new Date(row.created_at).toLocaleString() : '-';
  const updatedAt = row.updated_at ? new Date(row.updated_at).toLocaleString() : 'Never';
  return (
    <div className="space-y-1 text-xs">
      <div className="font-medium text-slate-700 dark:text-slate-200">
        Type: {row.admin_type || '-'}
      </div>
      <div className="text-slate-500 dark:text-slate-400">
        RBAC: {row.rbac_role_code || row.admin_role?.code || '-'}
      </div>
      <div className="text-slate-500 dark:text-slate-400">
        Created: {createdAt}
      </div>
      <div className="text-slate-500 dark:text-slate-400">
        Updated: {updatedAt}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const classes = status === 'active'
    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-200'
    : status === 'inactive'
      ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200'
      : 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-200';
  return <span className={`rounded-full px-2 py-1 text-xs font-medium ${classes}`}>{status}</span>;
}

function Metric({ label, value }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
    </Card>
  );
}
