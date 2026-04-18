import { useEffect, useMemo, useRef, useState } from 'react';
import { apiClient } from '../../services/apiClient';
import { getSectionPage } from '../../services/sectionsApi';

function normalizeQuery(query) {
  return {
    q: String(query.q || '').trim(),
    role: String(query.role || '').trim(),
    status: String(query.status || '').trim(),
    adminType: String(query.adminType || '').trim(),
    extension: String(query.extension || '').trim(),
    department: String(query.department || '').trim(),
    page: Number(query.page || 1),
    limit: Number(query.limit || 25),
    sortBy: String(query.sortBy || 'updated_at'),
    sortDir: String(query.sortDir || 'desc')
  };
}

function listParamsFromQuery(query) {
  const normalized = normalizeQuery(query);
  return {
    q: normalized.q || undefined,
    roles: normalized.role || undefined,
    is_active:
      normalized.status === 'active' ? true : normalized.status === 'inactive' ? false : undefined,
    admin_types: normalized.adminType || undefined,
    extensions: normalized.extension || undefined,
    department: normalized.department || undefined,
    sort_by: normalized.sortBy,
    sort_dir: normalized.sortDir === 'asc' ? 'asc' : 'desc',
    page: normalized.page > 0 ? normalized.page : 1,
    limit: [10, 25, 50, 100].includes(normalized.limit) ? normalized.limit : 25
  };
}

const DEFAULT_USERS_ADMIN_CAPABILITIES = {
  workspace: true,
  activity: true,
  bulk_operations: true,
  permission_templates: true,
  invitations: true,
  import_export: true,
  inline_editing: true,
  compact_density: true,
  responsive_workflows: true,
  table_virtualization: false,
  http_cache_validation: false,
  rollout_stage: 'all_admins',
  rollout_cohort: 'admin',
  rollout_access: true,
  rollout_reason: null
};

const CAPABILITY_DISABLED_MESSAGES = {
  workspace: 'Users workspace is currently disabled by configuration.',
  activity: 'User activity is currently disabled by configuration.',
  bulk_operations: 'Bulk operations are currently disabled by configuration.',
  permission_templates: 'Permission templates are currently disabled by configuration.',
  invitations: 'Invitations are currently disabled by configuration.',
  import_export: 'Import and export are currently disabled by configuration.',
  inline_editing: 'Inline editing is currently disabled by configuration.',
  compact_density: 'Compact density mode is currently disabled by configuration.',
  responsive_workflows: 'Responsive workflows are currently disabled by configuration.'
};

const DEFAULT_USERS_ADMIN_DASHBOARD = {
  window_minutes: 60,
  bucket_minutes: 5,
  generated_at: null,
  latency: {
    request_count: 0,
    success_count: 0,
    error_count: 0,
    error_rate_pct: 0,
    avg_duration_ms: 0,
    p50_duration_ms: 0,
    p95_duration_ms: 0,
    p99_duration_ms: 0,
    buckets: []
  },
  pagination: {
    sample_count: 0,
    avg_page: 0,
    avg_limit: 0,
    empty_page_rate_pct: 0,
    deep_page_rate_pct: 0,
    top_page_sizes: []
  },
  alerts: []
};

export function useUsersPageData({ pushToast, queryState, selectedUserId }) {
  const [rows, setRows] = useState([]);
  const [meta, setMeta] = useState({ page: 1, limit: 25, total: 0, total_pages: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [filterOptions, setFilterOptions] = useState({
    roles: [],
    admin_types: [],
    extensions: [],
    departments: [],
    status: []
  });
  const [filtersLoading, setFiltersLoading] = useState(false);
  const [detailsById, setDetailsById] = useState({});
  const [activityByUserId, setActivityByUserId] = useState({});
  const [activityLoadingByUserId, setActivityLoadingByUserId] = useState({});
  const [draftRoles, setDraftRoles] = useState({});
  const [draftScopes, setDraftScopes] = useState({});
  const [savingIds, setSavingIds] = useState([]);
  const [updatingProfileIds, setUpdatingProfileIds] = useState([]);
  const [creatingUser, setCreatingUser] = useState(false);
  const [invitingUser, setInvitingUser] = useState(false);
  const [importPreview, setImportPreview] = useState(null);
  const [importing, setImporting] = useState(false);
  const [permissionTemplates, setPermissionTemplates] = useState([]);
  const [permissionTemplateSaving, setPermissionTemplateSaving] = useState(false);
  const [filterPresets, setFilterPresets] = useState([]);
  const [filterPresetsLoading, setFilterPresetsLoading] = useState(false);
  const [savingFilterPreset, setSavingFilterPreset] = useState(false);
  const [refreshCounter, setRefreshCounter] = useState(0);
  const [capabilities, setCapabilities] = useState(DEFAULT_USERS_ADMIN_CAPABILITIES);
  const [capabilitiesReady, setCapabilitiesReady] = useState(false);
  const [adminDashboard, setAdminDashboard] = useState(DEFAULT_USERS_ADMIN_DASHBOARD);
  const [adminDashboardLoading, setAdminDashboardLoading] = useState(false);
  const [adminDashboardError, setAdminDashboardError] = useState('');
  const listEtagByKeyRef = useRef({});
  const listPayloadByKeyRef = useRef({});

  const [faculties, setFaculties] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [specializations, setSpecializations] = useState([]);
  const [batches, setBatches] = useState([]);
  const [semesters, setSemesters] = useState([]);
  const [sections, setSections] = useState([]);
  const [clubs, setClubs] = useState([]);

  const stableListParams = useMemo(() => listParamsFromQuery(queryState), [queryState]);
  const stableListParamsKey = JSON.stringify(stableListParams);

  function makeCapabilityError(capability) {
    return new Error(
      CAPABILITY_DISABLED_MESSAGES[capability] || `Capability "${String(capability || '')}" is disabled.`
    );
  }

  function ensureCapabilityEnabled(capability) {
    if (capabilities?.[capability] === false) {
      throw makeCapabilityError(capability);
    }
  }

  useEffect(() => {
    const controller = new AbortController();

    async function loadUsers() {
      if (!capabilitiesReady) {
        setLoading(true);
        return;
      }
      if (!capabilities.workspace) {
        setRows([]);
        setMeta({
          page: Number(stableListParams.page || 1),
          limit: Number(stableListParams.limit || 25),
          total: 0,
          total_pages: 0
        });
        setError(capabilities.rollout_reason || CAPABILITY_DISABLED_MESSAGES.workspace);
        setLoading(false);
        return;
      }
      setLoading(true);
      setError('');
      try {
        const useHttpCacheValidation = capabilities.http_cache_validation !== false;
        const cacheKey = stableListParamsKey;
        const previousEtag = listEtagByKeyRef.current[cacheKey];
        const response = await apiClient.get('/users/admin/list', {
          params: stableListParams,
          signal: controller.signal,
          headers:
            useHttpCacheValidation && previousEtag
              ? { 'If-None-Match': previousEtag }
              : undefined,
          validateStatus: useHttpCacheValidation
            ? (statusCode) => (statusCode >= 200 && statusCode < 300) || statusCode === 304
            : undefined
        });
        let data = response.data || {};
        if (response.status === 304 && useHttpCacheValidation) {
          data = listPayloadByKeyRef.current[cacheKey] || {};
        } else if (useHttpCacheValidation) {
          const etagValue = response?.headers?.etag;
          if (etagValue) {
            listEtagByKeyRef.current[cacheKey] = etagValue;
          }
          listPayloadByKeyRef.current[cacheKey] = data;
        }
        setRows(Array.isArray(data.items) ? data.items : []);
        setMeta({
          page: Number(data.page || stableListParams.page || 1),
          limit: Number(data.limit || stableListParams.limit || 25),
          total: Number(data.total || 0),
          total_pages: Number(data.total_pages || 0)
        });
        await emitUsersTelemetry('users.frontend.list_load', 'success', {
          scope: 'workspace',
          metadata: {
            page: Number(data.page || stableListParams.page || 1),
            limit: Number(data.limit || stableListParams.limit || 25),
            total: Number(data.total || 0),
            returned: Array.isArray(data.items) ? data.items.length : 0,
            cache_hit: response.status === 304
          }
        });
      } catch (err) {
        if (controller.signal.aborted) return;
        const detail = err?.response?.data?.detail || 'Failed to load users';
        setError(String(detail));
        await emitUsersTelemetry('users.frontend.list_load', 'error', {
          scope: 'workspace',
          severity: 'medium',
          metadata: { message: String(detail) }
        });
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    loadUsers();
    return () => controller.abort();
  }, [stableListParamsKey, refreshCounter, capabilities.workspace, capabilities.http_cache_validation, capabilitiesReady]);

  useEffect(() => {
    const controller = new AbortController();
    async function loadFilterOptions() {
      if (!capabilitiesReady) {
        setFiltersLoading(true);
        return;
      }
      if (!capabilities.workspace) {
        setFilterOptions({ roles: [], admin_types: [], extensions: [], departments: [], status: [] });
        setFiltersLoading(false);
        return;
      }
      setFiltersLoading(true);
      try {
        const response = await apiClient.get('/users/filter-options', {
          params: stableListParams,
          signal: controller.signal
        });
        if (!controller.signal.aborted) {
          setFilterOptions(
            response.data || {
              roles: [],
              admin_types: [],
              extensions: [],
              departments: [],
              status: []
            }
          );
          await emitUsersTelemetry('users.frontend.filter_options', 'success', {
            scope: 'workspace'
          });
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setFilterOptions({ roles: [], admin_types: [], extensions: [], departments: [], status: [] });
          const detail = err?.response?.data?.detail || 'Failed to load filter options';
          await emitUsersTelemetry('users.frontend.filter_options', 'error', {
            scope: 'workspace',
            metadata: { message: String(detail) }
          });
        }
      } finally {
        if (!controller.signal.aborted) {
          setFiltersLoading(false);
        }
      }
    }
    loadFilterOptions();
    return () => controller.abort();
  }, [stableListParamsKey, capabilities.workspace, capabilitiesReady]);

  useEffect(() => {
    const controller = new AbortController();
    async function loadDashboardOnRefresh() {
      if (!capabilitiesReady) {
        setAdminDashboardLoading(true);
        return;
      }
      if (!capabilities.workspace) {
        setAdminDashboard(DEFAULT_USERS_ADMIN_DASHBOARD);
        setAdminDashboardError(capabilities.rollout_reason || CAPABILITY_DISABLED_MESSAGES.workspace);
        setAdminDashboardLoading(false);
        return;
      }
      try {
        await loadAdminDashboard({
          silent: true,
          signal: controller.signal
        });
      } catch {
        // Silent mode intentionally suppresses dashboard refresh failures.
      }
    }
    loadDashboardOnRefresh();
    return () => controller.abort();
  }, [capabilities.workspace, capabilitiesReady, refreshCounter]);

  useEffect(() => {
    loadLookups();
    loadCapabilities();
    loadPermissionTemplates();
    loadFilterPresets();
  }, []);

  useEffect(() => {
    if (!selectedUserId) return;
    loadUserDetail(selectedUserId);
    loadUserActivity(selectedUserId);
  }, [selectedUserId]);

  async function loadLookups() {
    const [facultiesRes, departmentsRes, programsRes, specializationsRes, batchesRes, semestersRes, sectionsRes, clubsRes] =
      await Promise.allSettled([
        apiClient.get('/faculties/', { params: { skip: 0, limit: 100 } }),
        apiClient.get('/departments/', { params: { skip: 0, limit: 100 } }),
        apiClient.get('/programs/', { params: { skip: 0, limit: 100 } }),
        apiClient.get('/specializations/', { params: { skip: 0, limit: 100 } }),
        apiClient.get('/batches/', { params: { skip: 0, limit: 100 } }),
        apiClient.get('/semesters/', { params: { skip: 0, limit: 100 } }),
        getSectionPage({}, 100),
        apiClient.get('/clubs/', { params: { skip: 0, limit: 100 } })
      ]);

    setFaculties(facultiesRes.status === 'fulfilled' ? facultiesRes.value.data || [] : []);
    setDepartments(departmentsRes.status === 'fulfilled' ? departmentsRes.value.data || [] : []);
    setPrograms(programsRes.status === 'fulfilled' ? programsRes.value.data || [] : []);
    setSpecializations(specializationsRes.status === 'fulfilled' ? specializationsRes.value.data || [] : []);
    setBatches(batchesRes.status === 'fulfilled' ? batchesRes.value.data || [] : []);
    setSemesters(semestersRes.status === 'fulfilled' ? semestersRes.value.data || [] : []);
    setSections(sectionsRes.status === 'fulfilled' ? sectionsRes.value || [] : []);
    setClubs(clubsRes.status === 'fulfilled' ? clubsRes.value.data || [] : []);
  }

  async function loadCapabilities() {
    try {
      const response = await apiClient.get('/users/admin/capabilities');
      setCapabilities({ ...DEFAULT_USERS_ADMIN_CAPABILITIES, ...(response.data || {}) });
    } catch {
      setCapabilities(DEFAULT_USERS_ADMIN_CAPABILITIES);
    } finally {
      setCapabilitiesReady(true);
    }
  }

  async function emitUsersTelemetry(event, outcome = 'success', payload = {}) {
    try {
      await apiClient.post('/users/admin/telemetry', {
        event,
        outcome,
        scope: payload.scope,
        severity: payload.severity || (outcome === 'error' ? 'medium' : 'low'),
        metadata: payload.metadata || {}
      });
    } catch {
      // Best-effort telemetry: do not interrupt primary flows.
    }
  }

  async function loadAdminDashboard({ silent = true, signal } = {}) {
    setAdminDashboardLoading(true);
    if (!silent) {
      setAdminDashboardError('');
    }
    try {
      ensureCapabilityEnabled('workspace');
      const response = await apiClient.get('/users/admin/dashboard', {
        params: { window_minutes: 60, bucket_minutes: 5 },
        signal
      });
      setAdminDashboard({
        ...DEFAULT_USERS_ADMIN_DASHBOARD,
        ...(response.data || {}),
        latency: {
          ...DEFAULT_USERS_ADMIN_DASHBOARD.latency,
          ...(response.data?.latency || {}),
          buckets: Array.isArray(response.data?.latency?.buckets) ? response.data.latency.buckets : []
        },
        pagination: {
          ...DEFAULT_USERS_ADMIN_DASHBOARD.pagination,
          ...(response.data?.pagination || {}),
          top_page_sizes: Array.isArray(response.data?.pagination?.top_page_sizes)
            ? response.data.pagination.top_page_sizes
            : []
        },
        alerts: Array.isArray(response.data?.alerts) ? response.data.alerts : []
      });
      setAdminDashboardError('');
      await emitUsersTelemetry('users.frontend.dashboard_load', 'success', {
        scope: 'workspace'
      });
      return response.data || DEFAULT_USERS_ADMIN_DASHBOARD;
    } catch (err) {
      const message = err?.response?.data?.detail || err?.message || 'Failed to load users dashboard';
      setAdminDashboard(DEFAULT_USERS_ADMIN_DASHBOARD);
      setAdminDashboardError(String(message));
      await emitUsersTelemetry('users.frontend.dashboard_load', 'error', {
        scope: 'workspace',
        severity: 'medium',
        metadata: { message: String(message) }
      });
      if (!silent) {
        pushToast({
          title: 'Dashboard unavailable',
          description: String(message),
          variant: 'warning'
        });
      }
      throw err;
    } finally {
      setAdminDashboardLoading(false);
    }
  }

  async function loadPermissionTemplates(role = '') {
    if (!capabilities.permission_templates) {
      setPermissionTemplates([]);
      return [];
    }
    try {
      const response = await apiClient.get('/users/permission-templates', {
        params: role ? { role } : undefined
      });
      setPermissionTemplates(Array.isArray(response.data) ? response.data : []);
    } catch {
      setPermissionTemplates([]);
      return [];
    }
  }

  async function createPermissionTemplate(payload) {
    ensureCapabilityEnabled('permission_templates');
    setPermissionTemplateSaving(true);
    try {
      const response = await apiClient.post('/users/permission-templates', payload);
      const created = response.data || null;
      await loadPermissionTemplates();
      await emitUsersTelemetry('users.frontend.permission_template_create', 'success', {
        scope: 'permission_templates',
        metadata: { role: payload?.role, template_id: created?.id || null }
      });
      return created;
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to create permission template';
      await emitUsersTelemetry('users.frontend.permission_template_create', 'error', {
        scope: 'permission_templates',
        severity: 'medium',
        metadata: { role: payload?.role, message: String(detail) }
      });
      throw err;
    } finally {
      setPermissionTemplateSaving(false);
    }
  }

  async function updatePermissionTemplate(templateId, payload) {
    if (!templateId) return null;
    ensureCapabilityEnabled('permission_templates');
    setPermissionTemplateSaving(true);
    try {
      const response = await apiClient.patch(`/users/permission-templates/${templateId}`, payload);
      const updated = response.data || null;
      await loadPermissionTemplates();
      await emitUsersTelemetry('users.frontend.permission_template_update', 'success', {
        scope: 'permission_templates',
        metadata: { template_id: templateId }
      });
      return updated;
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to update permission template';
      await emitUsersTelemetry('users.frontend.permission_template_update', 'error', {
        scope: 'permission_templates',
        severity: 'medium',
        metadata: { template_id: templateId, message: String(detail) }
      });
      throw err;
    } finally {
      setPermissionTemplateSaving(false);
    }
  }

  async function deletePermissionTemplate(templateId) {
    if (!templateId) return null;
    ensureCapabilityEnabled('permission_templates');
    setPermissionTemplateSaving(true);
    try {
      const response = await apiClient.delete(`/users/permission-templates/${templateId}`);
      await loadPermissionTemplates();
      await emitUsersTelemetry('users.frontend.permission_template_delete', 'success', {
        scope: 'permission_templates',
        severity: 'medium',
        metadata: { template_id: templateId }
      });
      return response.data || null;
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to delete permission template';
      await emitUsersTelemetry('users.frontend.permission_template_delete', 'error', {
        scope: 'permission_templates',
        severity: 'high',
        metadata: { template_id: templateId, message: String(detail) }
      });
      throw err;
    } finally {
      setPermissionTemplateSaving(false);
    }
  }

  async function loadFilterPresets() {
    setFilterPresetsLoading(true);
    try {
      const response = await apiClient.get('/users/filter-presets');
      setFilterPresets(Array.isArray(response.data) ? response.data : []);
    } catch {
      setFilterPresets([]);
    } finally {
      setFilterPresetsLoading(false);
    }
  }

  async function loadUserDetail(userId) {
    if (!userId) return null;
    try {
      const response = await apiClient.get(`/users/${userId}`);
      const user = response.data || null;
      if (user) {
        setDetailsById((prev) => ({ ...prev, [userId]: user }));
      }
      return user;
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to load user details';
      pushToast({ title: 'Details unavailable', description: String(detail), variant: 'error' });
      await emitUsersTelemetry('users.frontend.user_details', 'error', {
        scope: 'workspace',
        metadata: { user_id: userId, message: String(detail) }
      });
      return null;
    }
  }

  async function loadUserActivity(userId) {
    if (!userId) return [];
    if (!capabilities.activity) {
      setActivityByUserId((prev) => ({ ...prev, [userId]: [] }));
      return [];
    }
    setActivityLoadingByUserId((prev) => ({ ...prev, [userId]: true }));
    try {
      const response = await apiClient.get(`/users/${userId}/activity`, { params: { page: 1, limit: 25 } });
      const items = Array.isArray(response.data?.items) ? response.data.items : [];
      setActivityByUserId((prev) => ({ ...prev, [userId]: items }));
      await emitUsersTelemetry('users.frontend.activity_load', 'success', {
        scope: 'activity',
        metadata: { user_id: userId, returned: items.length }
      });
      return items;
    } catch (err) {
      setActivityByUserId((prev) => ({ ...prev, [userId]: [] }));
      const detail = err?.response?.data?.detail || 'Failed to load user activity';
      await emitUsersTelemetry('users.frontend.activity_load', 'error', {
        scope: 'activity',
        metadata: { user_id: userId, message: String(detail) }
      });
      return [];
    } finally {
      setActivityLoadingByUserId((prev) => ({ ...prev, [userId]: false }));
    }
  }

  function getMergedUserById(userId) {
    if (!userId) return null;
    const row = rows.find((item) => item.id === userId) || null;
    const details = detailsById[userId] || null;
    if (!row && !details) return null;
    return { ...(row || {}), ...(details || {}) };
  }

  function getEffectiveExtensions(user) {
    if (!user) return [];
    return draftRoles[user.id] ?? user.extended_roles ?? [];
  }

  function getEffectiveScope(user) {
    if (!user) return {};
    return draftScopes[user.id] ?? user.role_scope ?? {};
  }

  function setScopeForUser(user, nextScope) {
    if (!user?.id) return;
    setDraftScopes((prev) => ({ ...prev, [user.id]: nextScope }));
  }

  function updateClassCoordinatorScope(user, patch) {
    const current = getEffectiveScope(user);
    const existing = current.class_coordinator || {};
    setScopeForUser(user, {
      ...current,
      class_coordinator: { ...existing, ...patch }
    });
  }

  function updateClubPresidentScope(user, patch) {
    const current = getEffectiveScope(user);
    const existing = current.club_president || {};
    setScopeForUser(user, {
      ...current,
      club_president: { ...existing, ...patch }
    });
  }

  function updateClassRepresentativeScope(user, patch) {
    const current = getEffectiveScope(user);
    const existing = current.class_representative || {};
    setScopeForUser(user, {
      ...current,
      class_representative: { ...existing, ...patch }
    });
  }

  function toggleExtension(user, extension) {
    const current = getEffectiveExtensions(user);
    const next = current.includes(extension)
      ? current.filter((item) => item !== extension)
      : [...current, extension];
    setDraftRoles((prev) => ({ ...prev, [user.id]: next }));
  }

  function applyPermissionTemplate(user, template) {
    if (!user?.id || !template) return;
    setDraftRoles((prev) => ({ ...prev, [user.id]: template.extended_roles || [] }));
    setDraftScopes((prev) => ({ ...prev, [user.id]: template.role_scope || {} }));
  }

  function resetPermissionDraft(user) {
    if (!user?.id) return;
    setDraftRoles((prev) => {
      const copy = { ...prev };
      delete copy[user.id];
      return copy;
    });
    setDraftScopes((prev) => {
      const copy = { ...prev };
      delete copy[user.id];
      return copy;
    });
  }

  function refreshUsers() {
    setRefreshCounter((prev) => prev + 1);
  }

  async function savePermissions(user, changeReason = '') {
    if (!user?.id) return;
    const nextRoles = getEffectiveExtensions(user);
    const nextScope = getEffectiveScope(user);
    setSavingIds((prev) => (prev.includes(user.id) ? prev : [...prev, user.id]));
    try {
      const response = await apiClient.patch(`/users/${user.id}/extensions`, {
        extended_roles: nextRoles,
        role_scope: nextScope,
        change_reason: String(changeReason || '').trim() || undefined
      });
      const updated = response.data || {};
      setRows((prev) =>
        prev.map((item) =>
          item.id === user.id
            ? {
                ...item,
                extended_roles: updated.extended_roles || nextRoles,
                role_scope: updated.role_scope || nextScope,
                updated_at: updated.updated_at || item.updated_at,
                last_permission_change_at: updated.last_permission_change_at || item.last_permission_change_at,
                last_permission_change_by: updated.last_permission_change_by || item.last_permission_change_by
              }
            : item
        )
      );
      setDetailsById((prev) => ({ ...prev, [user.id]: { ...(prev[user.id] || {}), ...updated } }));
      setDraftRoles((prev) => {
        const copy = { ...prev };
        delete copy[user.id];
        return copy;
      });
      setDraftScopes((prev) => {
        const copy = { ...prev };
        delete copy[user.id];
        return copy;
      });
      await emitUsersTelemetry('users.frontend.permissions_save', 'success', {
        scope: 'workspace',
        metadata: { user_id: user.id, extension_count: nextRoles.length }
      });
      pushToast({ title: 'Permissions updated', description: 'User permissions were saved.', variant: 'success' });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to update permissions';
      pushToast({ title: 'Update failed', description: String(detail), variant: 'error' });
      await emitUsersTelemetry('users.frontend.permissions_save', 'error', {
        scope: 'workspace',
        severity: 'medium',
        metadata: { user_id: user.id, message: String(detail) }
      });
      throw err;
    } finally {
      setSavingIds((prev) => prev.filter((id) => id !== user.id));
    }
  }

  async function updateUserProfile(userId, payload) {
    if (!userId) return null;
    ensureCapabilityEnabled('inline_editing');
    setUpdatingProfileIds((prev) => (prev.includes(userId) ? prev : [...prev, userId]));
    try {
      const response = await apiClient.patch(`/users/${userId}/profile`, payload);
      const updated = response.data || {};
      const nextDepartment = updated.profile?.department ?? null;
      const nextDesignation = updated.profile?.designation ?? null;
      setRows((prev) =>
        prev.map((item) =>
          item.id === userId
            ? {
                ...item,
                full_name: updated.full_name || item.full_name,
                department: nextDepartment,
                designation: nextDesignation,
                updated_at: updated.updated_at || item.updated_at
              }
            : item
        )
      );
      setDetailsById((prev) => ({ ...prev, [userId]: { ...(prev[userId] || {}), ...updated } }));
      await emitUsersTelemetry('users.frontend.profile_update', 'success', {
        scope: 'inline_editing',
        metadata: { user_id: userId, changed_fields: Object.keys(payload || {}).filter((key) => key !== 'change_reason') }
      });
      return updated;
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to update profile';
      await emitUsersTelemetry('users.frontend.profile_update', 'error', {
        scope: 'inline_editing',
        severity: 'medium',
        metadata: { user_id: userId, message: String(detail) }
      });
      throw err;
    } finally {
      setUpdatingProfileIds((prev) => prev.filter((id) => id !== userId));
    }
  }

  async function updateUserStatus(userId, isActive, reason) {
    try {
      const response = await apiClient.patch(`/users/${userId}/status`, { is_active: isActive, reason });
      const updated = response.data || {};
      setRows((prev) => prev.map((item) => (item.id === userId ? { ...item, ...updated } : item)));
      setDetailsById((prev) => ({ ...prev, [userId]: { ...(prev[userId] || {}), ...updated } }));
      await emitUsersTelemetry('users.frontend.status_update', 'success', {
        scope: 'workspace',
        severity: 'medium',
        metadata: { user_id: userId, is_active: isActive }
      });
      return updated;
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to update status';
      await emitUsersTelemetry('users.frontend.status_update', 'error', {
        scope: 'workspace',
        severity: 'medium',
        metadata: { user_id: userId, message: String(detail) }
      });
      throw err;
    }
  }

  async function bulkUpdateStatus(userIds, isActive, reason) {
    ensureCapabilityEnabled('bulk_operations');
    try {
      const response = await apiClient.post('/users/bulk/status', {
        user_ids: userIds,
        is_active: isActive,
        reason
      });
      const payload = response.data || {};
      await Promise.all(
        (payload.results || [])
          .filter((item) => item.success)
          .map((item) => loadUserDetail(item.user_id))
      );
      await emitUsersTelemetry('users.frontend.bulk_status', 'success', {
        scope: 'bulk_operations',
        severity: 'medium',
        metadata: {
          requested_count: userIds.length,
          updated_count: payload.updated_count || 0,
          failed_count: payload.failed_count || 0
        }
      });
      return payload;
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed bulk status update';
      await emitUsersTelemetry('users.frontend.bulk_status', 'error', {
        scope: 'bulk_operations',
        severity: 'high',
        metadata: { requested_count: userIds.length, message: String(detail) }
      });
      throw err;
    }
  }

  async function bulkUpdateExtensions(updates, changeReason) {
    ensureCapabilityEnabled('bulk_operations');
    try {
      const response = await apiClient.patch('/users/bulk/extensions', {
        updates,
        change_reason: changeReason
      });
      const payload = response.data || {};
      await Promise.all(
        (payload.results || [])
          .filter((item) => item.success)
          .map((item) => loadUserDetail(item.user_id))
      );
      await emitUsersTelemetry('users.frontend.bulk_extensions', 'success', {
        scope: 'bulk_operations',
        severity: 'medium',
        metadata: {
          requested_count: updates.length,
          updated_count: payload.updated_count || 0,
          failed_count: payload.failed_count || 0
        }
      });
      return payload;
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed bulk extensions update';
      await emitUsersTelemetry('users.frontend.bulk_extensions', 'error', {
        scope: 'bulk_operations',
        severity: 'high',
        metadata: { requested_count: updates.length, message: String(detail) }
      });
      throw err;
    }
  }

  async function createDirectUser(payload) {
    setCreatingUser(true);
    try {
      const response = await apiClient.post('/users/', payload);
      await emitUsersTelemetry('users.frontend.user_create', 'success', {
        scope: 'workspace',
        metadata: { role: payload?.role, has_scope: Boolean(payload?.role_scope) }
      });
      pushToast({ title: 'User created', description: 'New user account has been created.', variant: 'success' });
      return response.data;
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to create user';
      await emitUsersTelemetry('users.frontend.user_create', 'error', {
        scope: 'workspace',
        severity: 'medium',
        metadata: { role: payload?.role, message: String(detail) }
      });
      throw err;
    } finally {
      setCreatingUser(false);
    }
  }

  async function inviteUser(payload) {
    ensureCapabilityEnabled('invitations');
    setInvitingUser(true);
    try {
      const response = await apiClient.post('/users/invitations', payload);
      pushToast({ title: 'Invitation sent', description: 'Invitation record created successfully.', variant: 'success' });
      await emitUsersTelemetry('users.frontend.invitation_create', 'success', {
        scope: 'invitations',
        metadata: { role: payload.role }
      });
      return response.data;
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to create invitation';
      await emitUsersTelemetry('users.frontend.invitation_create', 'error', {
        scope: 'invitations',
        metadata: { message: String(detail) }
      });
      throw err;
    } finally {
      setInvitingUser(false);
    }
  }

  async function previewImport(file) {
    if (!file) return null;
    ensureCapabilityEnabled('import_export');
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await apiClient.post('/users/import/preview', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      const payload = response.data || null;
      setImportPreview(payload);
      await emitUsersTelemetry('users.frontend.import_preview', 'success', {
        scope: 'import_export',
        metadata: {
          total_rows: payload?.total_rows || 0,
          valid_rows: payload?.valid_rows || 0,
          invalid_rows: payload?.invalid_rows || 0
        }
      });
      return payload;
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed import preview';
      await emitUsersTelemetry('users.frontend.import_preview', 'error', {
        scope: 'import_export',
        metadata: { message: String(detail) }
      });
      throw err;
    }
  }

  async function commitImport({ mode, defaultPassword }) {
    if (!importPreview) return null;
    ensureCapabilityEnabled('import_export');
    setImporting(true);
    try {
      const rowsForCommit = (importPreview.rows || [])
        .filter((row) => row.valid)
        .map((row) => ({
          full_name: row.full_name,
          email: row.email,
          role: row.role,
          admin_type: row.admin_type || null,
          extended_roles: Array.isArray(row.extended_roles) ? row.extended_roles : []
        }));
      const response = await apiClient.post('/users/import/commit', {
        mode,
        default_password: mode === 'create' ? defaultPassword : undefined,
        rows: rowsForCommit
      });
      pushToast({ title: 'Import committed', description: 'User import commit completed.', variant: 'success' });
      setImportPreview(null);
      await emitUsersTelemetry('users.frontend.import_commit', 'success', {
        scope: 'import_export',
        severity: 'medium',
        metadata: { mode, rows: rowsForCommit.length }
      });
      return response.data;
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed import commit';
      await emitUsersTelemetry('users.frontend.import_commit', 'error', {
        scope: 'import_export',
        severity: 'high',
        metadata: { mode, message: String(detail) }
      });
      throw err;
    } finally {
      setImporting(false);
    }
  }

  async function exportCsv() {
    ensureCapabilityEnabled('import_export');
    try {
      const response = await apiClient.get('/users/export.csv', {
        params: stableListParams,
        responseType: 'blob'
      });
      const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `users-export-${new Date().toISOString().replace(/[:.]/g, '-')}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      await emitUsersTelemetry('users.frontend.export_csv', 'success', {
        scope: 'import_export'
      });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed export';
      await emitUsersTelemetry('users.frontend.export_csv', 'error', {
        scope: 'import_export',
        metadata: { message: String(detail) }
      });
      throw err;
    }
  }

  async function createFilterPreset(payload) {
    setSavingFilterPreset(true);
    try {
      const response = await apiClient.post('/users/filter-presets', payload);
      await loadFilterPresets();
      return response.data || null;
    } finally {
      setSavingFilterPreset(false);
    }
  }

  async function updateFilterPreset(presetId, payload) {
    if (!presetId) return null;
    setSavingFilterPreset(true);
    try {
      const response = await apiClient.patch(`/users/filter-presets/${presetId}`, payload);
      await loadFilterPresets();
      return response.data || null;
    } finally {
      setSavingFilterPreset(false);
    }
  }

  async function deleteFilterPreset(presetId) {
    if (!presetId) return null;
    setSavingFilterPreset(true);
    try {
      const response = await apiClient.delete(`/users/filter-presets/${presetId}`);
      await loadFilterPresets();
      return response.data || null;
    } finally {
      setSavingFilterPreset(false);
    }
  }

  return {
    capabilities,
    adminDashboard,
    adminDashboardLoading,
    adminDashboardError,
    loadAdminDashboard,
    rows,
    meta,
    loading,
    error,
    filterOptions,
    filtersLoading,
    detailsById,
    activityByUserId,
    activityLoadingByUserId,
    getMergedUserById,
    loadUserDetail,
    loadUserActivity,
    getEffectiveExtensions,
    getEffectiveScope,
    toggleExtension,
    updateClassCoordinatorScope,
    updateClubPresidentScope,
    updateClassRepresentativeScope,
    applyPermissionTemplate,
    resetPermissionDraft,
    savePermissions,
    savingIds,
    updatingProfileIds,
    updateUserProfile,
    refreshUsers,
    updateUserStatus,
    bulkUpdateStatus,
    bulkUpdateExtensions,
    createDirectUser,
    creatingUser,
    inviteUser,
    invitingUser,
    previewImport,
    importPreview,
    commitImport,
    importing,
    setImportPreview,
    exportCsv,
    filterPresets,
    filterPresetsLoading,
    savingFilterPreset,
    loadFilterPresets,
    createFilterPreset,
    updateFilterPreset,
    deleteFilterPreset,
    permissionTemplates,
    permissionTemplateSaving,
    loadPermissionTemplates,
    createPermissionTemplate,
    updatePermissionTemplate,
    deletePermissionTemplate,
    faculties,
    departments,
    programs,
    specializations,
    batches,
    semesters,
    sections,
    clubs
  };
}
