import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Bookmark,
  BookmarkPlus,
  Download,
  Edit3,
  Filter,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  Upload,
  UserPlus,
  Users,
  X
} from 'lucide-react';
import Card from '../components/ui/Card';
import FormInput from '../components/ui/FormInput';
import Table from '../components/ui/Table';
import { useAuthorizedImage } from '../hooks/useAuthorizedImage';
import { useToast } from '../hooks/useToast';
import { cn } from '../utils/cn';
import UserDetailOverlay from './users/UserDetailOverlay';
import { useUsersPageData } from './users/useUsersPageData';

const PAGE_SIZES = [10, 25, 50, 100];
const SORT_OPTIONS = [
  { value: 'updated_at', label: 'Recently Updated' },
  { value: 'created_at', label: 'Recently Created' },
  { value: 'full_name', label: 'Name' },
  { value: 'last_active_at', label: 'Last Active' }
];
const DENSITY_OPTIONS = [
  { value: 'comfortable', label: 'Comfortable' },
  { value: 'compact', label: 'Compact' }
];
const BULK_EXTENSIONS = ['year_head', 'class_coordinator', 'club_coordinator', 'club_president'];
const EXTENSIONS_BY_ROLE = {
  teacher: ['year_head', 'class_coordinator', 'club_coordinator'],
  student: ['club_president', 'class_representative'],
  admin: []
};
const USERS_OVERLAY_TOP_OFFSET_PX = 68;

export default function UsersPage() {
  const { pushToast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [filtersOpen, setFiltersOpen] = useState(true);
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(false);
  const [selectedRowIds, setSelectedRowIds] = useState([]);
  const [searchInput, setSearchInput] = useState(searchParams.get('q') || '');
  const [bulkExtension, setBulkExtension] = useState('year_head');
  const [bulkMode, setBulkMode] = useState('add');
  const [overlayModalType, setOverlayModalType] = useState('none');
  const [overlayReturnFocusEl, setOverlayReturnFocusEl] = useState(null);
  const [inlineDraftById, setInlineDraftById] = useState({});
  const [inlineEditingIds, setInlineEditingIds] = useState([]);
  const [inlineSavingIds, setInlineSavingIds] = useState([]);

  const queryState = useMemo(
    () => ({
      q: searchParams.get('q') || '',
      role: searchParams.get('role') || '',
      status: searchParams.get('status') || '',
      adminType: searchParams.get('admin_type') || '',
      extension: searchParams.get('extension') || '',
      department: searchParams.get('department') || '',
      page: Number(searchParams.get('page') || 1),
      limit: Number(searchParams.get('limit') || 25),
      sortBy: searchParams.get('sort_by') || 'updated_at',
      sortDir: searchParams.get('sort_dir') || 'desc',
      preset: searchParams.get('preset') || '',
      density: searchParams.get('density') === 'compact' ? 'compact' : 'comfortable'
    }),
    [searchParams]
  );

  const selectedUserId = searchParams.get('selected') || '';
  const selectedTab = searchParams.get('tab') || 'details';
  const overlayState = useMemo(() => {
    if (overlayModalType !== 'none') {
      return { type: overlayModalType, userId: '', tab: 'details' };
    }
    if (selectedUserId) {
      return { type: 'drawer', userId: selectedUserId, tab: selectedTab };
    }
    return { type: 'none', userId: '', tab: 'details' };
  }, [overlayModalType, selectedTab, selectedUserId]);
  const isAnyOverlayOpen = overlayState.type !== 'none';

  const {
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
    getMergedUserById,
    loadUserActivity,
    activityByUserId,
    activityLoadingByUserId,
    getEffectiveExtensions,
    getEffectiveScope,
    toggleExtension,
    updateClassCoordinatorScope,
    updateClubPresidentScope,
    updateClassRepresentativeScope,
    applyPermissionTemplate,
    savePermissions,
    resetPermissionDraft,
    savingIds,
    updatingProfileIds,
    updateUserProfile,
    updateUserStatus,
    bulkUpdateStatus,
    bulkUpdateExtensions,
    refreshUsers,
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
    createFilterPreset,
    updateFilterPreset,
    deleteFilterPreset,
    permissionTemplates,
    permissionTemplateSaving,
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
  } = useUsersPageData({ pushToast, queryState, selectedUserId });

  const canWorkspace = capabilities.workspace !== false;
  const canActivity = capabilities.activity !== false;
  const canBulkOperations = capabilities.bulk_operations !== false;
  const canInvitations = capabilities.invitations !== false;
  const canImportExport = capabilities.import_export !== false;
  const canInlineEditing = capabilities.inline_editing !== false;
  const canCompactDensity = capabilities.compact_density !== false;
  const canResponsiveWorkflows = capabilities.responsive_workflows !== false;
  const canTableVirtualization = capabilities.table_virtualization === true;
  const effectiveDensity = canCompactDensity ? queryState.density : 'comfortable';

  const selectedUser = useMemo(() => getMergedUserById(selectedUserId), [getMergedUserById, selectedUserId]);
  const selectedRows = useMemo(() => rows.filter((row) => selectedRowIds.includes(row.id)), [rows, selectedRowIds]);
  const selectedPreset = useMemo(
    () => filterPresets.find((item) => item.id === queryState.preset) || null,
    [filterPresets, queryState.preset]
  );

  useEffect(() => {
    setSearchInput(queryState.q);
  }, [queryState.q]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (searchInput === queryState.q) return;
      updateParams({ q: searchInput, page: '1' });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchInput, queryState.q]);

  useEffect(() => {
    setSelectedRowIds((prev) => prev.filter((id) => rows.some((row) => row.id === id)));
  }, [rows]);

  useEffect(() => {
    setInlineEditingIds((prev) => prev.filter((id) => rows.some((row) => row.id === id)));
    setInlineDraftById((prev) => {
      const next = {};
      Object.entries(prev).forEach(([userId, draft]) => {
        if (rows.some((row) => row.id === userId)) {
          next[userId] = draft;
        }
      });
      return next;
    });
  }, [rows]);

  useEffect(() => {
    if (!queryState.preset) return;
    if (filterPresetsLoading) return;
    const exists = filterPresets.some((item) => item.id === queryState.preset);
    if (!exists) {
      updateParams({ preset: '' });
    }
  }, [queryState.preset, filterPresets, filterPresetsLoading]);

  useEffect(() => {
    if (!canCompactDensity && queryState.density === 'compact') {
      updateParams({ density: 'comfortable' });
    }
  }, [canCompactDensity, queryState.density]);

  useEffect(() => {
    if (!canActivity && selectedTab === 'activity') {
      updateParams({ tab: 'details' });
    }
  }, [canActivity, selectedTab]);

  useEffect(() => {
    if (!canBulkOperations && selectedRowIds.length) {
      setSelectedRowIds([]);
    }
  }, [canBulkOperations, selectedRowIds.length]);

  useEffect(() => {
    if (!canInvitations && overlayModalType === 'invite') {
      setOverlayModalType('none');
    }
  }, [canInvitations, overlayModalType]);

  useEffect(() => {
    if (!canImportExport && overlayModalType === 'import') {
      setOverlayModalType('none');
      setImportPreview(null);
    }
  }, [canImportExport, overlayModalType]);

  useEffect(() => {
    if (!isAnyOverlayOpen || typeof document === 'undefined') return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isAnyOverlayOpen]);

  function updateParams(patch, replace = true) {
    const next = new URLSearchParams(searchParams);
    const filterKeys = new Set(['q', 'role', 'status', 'admin_type', 'extension', 'department', 'sort_by', 'sort_dir', 'limit']);
    const shouldClearPreset = !Object.prototype.hasOwnProperty.call(patch, 'preset')
      && Object.keys(patch).some((key) => filterKeys.has(key));

    Object.entries(patch).forEach(([key, value]) => {
      const normalized = String(value ?? '').trim();
      if (!normalized) next.delete(key);
      else next.set(key, normalized);
    });
    if (shouldClearPreset) {
      next.delete('preset');
    }
    setSearchParams(next, { replace });
  }

  function openUser(userId, tab = 'details') {
    setOverlayModalType('none');
    if (typeof document !== 'undefined' && document.activeElement instanceof HTMLElement) {
      setOverlayReturnFocusEl(document.activeElement);
    } else {
      setOverlayReturnFocusEl(null);
    }
    const nextTab = tab === 'activity' && !canActivity ? 'details' : tab;
    updateParams({ selected: userId, tab: nextTab });
  }

  function closeUser() {
    updateParams({ selected: '', tab: '' });
    if (overlayReturnFocusEl && typeof overlayReturnFocusEl.focus === 'function') {
      window.setTimeout(() => {
        try {
          overlayReturnFocusEl.focus();
        } catch {
          // Ignore focus restoration failures.
        }
      }, 0);
    }
    setOverlayReturnFocusEl(null);
  }

  function openModal(type) {
    setOverlayModalType(type);
    updateParams({ selected: '', tab: '' });
  }

  function closeModal() {
    setOverlayModalType('none');
  }

  function setActiveTab(tab) {
    if (tab === 'activity' && !canActivity) return;
    updateParams({ tab });
  }

  function handleSort(sortBy) {
    const nextSortDir =
      queryState.sortBy === sortBy && queryState.sortDir === 'asc' ? 'desc' : 'asc';
    updateParams({ sort_by: sortBy, sort_dir: nextSortDir, page: '1' });
  }

  function handleFilterChange(key, value) {
    updateParams({ [key]: value, page: '1' });
  }

  function handleToggleRow(row) {
    if (!canBulkOperations) return;
    setSelectedRowIds((prev) =>
      prev.includes(row.id) ? prev.filter((id) => id !== row.id) : [...prev, row.id]
    );
  }

  function handleToggleAllRows() {
    if (!canBulkOperations) return;
    if (selectedRowIds.length && selectedRowIds.length === rows.length) {
      setSelectedRowIds([]);
      return;
    }
    setSelectedRowIds(rows.map((row) => row.id));
  }

  function buildInlineDraft(row) {
    return {
      department: row.department || '',
      designation: row.designation || ''
    };
  }

  function isInlineEditing(userId) {
    return inlineEditingIds.includes(userId);
  }

  function startInlineEdit(row) {
    if (!canInlineEditing) return;
    setInlineEditingIds((prev) => (prev.includes(row.id) ? prev : [...prev, row.id]));
    setInlineDraftById((prev) => ({ ...prev, [row.id]: buildInlineDraft(row) }));
  }

  function cancelInlineEdit(userId) {
    setInlineEditingIds((prev) => prev.filter((id) => id !== userId));
    setInlineDraftById((prev) => {
      const next = { ...prev };
      delete next[userId];
      return next;
    });
  }

  function updateInlineDraft(userId, key, value) {
    setInlineDraftById((prev) => ({
      ...prev,
      [userId]: {
        ...(prev[userId] || {}),
        [key]: value
      }
    }));
  }

  function getInlineChanges(row) {
    const draft = inlineDraftById[row.id];
    if (!draft) return {};
    const changes = {};
    if ((draft.department || '').trim() !== (row.department || '').trim()) {
      changes.department = draft.department.trim() || null;
    }
    if ((draft.designation || '').trim() !== (row.designation || '').trim()) {
      changes.designation = draft.designation.trim() || null;
    }
    return changes;
  }

  async function saveInlineEdit(row) {
    if (!canInlineEditing) return;
    const payload = getInlineChanges(row);
    if (!Object.keys(payload).length) {
      cancelInlineEdit(row.id);
      return;
    }
    const reasonRaw = window.prompt('Optional reason for profile update:', '');
    if (reasonRaw && reasonRaw.trim()) {
      payload.change_reason = reasonRaw.trim();
    }
    setInlineSavingIds((prev) => (prev.includes(row.id) ? prev : [...prev, row.id]));
    try {
      await updateUserProfile(row.id, payload);
      pushToast({
        title: 'User updated',
        description: `${row.full_name} profile fields saved.`,
        variant: 'success'
      });
      cancelInlineEdit(row.id);
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to update user profile';
      pushToast({ title: 'Inline update failed', description: String(detail), variant: 'error' });
    } finally {
      setInlineSavingIds((prev) => prev.filter((id) => id !== row.id));
    }
  }

  async function handleBulkStatus(isActive) {
    if (!canBulkOperations) return;
    if (!selectedRowIds.length) return;
    const reason = window.prompt('Reason is required for bulk status change:');
    if (!reason || !reason.trim()) return;
    try {
      const result = await bulkUpdateStatus(selectedRowIds, isActive, reason.trim());
      refreshUsers();
      pushToast({
        title: 'Bulk status processed',
        description: `Updated ${result.updated_count || 0}, failed ${result.failed_count || 0}.`,
        variant: result.failed_count ? 'warning' : 'success'
      });
      setSelectedRowIds([]);
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Bulk status update failed';
      pushToast({ title: 'Bulk update failed', description: String(detail), variant: 'error' });
    }
  }

  async function handleBulkExtensionApply() {
    if (!canBulkOperations) return;
    if (!selectedRows.length) return;
    const reason = window.prompt('Reason is required for bulk permission update:');
    if (!reason || !reason.trim()) return;
    const updates = selectedRows.map((row) => {
      const current = Array.isArray(row.extended_roles) ? row.extended_roles : [];
      const next =
        bulkMode === 'add'
          ? Array.from(new Set([...current, bulkExtension]))
          : current.filter((item) => item !== bulkExtension);
      return {
        user_id: row.id,
        extended_roles: next,
        role_scope: getMergedUserById(row.id)?.role_scope || {}
      };
    });
    try {
      const result = await bulkUpdateExtensions(updates, reason.trim());
      refreshUsers();
      pushToast({
        title: 'Bulk permission update processed',
        description: `Updated ${result.updated_count || 0}, failed ${result.failed_count || 0}.`,
        variant: result.failed_count ? 'warning' : 'success'
      });
      setSelectedRowIds([]);
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Bulk permission update failed';
      pushToast({ title: 'Bulk update failed', description: String(detail), variant: 'error' });
    }
  }

  async function handleExport() {
    if (!canImportExport) {
      pushToast({
        title: 'Export unavailable',
        description: 'Import/export capability is disabled for this workspace.',
        variant: 'warning'
      });
      return;
    }
    try {
      await exportCsv();
      pushToast({ title: 'Export ready', description: 'CSV export downloaded.', variant: 'success' });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'CSV export failed';
      pushToast({ title: 'Export failed', description: String(detail), variant: 'error' });
    }
  }

  function buildPresetQueryPayload() {
    return {
      q: queryState.q || undefined,
      role: queryState.role || undefined,
      status: queryState.status || undefined,
      admin_type: queryState.adminType || undefined,
      extension: queryState.extension || undefined,
      department: queryState.department || undefined,
      sort_by: queryState.sortBy || 'updated_at',
      sort_dir: queryState.sortDir === 'asc' ? 'asc' : 'desc',
      limit: PAGE_SIZES.includes(queryState.limit) ? queryState.limit : 25
    };
  }

  function applyPresetToParams(preset) {
    const query = preset?.query || {};
    updateParams({
      q: query.q || '',
      role: query.role || '',
      status: query.status || '',
      admin_type: query.admin_type || '',
      extension: query.extension || '',
      department: query.department || '',
      sort_by: query.sort_by || 'updated_at',
      sort_dir: query.sort_dir === 'asc' ? 'asc' : 'desc',
      limit: String(query.limit || 25),
      page: '1',
      preset: preset?.id || ''
    });
  }

  function handlePresetSelect(value) {
    updateParams({ preset: value || '' });
  }

  function handleApplyPreset() {
    if (!selectedPreset) return;
    applyPresetToParams(selectedPreset);
  }

  async function handleSavePreset() {
    const name = window.prompt('Preset name:');
    if (!name || !name.trim()) return;
    try {
      const created = await createFilterPreset({
        name: name.trim(),
        query: buildPresetQueryPayload()
      });
      if (!created?.id) return;
      pushToast({ title: 'Preset saved', description: `${created.name} is now available.`, variant: 'success' });
      updateParams({ preset: created.id });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to save preset';
      pushToast({ title: 'Preset save failed', description: String(detail), variant: 'error' });
    }
  }

  async function handleUpdatePreset() {
    if (!selectedPreset?.id) return;
    try {
      await updateFilterPreset(selectedPreset.id, { query: buildPresetQueryPayload() });
      pushToast({ title: 'Preset updated', description: `${selectedPreset.name} now matches current filters.`, variant: 'success' });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to update preset';
      pushToast({ title: 'Preset update failed', description: String(detail), variant: 'error' });
    }
  }

  async function handleRenamePreset() {
    if (!selectedPreset?.id) return;
    const name = window.prompt('Rename preset:', selectedPreset.name || '');
    if (!name || !name.trim()) return;
    try {
      const updated = await updateFilterPreset(selectedPreset.id, { name: name.trim() });
      pushToast({
        title: 'Preset renamed',
        description: `${updated?.name || selectedPreset.name} updated successfully.`,
        variant: 'success'
      });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to rename preset';
      pushToast({ title: 'Preset rename failed', description: String(detail), variant: 'error' });
    }
  }

  async function handleDeletePreset() {
    if (!selectedPreset?.id) return;
    const confirmed = window.confirm(`Delete preset "${selectedPreset.name}"?`);
    if (!confirmed) return;
    try {
      await deleteFilterPreset(selectedPreset.id);
      pushToast({ title: 'Preset deleted', description: 'Saved filter preset removed.', variant: 'success' });
      updateParams({ preset: '' });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to delete preset';
      pushToast({ title: 'Preset delete failed', description: String(detail), variant: 'error' });
    }
  }

  const columns = useMemo(
    () => [
      {
        key: 'full_name',
        label: 'Name',
        priority: 'high',
        render: (row) => <UserIdentityLabel row={row} />
      },
      { key: 'email', label: 'Email', priority: 'medium' },
      {
        key: 'department',
        label: 'Department',
        priority: 'medium',
        render: (row) =>
          canInlineEditing && isInlineEditing(row.id) ? (
            <input
              type="text"
              className="input w-full min-w-[150px]"
              value={inlineDraftById[row.id]?.department || ''}
              onChange={(event) => updateInlineDraft(row.id, 'department', event.target.value)}
              disabled={inlineSavingIds.includes(row.id)}
            />
          ) : (
            row.department || '-'
          )
      },
      {
        key: 'designation',
        label: 'Designation',
        priority: 'low',
        render: (row) =>
          canInlineEditing && isInlineEditing(row.id) ? (
            <input
              type="text"
              className="input w-full min-w-[150px]"
              value={inlineDraftById[row.id]?.designation || ''}
              onChange={(event) => updateInlineDraft(row.id, 'designation', event.target.value)}
              disabled={inlineSavingIds.includes(row.id)}
            />
          ) : (
            row.designation || '-'
          )
      },
      {
        key: 'role',
        label: 'Role',
        priority: 'medium',
        render: (row) => (
          <div className="space-y-1">
            <span className="rounded-full border border-slate-200 bg-slate-100 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
              {formatRoleLabel(row.role)}
            </span>
            {row.admin_type ? (
              <p className="text-xs text-slate-500 dark:text-slate-400">{formatRoleLabel(row.admin_type)}</p>
            ) : null}
          </div>
        )
      },
      {
        key: 'extended_roles',
        label: 'Extensions',
        priority: 'medium',
        render: (row) => (row.extended_roles?.length ? row.extended_roles.map(formatRoleLabel).join(', ') : '-')
      },
      {
        key: 'last_active_at',
        label: 'Last Active',
        priority: 'low',
        render: (row) => formatDate(row.last_active_at)
      },
      {
        key: 'governance',
        label: 'Governance',
        priority: 'low',
        render: (row) => (
          <div className="space-y-1 text-xs">
            <p className="text-slate-600 dark:text-slate-300">
              Perm: {formatAuditMeta(row.last_permission_change_by, row.last_permission_change_at)}
            </p>
            <p className="text-slate-600 dark:text-slate-300">
              Status: {formatAuditMeta(row.last_status_change_by, row.last_status_change_at)}
            </p>
          </div>
        )
      },
      {
        key: 'is_active',
        label: 'Status',
        priority: 'high',
        render: (row) => (
          <span
            className={`rounded-full border px-2 py-1 text-[11px] font-semibold uppercase tracking-wide ${
              row.is_active === false
                ? 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/30 dark:text-rose-300'
                : 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/30 dark:text-emerald-300'
            }`}
          >
            {row.is_active === false ? 'Inactive' : 'Active'}
          </span>
        )
      }
    ],
    [canInlineEditing, inlineDraftById, inlineEditingIds, inlineSavingIds]
  );

  const rowActions = useMemo(
    () => {
      const actions = [];
      if (canInlineEditing) {
        actions.push(
          {
            key: 'quick-edit',
            label: (row) => (isInlineEditing(row.id) ? 'Cancel Edit' : 'Quick Edit'),
            onClick: (row) => (isInlineEditing(row.id) ? cancelInlineEdit(row.id) : startInlineEdit(row))
          },
          {
            key: 'save-inline',
            label: (row) => (inlineSavingIds.includes(row.id) ? 'Saving...' : 'Save Inline'),
            hidden: (row) => !isInlineEditing(row.id),
            disabled: (row) => inlineSavingIds.includes(row.id) || !Object.keys(getInlineChanges(row)).length,
            onClick: (row) => saveInlineEdit(row),
            className: 'min-w-[96px]'
          }
        );
      }
      actions.push({
        key: 'open-risk',
        label: 'Open Risk',
        onClick: (row) => openUser(row.id, 'risk'),
        className: 'min-w-[88px]'
      });
      return actions;
    },
    [canInlineEditing, inlineDraftById, inlineEditingIds, inlineSavingIds, openUser]
  );

  const activeCount =
    filterOptions.status?.find((item) => item.value === 'active')?.count ?? rows.filter((item) => item.is_active !== false).length;
  const adminCount =
    filterOptions.roles?.find((item) => item.value === 'admin')?.count ?? rows.filter((item) => item.role === 'admin').length;

  const appliedFilters = [
    queryState.role ? { key: 'role', label: `Role: ${queryState.role}` } : null,
    queryState.status ? { key: 'status', label: `Status: ${queryState.status}` } : null,
    queryState.adminType ? { key: 'admin_type', label: `Admin Type: ${queryState.adminType}` } : null,
    queryState.extension ? { key: 'extension', label: `Extension: ${queryState.extension}` } : null,
    queryState.department ? { key: 'department', label: `Department: ${queryState.department}` } : null
  ].filter(Boolean);

  const mobileCardRender = (row, { renderRowActions }) => {
    const editing = canInlineEditing && isInlineEditing(row.id);
    const savingInline = inlineSavingIds.includes(row.id);
    return (
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <UserIdentityLabel row={row} />
            <p className="text-xs text-slate-500 dark:text-slate-400">{row.email || '-'}</p>
          </div>
          <div className="flex items-center gap-2">
            {canBulkOperations ? (
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                checked={selectedRowIds.includes(row.id)}
                onChange={() => handleToggleRow(row)}
                aria-label={`Select ${row.full_name || 'user'}`}
              />
            ) : null}
            <span
              className={`rounded-full border px-2 py-1 text-[11px] font-semibold uppercase tracking-wide ${
                row.is_active === false
                  ? 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/30 dark:text-rose-300'
                  : 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/30 dark:text-emerald-300'
              }`}
            >
              {row.is_active === false ? 'Inactive' : 'Active'}
            </span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Role</p>
            <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">{formatRoleLabel(row.role)}</p>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Last Active</p>
            <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">{formatDate(row.last_active_at)}</p>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Department</p>
            {editing ? (
              <input
                type="text"
                className="input mt-1 w-full"
                value={inlineDraftById[row.id]?.department || ''}
                onChange={(event) => updateInlineDraft(row.id, 'department', event.target.value)}
                disabled={savingInline}
              />
            ) : (
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">{row.department || '-'}</p>
            )}
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Designation</p>
            {editing ? (
              <input
                type="text"
                className="input mt-1 w-full"
                value={inlineDraftById[row.id]?.designation || ''}
                onChange={(event) => updateInlineDraft(row.id, 'designation', event.target.value)}
                disabled={savingInline}
              />
            ) : (
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">{row.designation || '-'}</p>
            )}
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Perm Last Changed</p>
            <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">
              {formatAuditMeta(row.last_permission_change_by, row.last_permission_change_at)}
            </p>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Status Last Changed</p>
            <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">
              {formatAuditMeta(row.last_status_change_by, row.last_status_change_at)}
            </p>
          </div>
        </div>
        {renderRowActions(row)}
      </div>
    );
  };

  return (
    <div className={cn('page-fade', effectiveDensity === 'compact' ? 'space-y-3' : 'space-y-4')}>
      <Card className="space-y-4">
        <div>
          <h1 className="text-2xl font-semibold">Admin Users Workspace</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Unified search, filtering, bulk actions, and audited user management.
          </p>
        </div>
        {!canWorkspace ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
            {capabilities.rollout_reason || 'Users workspace is disabled by feature flag.'}{' '}
            {capabilities.rollout_stage ? `Current rollout stage: ${String(capabilities.rollout_stage).replace(/_/g, ' ')}.` : ''}
          </div>
        ) : null}
      </Card>

      {canWorkspace ? (
      <Card className="space-y-4">
        <div className="grid w-full grid-cols-2 gap-2 sm:flex sm:w-auto sm:flex-wrap">
          <button type="button" className="btn-secondary !justify-center sm:!justify-start" onClick={() => openModal('create')}>
            <Plus size={14} />
            Add User
          </button>
          {canInvitations ? (
            <button type="button" className="btn-secondary !justify-center sm:!justify-start" onClick={() => openModal('invite')}>
              <UserPlus size={14} />
              Invite User
            </button>
          ) : null}
          {canImportExport ? (
            <>
              <button
                type="button"
                className="btn-secondary !justify-center sm:!justify-start"
                onClick={() => {
                  setImportPreview(null);
                  openModal('import');
                }}
              >
                <Upload size={14} />
                Import
              </button>
              <button type="button" className="btn-secondary !justify-center sm:!justify-start" onClick={handleExport}>
                <Download size={14} />
                Export
              </button>
            </>
          ) : null}
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Kpi label="Total Users" value={meta.total} icon={<Users size={15} />} />
          <Kpi label="Active Users" value={activeCount} />
          <Kpi label="Admins" value={adminCount} />
          <Kpi label="Selected" value={selectedRowIds.length} />
        </div>
      </Card>
      ) : null}

      {canWorkspace ? (
      <Card className="space-y-3">
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-[minmax(260px,1fr)_auto_auto_auto_auto_auto] xl:items-end">
          <div className="min-w-[220px]">
            <FormInput
              label="Global Search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Search by user name or email"
            />
          </div>
          <FormInput as="select" label="Sort" value={queryState.sortBy} onChange={(event) => handleSort(event.target.value)}>
            {SORT_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </FormInput>
          <FormInput as="select" label="Direction" value={queryState.sortDir} onChange={(event) => updateParams({ sort_dir: event.target.value, page: '1' })}>
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </FormInput>
          {canCompactDensity ? (
            <FormInput as="select" label="Density" value={queryState.density} onChange={(event) => updateParams({ density: event.target.value })}>
              {DENSITY_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </FormInput>
          ) : null}
          <button type="button" className="btn-secondary" onClick={() => setFiltersOpen((prev) => !prev)}>
            <Filter size={14} />
            {filtersOpen ? 'Hide Filters' : 'Show Filters'}
          </button>
          <button type="button" className="btn-secondary" onClick={() => updateParams({ q: '', role: '', status: '', admin_type: '', extension: '', department: '', page: '1', preset: '' })}>
            <X size={14} />
            Clear
          </button>
        </div>

        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-[minmax(260px,1fr)_auto_auto_auto_auto_auto] xl:items-end">
          <div className="min-w-[260px]">
            <FormInput
              as="select"
              label="Saved Filter Preset"
              value={queryState.preset}
              onChange={(event) => handlePresetSelect(event.target.value)}
            >
              <option value="">{filterPresetsLoading ? 'Loading presets...' : 'Select preset'}</option>
              {(filterPresets || []).map((preset) => (
                <option key={preset.id} value={preset.id}>
                  {preset.name}
                </option>
              ))}
            </FormInput>
          </div>
          <button
            type="button"
            className="btn-secondary"
            onClick={handleApplyPreset}
            disabled={!selectedPreset || savingFilterPreset}
            title="Apply selected preset"
          >
            <Bookmark size={14} />
            Apply
          </button>
          <button type="button" className="btn-secondary" onClick={handleSavePreset} disabled={savingFilterPreset}>
            <BookmarkPlus size={14} />
            Save New
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={handleUpdatePreset}
            disabled={!selectedPreset || savingFilterPreset}
            title="Overwrite selected preset with current filters"
          >
            <RefreshCw size={14} />
            Update
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={handleRenamePreset}
            disabled={!selectedPreset || savingFilterPreset}
            title="Rename selected preset"
          >
            <Edit3 size={14} />
            Rename
          </button>
          <button
            type="button"
            className="btn-secondary !border-rose-300 !text-rose-700 dark:!border-rose-900/50 dark:!text-rose-300"
            onClick={handleDeletePreset}
            disabled={!selectedPreset || savingFilterPreset}
            title="Delete selected preset"
          >
            <Trash2 size={14} />
            Delete
          </button>
        </div>

        {filtersOpen ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <FormInput as="select" label="Role" value={queryState.role} onChange={(event) => handleFilterChange('role', event.target.value)}>
              <option value="">All</option>
              {(filterOptions.roles || []).map((item) => <option key={item.value} value={item.value}>{item.value} ({item.count})</option>)}
            </FormInput>
            <FormInput as="select" label="Status" value={queryState.status} onChange={(event) => handleFilterChange('status', event.target.value)}>
              <option value="">All</option>
              {(filterOptions.status || []).map((item) => <option key={item.value} value={item.value}>{item.value} ({item.count})</option>)}
            </FormInput>
            <FormInput as="select" label="Admin Type" value={queryState.adminType} onChange={(event) => handleFilterChange('admin_type', event.target.value)}>
              <option value="">All</option>
              {(filterOptions.admin_types || []).map((item) => <option key={item.value} value={item.value}>{item.value} ({item.count})</option>)}
            </FormInput>
            <FormInput as="select" label="Extension" value={queryState.extension} onChange={(event) => handleFilterChange('extension', event.target.value)}>
              <option value="">All</option>
              {(filterOptions.extensions || []).map((item) => <option key={item.value} value={item.value}>{item.value} ({item.count})</option>)}
            </FormInput>
            <FormInput as="select" label="Department" value={queryState.department} onChange={(event) => handleFilterChange('department', event.target.value)}>
              <option value="">All</option>
              {(filterOptions.departments || []).map((item) => <option key={item.value} value={item.value}>{item.value} ({item.count})</option>)}
            </FormInput>
          </div>
        ) : null}

        {appliedFilters.length ? (
          <div className="flex flex-wrap gap-2">
            {appliedFilters.map((item) => (
              <button key={item.key} type="button" className="btn-secondary !py-1 !text-xs" onClick={() => updateParams({ [item.key]: '', page: '1' })}>
                {item.label}
                <X size={12} />
              </button>
            ))}
          </div>
        ) : null}
      </Card>
      ) : null}

      {canBulkOperations && selectedRowIds.length ? (
        <Card className="sticky bottom-2 z-20 space-y-2 border-brand-200 bg-white/95 backdrop-blur dark:border-brand-900/40 dark:bg-slate-900/95 md:static md:backdrop-blur-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-brand-700 dark:text-brand-300">
              {selectedRowIds.length} user(s) selected
            </p>
            <button type="button" className="btn-secondary" onClick={() => handleBulkStatus(true)}>Activate</button>
            <button type="button" className="btn-secondary" onClick={() => handleBulkStatus(false)}>Deactivate</button>
            <FormInput as="select" label="Extension" value={bulkExtension} onChange={(event) => setBulkExtension(event.target.value)}>
              {BULK_EXTENSIONS.map((item) => <option key={item} value={item}>{formatRoleLabel(item)}</option>)}
            </FormInput>
            <FormInput as="select" label="Mode" value={bulkMode} onChange={(event) => setBulkMode(event.target.value)}>
              <option value="add">Add</option>
              <option value="remove">Remove</option>
            </FormInput>
            <button type="button" className="btn-secondary self-end" onClick={handleBulkExtensionApply}>Apply Extension</button>
            <button type="button" className="btn-secondary self-end" onClick={() => setSelectedRowIds([])}>Clear Selection</button>
          </div>
        </Card>
      ) : null}

      {canWorkspace ? (
      <Card className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Search size={14} className="text-slate-500" />
            <p className="text-sm text-slate-600 dark:text-slate-300">
              {loading ? 'Loading users...' : `${meta.total} users found`}
            </p>
            {filtersLoading ? <span className="text-xs text-slate-400">(updating filters)</span> : null}
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Tip: click a row or press Enter to open the user workspace.
          </p>
          <button type="button" className="btn-secondary" onClick={refreshUsers}>
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>

        {error ? <p className="text-sm text-rose-600">{error}</p> : null}

        <Table
          columns={columns}
          data={rows}
          rowActions={rowActions}
          selectable={canBulkOperations}
          selectedRowIds={selectedRowIds}
          onToggleRow={handleToggleRow}
          onToggleAllRows={handleToggleAllRows}
          responsive={canResponsiveWorkflows}
          density={effectiveDensity}
          mobileCardRender={mobileCardRender}
          rowClassName={(row) =>
            row.id === selectedUserId
              ? 'bg-brand-50/70 ring-1 ring-inset ring-brand-200 dark:bg-brand-950/20 dark:ring-brand-800/60'
              : ''
          }
          mobileCardClassName={(row) =>
            row.id === selectedUserId
              ? 'border-brand-300 ring-2 ring-brand-200 dark:border-brand-700 dark:ring-brand-900/70'
              : ''
          }
          onRowClick={(row) => openUser(row.id)}
          rowAriaLabel={(row) => `Open details for ${row.full_name || 'user'}`}
          virtualization={{
            enabled: canTableVirtualization,
            threshold: 120,
            rowHeight: effectiveDensity === 'compact' ? 44 : 56,
            viewportHeight: 560,
            overscan: 8,
          }}
        />

        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Page {meta.page} of {Math.max(meta.total_pages || 1, 1)}
          </p>
          <div className="flex items-center gap-2">
            <button type="button" className="btn-secondary" disabled={queryState.page <= 1} onClick={() => updateParams({ page: String(Math.max(queryState.page - 1, 1)) })}>
              Previous
            </button>
            <button type="button" className="btn-secondary" disabled={queryState.page >= (meta.total_pages || 1)} onClick={() => updateParams({ page: String(queryState.page + 1) })}>
              Next
            </button>
            <FormInput as="select" label="Page Size" value={String(queryState.limit)} onChange={(event) => updateParams({ limit: event.target.value, page: '1' })}>
              {PAGE_SIZES.map((size) => <option key={size} value={String(size)}>{size}</option>)}
            </FormInput>
          </div>
        </div>
      </Card>
      ) : null}

      {canWorkspace ? (
        <Card className="space-y-3">
          <button
            type="button"
            className="flex w-full items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-left dark:border-slate-700 dark:bg-slate-900"
            onClick={() => setDiagnosticsOpen((prev) => !prev)}
            aria-expanded={diagnosticsOpen}
          >
            <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">Workspace Diagnostics</span>
            <span className="text-xs text-slate-500 dark:text-slate-400">{diagnosticsOpen ? 'Hide' : 'Show'}</span>
          </button>
          {diagnosticsOpen ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">Pagination & API Latency</h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Live diagnostics from users admin telemetry ({adminDashboard.window_minutes}m window).
                  </p>
                </div>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => void loadAdminDashboard({ silent: false })}
                  disabled={adminDashboardLoading}
                >
                  <RefreshCw size={14} />
                  {adminDashboardLoading ? 'Refreshing...' : 'Refresh Dashboard'}
                </button>
              </div>

              {adminDashboardError ? (
                <p className="text-sm text-amber-700 dark:text-amber-300">{adminDashboardError}</p>
              ) : null}

              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <Kpi label="Requests" value={adminDashboard.latency.request_count} />
                <Kpi label="Error Rate" value={formatPercent(adminDashboard.latency.error_rate_pct)} />
                <Kpi label="P95 Latency" value={formatMilliseconds(adminDashboard.latency.p95_duration_ms)} />
                <Kpi label="P99 Latency" value={formatMilliseconds(adminDashboard.latency.p99_duration_ms)} />
              </div>

              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <Kpi label="Avg Page" value={adminDashboard.pagination.avg_page} />
                <Kpi label="Avg Page Size" value={adminDashboard.pagination.avg_limit} />
                <Kpi label="Empty Page Rate" value={formatPercent(adminDashboard.pagination.empty_page_rate_pct)} />
                <Kpi label="Deep Page Rate (>=5)" value={formatPercent(adminDashboard.pagination.deep_page_rate_pct)} />
              </div>

              {Array.isArray(adminDashboard.alerts) && adminDashboard.alerts.length ? (
                <Card className="space-y-2">
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Users Alert State</p>
                  <div className="space-y-2">
                    {adminDashboard.alerts.map((alert) => (
                      <div key={alert.code} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-900">
                        <p className="font-semibold text-slate-800 dark:text-slate-100">
                          {alert.code} ({String(alert.level || 'warning').toUpperCase()})
                        </p>
                        <p className="text-slate-500 dark:text-slate-400">{alert.message}</p>
                        <p className="text-slate-500 dark:text-slate-400">
                          Threshold: {alert.current_value} {alert.comparison || '>'} {alert.threshold_value}
                        </p>
                      </div>
                    ))}
                  </div>
                </Card>
              ) : null}

              <div className="grid gap-3 xl:grid-cols-2">
                <Card className="space-y-2">
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Top Page Sizes</p>
                  {(adminDashboard.pagination.top_page_sizes || []).length ? (
                    <div className="flex flex-wrap gap-2">
                      {adminDashboard.pagination.top_page_sizes.map((item) => (
                        <span
                          key={`${item.page_size}-${item.count}`}
                          className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                        >
                          {item.page_size}: {item.count}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-slate-500 dark:text-slate-400">No page-size telemetry yet.</p>
                  )}
                </Card>
                <Card className="space-y-2">
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Latency Buckets</p>
                  {(adminDashboard.latency.buckets || []).length ? (
                    <div className="max-h-48 overflow-auto rounded-xl border border-slate-200 dark:border-slate-700">
                      <table className="min-w-full text-xs">
                        <thead className="bg-slate-50 dark:bg-slate-900/70">
                          <tr>
                            <th className="px-2 py-2 text-left">Time</th>
                            <th className="px-2 py-2 text-right">Req</th>
                            <th className="px-2 py-2 text-right">Err</th>
                            <th className="px-2 py-2 text-right">Avg</th>
                            <th className="px-2 py-2 text-right">P95</th>
                          </tr>
                        </thead>
                        <tbody>
                          {[...(adminDashboard.latency.buckets || [])].slice(-12).map((bucket, index) => (
                            <tr key={`${bucket.bucket_start || 'bucket'}-${index}`} className="border-t border-slate-200 dark:border-slate-700">
                              <td className="px-2 py-1.5 text-left">{formatBucketTime(bucket.bucket_start)}</td>
                              <td className="px-2 py-1.5 text-right">{bucket.requests ?? 0}</td>
                              <td className="px-2 py-1.5 text-right">{bucket.errors ?? 0}</td>
                              <td className="px-2 py-1.5 text-right">{formatMilliseconds(bucket.avg_duration_ms)}</td>
                              <td className="px-2 py-1.5 text-right">{formatMilliseconds(bucket.p95_duration_ms)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-sm text-slate-500 dark:text-slate-400">No bucketed latency telemetry yet.</p>
                  )}
                </Card>
              </div>
            </div>
          ) : null}
        </Card>
      ) : null}

      <UserCreateModal
        open={overlayState.type === 'create'}
        topOffsetPx={USERS_OVERLAY_TOP_OFFSET_PX}
        onClose={closeModal}
        loading={creatingUser}
        sections={sections}
        clubs={clubs}
        onSubmit={async (payload) => {
          await createDirectUser(payload);
          refreshUsers();
          closeModal();
        }}
      />

      {canInvitations ? (
        <UserInviteModal
          open={overlayState.type === 'invite'}
          topOffsetPx={USERS_OVERLAY_TOP_OFFSET_PX}
          onClose={closeModal}
          loading={invitingUser}
          sections={sections}
          clubs={clubs}
          onSubmit={async (payload) => {
            await inviteUser(payload);
            refreshUsers();
            closeModal();
          }}
        />
      ) : null}

      {canImportExport ? (
        <UserImportModal
          open={overlayState.type === 'import'}
          topOffsetPx={USERS_OVERLAY_TOP_OFFSET_PX}
          onClose={() => {
            closeModal();
            setImportPreview(null);
          }}
          previewImport={previewImport}
          importPreview={importPreview}
          commitImport={commitImport}
          importing={importing}
          onCommitted={refreshUsers}
        />
      ) : null}

      <UserDetailOverlay
        key={selectedUser?.id || 'no-user-selected'}
        open={overlayState.type === 'drawer'}
        topOffsetPx={USERS_OVERLAY_TOP_OFFSET_PX}
        batches={batches}
        clubs={clubs}
        close={closeUser}
        departments={departments}
        faculties={faculties}
        getEffectiveExtensions={getEffectiveExtensions}
        getEffectiveScope={getEffectiveScope}
        programs={programs}
        savePermissions={savePermissions}
        resetPermissionDraft={resetPermissionDraft}
        savingIds={savingIds}
        sections={sections}
        selectedTab={selectedTab}
        selectedUser={selectedUser}
        semesters={semesters}
        setSelectedTab={setActiveTab}
        specializations={specializations}
        toggleExtension={toggleExtension}
        updateClassCoordinatorScope={updateClassCoordinatorScope}
        updateClubPresidentScope={updateClubPresidentScope}
        updateClassRepresentativeScope={updateClassRepresentativeScope}
        activityItems={activityByUserId[selectedUserId] || []}
        activityLoading={Boolean(activityLoadingByUserId[selectedUserId])}
        refreshActivity={() => loadUserActivity(selectedUserId)}
        permissionTemplates={permissionTemplates}
        applyPermissionTemplate={applyPermissionTemplate}
        permissionTemplateSaving={permissionTemplateSaving}
        createPermissionTemplate={async (payload) => {
          const created = await createPermissionTemplate(payload);
          pushToast({
            title: 'Template created',
            description: `${created?.name || 'Permission template'} is ready to use.`,
            variant: 'success'
          });
          return created;
        }}
        updatePermissionTemplate={async (templateId, payload) => {
          const updated = await updatePermissionTemplate(templateId, payload);
          pushToast({
            title: 'Template updated',
            description: `${updated?.name || 'Permission template'} saved successfully.`,
            variant: 'success'
          });
          return updated;
        }}
        deletePermissionTemplate={async (templateId) => {
          await deletePermissionTemplate(templateId);
          pushToast({
            title: 'Template deleted',
            description: 'Permission template removed successfully.',
            variant: 'success'
          });
        }}
        onStatusChange={async (isActive, reason) => {
          if (!selectedUserId) return;
          await updateUserStatus(selectedUserId, isActive, reason);
          refreshUsers();
        }}
        onSaveDetails={async (payload) => {
          if (!selectedUserId) return;
          await updateUserProfile(selectedUserId, payload);
          refreshUsers();
          pushToast({ title: 'User details updated', description: 'Profile changes saved.', variant: 'success' });
        }}
        detailsSaving={Boolean(selectedUserId && updatingProfileIds.includes(selectedUserId))}
        capabilities={capabilities}
      />
    </div>
  );
}

function Kpi({ label, value, icon = null }) {
  const isNumericValue = typeof value === 'number' && Number.isFinite(value);
  const displayValue = isNumericValue ? Number(value).toLocaleString() : String(value ?? '-');
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-3 py-3 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
        {icon}
      </div>
      <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-100">{displayValue}</p>
    </div>
  );
}

function UserIdentityLabel({ row }) {
  const avatarSrc = useAuthorizedImage(row.avatar_url, row.avatar_updated_at);
  const initials = getNameInitials(row.full_name);
  return (
    <div className="inline-flex items-center gap-2 text-left font-medium text-slate-800 dark:text-slate-100">
      {avatarSrc ? (
        <img
          src={avatarSrc}
          alt={`${row.full_name || 'User'} profile`}
          className="h-7 w-7 rounded-full border border-slate-200 object-cover dark:border-slate-700"
        />
      ) : (
        <span className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-slate-200 bg-slate-100 text-[10px] font-semibold uppercase text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
          {initials}
        </span>
      )}
      <span>{row.full_name}</span>
    </div>
  );
}

function UserCreateModal({ open, onClose, onSubmit, loading, sections = [], clubs = [], topOffsetPx = 68 }) {
  return (
    <UserLifecycleWizardModal
      mode="create"
      open={open}
      onClose={onClose}
      onSubmit={onSubmit}
      loading={loading}
      sections={sections}
      clubs={clubs}
      topOffsetPx={topOffsetPx}
    />
  );
}

function UserInviteModal({ open, onClose, onSubmit, loading, sections = [], clubs = [], topOffsetPx = 68 }) {
  return (
    <UserLifecycleWizardModal
      mode="invite"
      open={open}
      onClose={onClose}
      onSubmit={onSubmit}
      loading={loading}
      sections={sections}
      clubs={clubs}
      topOffsetPx={topOffsetPx}
    />
  );
}

function UserLifecycleWizardModal({ mode, open, onClose, onSubmit, loading, sections = [], clubs = [], topOffsetPx = 68 }) {
  const [step, setStep] = useState(0);
  const [errorMessage, setErrorMessage] = useState('');
  const [form, setForm] = useState(() => ({
    full_name: '',
    email: '',
    password: '',
    expires_in_days: 7,
    role: 'teacher',
    admin_type: '',
    extended_roles: [],
    role_scope: {}
  }));

  const steps = [
    'Identity',
    'Role',
    'Extensions',
    'Scope',
    'Review'
  ];
  const availableExtensions = EXTENSIONS_BY_ROLE[form.role] || [];
  const selectedClassScope = form.role_scope?.class_coordinator || {};
  const selectedClubScope = form.role_scope?.club_president || {};
  const selectedRepresentativeScope = form.role_scope?.class_representative || {};
  const selectedSection = sections.find((section) => section.id === selectedClassScope.class_id);
  const selectedRepresentativeSection = sections.find((section) => section.id === selectedRepresentativeScope.class_id);
  const selectedClub = clubs.find((club) => club.id === selectedClubScope.club_id);

  useEffect(() => {
    if (!open) return;
    setStep(0);
    setErrorMessage('');
    setForm({
      full_name: '',
      email: '',
      password: '',
      expires_in_days: 7,
      role: 'teacher',
      admin_type: '',
      extended_roles: [],
      role_scope: {}
    });
  }, [open]);

  useEffect(() => {
    if (form.role === 'admin') {
      setForm((prev) => ({ ...prev, extended_roles: [], role_scope: {} }));
      return;
    }
    setForm((prev) => {
      const nextExtensions = (prev.extended_roles || []).filter((item) => (EXTENSIONS_BY_ROLE[form.role] || []).includes(item));
      const nextScope = { ...(prev.role_scope || {}) };
      if (form.role === 'teacher') {
        delete nextScope.club_president;
        delete nextScope.class_representative;
        if (!nextExtensions.includes('class_coordinator')) {
          delete nextScope.class_coordinator;
        }
      }
      if (form.role === 'student') {
        delete nextScope.class_coordinator;
        if (!nextExtensions.includes('class_representative')) {
          delete nextScope.class_representative;
        }
        if (!nextExtensions.includes('club_president')) {
          delete nextScope.club_president;
        }
      }
      return { ...prev, extended_roles: nextExtensions, role_scope: nextScope };
    });
  }, [form.role]);

  if (!open) return null;

  function updateRoleScope(path, value) {
    setForm((prev) => {
      const next = { ...(prev.role_scope || {}) };
      if (path === 'class_coordinator.class_id') {
        if (!value) {
          delete next.class_coordinator;
        } else {
          next.class_coordinator = { ...(next.class_coordinator || {}), class_id: value };
        }
      }
      if (path === 'club_president.club_id') {
        if (!value) {
          delete next.club_president;
        } else {
          next.club_president = { ...(next.club_president || {}), club_id: value };
        }
      }
      if (path === 'class_representative.class_id') {
        if (!value) {
          delete next.class_representative;
        } else {
          next.class_representative = { ...(next.class_representative || {}), class_id: value };
        }
      }
      if (path === 'class_representative.seat') {
        next.class_representative = { ...(next.class_representative || {}), seat: value || null };
      }
      return { ...prev, role_scope: next };
    });
  }

  function toggleExtension(extension) {
    setForm((prev) => {
      const current = Array.isArray(prev.extended_roles) ? prev.extended_roles : [];
      const next = current.includes(extension)
        ? current.filter((item) => item !== extension)
        : [...current, extension];
      return { ...prev, extended_roles: next };
    });
  }

  function validateStep(currentStep) {
    if (currentStep === 0) {
      if (!form.full_name.trim()) return 'Full name is required.';
      if (!form.email.trim() || !String(form.email).includes('@')) return 'A valid email is required.';
      if (mode === 'create' && String(form.password || '').length < 8) return 'Password must be at least 8 characters.';
    }
    if (currentStep === 1 && form.role === 'admin' && !form.admin_type.trim()) {
      return 'Admin type is required for admin role.';
    }
    if (currentStep === 3) {
      if (form.role === 'teacher' && form.extended_roles.includes('class_coordinator') && !selectedClassScope.class_id) {
        return 'Class coordinator requires a section assignment.';
      }
      if (form.role === 'student' && form.extended_roles.includes('club_president') && !selectedClubScope.club_id) {
        return 'Club president requires a club assignment.';
      }
      if (form.role === 'student' && form.extended_roles.includes('class_representative')) {
        if (!selectedRepresentativeScope.class_id) {
          return 'Class representative requires a section assignment.';
        }
        if (!selectedRepresentativeScope.seat) {
          return 'Class representative requires a seat assignment.';
        }
      }
    }
    return '';
  }

  function goNext() {
    const nextError = validateStep(step);
    if (nextError) {
      setErrorMessage(nextError);
      return;
    }
    setErrorMessage('');
    setStep((prev) => Math.min(prev + 1, steps.length - 1));
  }

  function goBack() {
    setErrorMessage('');
    setStep((prev) => Math.max(prev - 1, 0));
  }

  async function handleSubmit() {
    const finalError = validateStep(step);
    if (finalError) {
      setErrorMessage(finalError);
      return;
    }
    const payload = {
      full_name: form.full_name.trim(),
      email: form.email.trim(),
      role: form.role,
      admin_type: form.role === 'admin' ? form.admin_type.trim() || undefined : undefined,
      extended_roles: form.extended_roles,
      role_scope: form.role_scope
    };
    if (mode === 'create') {
      payload.password = form.password;
    } else {
      payload.expires_in_days = Number(form.expires_in_days || 7);
    }
    await onSubmit(payload);
  }

  return (
    <ModalShell title={mode === 'create' ? 'Create User Wizard' : 'Invite User Wizard'} onClose={onClose} topOffsetPx={topOffsetPx}>
      <div className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {steps.map((label, index) => (
            <span
              key={label}
              className={cn(
                'rounded-full border px-2 py-1 text-xs',
                index === step
                  ? 'border-brand-300 bg-brand-50 text-brand-700 dark:border-brand-800/40 dark:bg-brand-950/20 dark:text-brand-300'
                  : 'border-slate-200 bg-slate-50 text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300'
              )}
            >
              {index + 1}. {label}
            </span>
          ))}
        </div>

        {step === 0 ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <FormInput label="Full Name" value={form.full_name} onChange={(event) => setForm((prev) => ({ ...prev, full_name: event.target.value }))} />
            <FormInput label="Email" value={form.email} onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))} />
            {mode === 'create' ? (
              <FormInput
                label="Password"
                type="password"
                value={form.password}
                onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
              />
            ) : (
              <FormInput
                label="Expires In (Days)"
                type="number"
                min="1"
                max="30"
                value={form.expires_in_days}
                onChange={(event) => setForm((prev) => ({ ...prev, expires_in_days: Number(event.target.value || 7) }))}
              />
            )}
          </div>
        ) : null}

        {step === 1 ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <FormInput as="select" label="Role" value={form.role} onChange={(event) => setForm((prev) => ({ ...prev, role: event.target.value }))}>
              <option value="teacher">Teacher</option>
              <option value="student">Student</option>
              <option value="admin">Admin</option>
            </FormInput>
            {form.role === 'admin' ? (
              <FormInput
                label="Admin Type"
                value={form.admin_type}
                onChange={(event) => setForm((prev) => ({ ...prev, admin_type: event.target.value }))}
                placeholder="admin / hod / dean"
              />
            ) : (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                Admin type is optional for non-admin roles and will be ignored.
              </div>
            )}
          </div>
        ) : null}

        {step === 2 ? (
          <div className="space-y-2">
            {!availableExtensions.length ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                This role has no extension upgrades.
              </div>
            ) : (
              <div className="grid gap-2 sm:grid-cols-2">
                {availableExtensions.map((extension) => (
                  <label key={extension} className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                      checked={form.extended_roles.includes(extension)}
                      onChange={() => toggleExtension(extension)}
                    />
                    <span>{formatRoleLabel(extension)}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        ) : null}

        {step === 3 ? (
          <div className="space-y-3">
            {form.role === 'teacher' && form.extended_roles.includes('class_coordinator') ? (
              <FormInput
                as="select"
                label="Class Coordinator Section"
                value={selectedClassScope.class_id || ''}
                onChange={(event) => updateRoleScope('class_coordinator.class_id', event.target.value || null)}
              >
                <option value="">Select Section</option>
                {sections.map((section) => (
                  <option key={section.id} value={section.id}>
                    {section.name}
                  </option>
                ))}
              </FormInput>
            ) : null}
            {form.role === 'student' && form.extended_roles.includes('club_president') ? (
              <FormInput
                as="select"
                label="Club President Club"
                value={selectedClubScope.club_id || ''}
                onChange={(event) => updateRoleScope('club_president.club_id', event.target.value || null)}
              >
                <option value="">Select Club</option>
                {clubs.map((club) => (
                  <option key={club.id} value={club.id}>
                    {club.name}
                  </option>
                ))}
              </FormInput>
            ) : null}
            {form.role === 'student' && form.extended_roles.includes('class_representative') ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <FormInput
                  as="select"
                  label="CR Section"
                  value={selectedRepresentativeScope.class_id || ''}
                  onChange={(event) => updateRoleScope('class_representative.class_id', event.target.value || null)}
                >
                  <option value="">Select Section</option>
                  {sections.map((section) => (
                    <option key={section.id} value={section.id}>
                      {section.name}
                    </option>
                  ))}
                </FormInput>
                <FormInput
                  as="select"
                  label="CR Seat"
                  value={selectedRepresentativeScope.seat || ''}
                  onChange={(event) => updateRoleScope('class_representative.seat', event.target.value || null)}
                >
                  <option value="">Select Seat</option>
                  <option value="cr_1">CR-1</option>
                  <option value="cr_2">CR-2</option>
                </FormInput>
              </div>
            ) : null}
            {!((form.role === 'teacher' && form.extended_roles.includes('class_coordinator')) || (form.role === 'student' && (form.extended_roles.includes('club_president') || form.extended_roles.includes('class_representative')))) ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                No scope assignment is required for the selected role/extensions.
              </div>
            ) : null}
          </div>
        ) : null}

        {step === 4 ? (
          <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm dark:border-slate-700 dark:bg-slate-900">
            <p><strong>Name:</strong> {form.full_name || '-'}</p>
            <p><strong>Email:</strong> {form.email || '-'}</p>
            <p><strong>Role:</strong> {formatRoleLabel(form.role)}</p>
            <p><strong>Admin Type:</strong> {form.role === 'admin' ? form.admin_type || '-' : '-'}</p>
            <p><strong>Extensions:</strong> {form.extended_roles.length ? form.extended_roles.map(formatRoleLabel).join(', ') : 'None'}</p>
            <p>
              <strong>Scope:</strong>{' '}
              {selectedSection?.name
                || (selectedRepresentativeSection?.name ? `${selectedRepresentativeSection.name} (${String(selectedRepresentativeScope.seat || '').replace('_', '-').toUpperCase() || 'Seat'})` : null)
                || selectedClub?.name
                || (Object.keys(form.role_scope || {}).length ? JSON.stringify(form.role_scope) : 'None')}
            </p>
            {mode === 'invite' ? <p><strong>Invite Expiry:</strong> {Number(form.expires_in_days || 7)} day(s)</p> : null}
          </div>
        ) : null}

        {errorMessage ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-300">
            {errorMessage}
          </div>
        ) : null}
      </div>

      <div className="flex justify-between gap-2">
        <button type="button" className="btn-secondary" onClick={step === 0 ? onClose : goBack}>
          {step === 0 ? 'Cancel' : 'Back'}
        </button>
        {step < steps.length - 1 ? (
          <button type="button" className="btn-primary" onClick={goNext}>
            Next
          </button>
        ) : (
          <button type="button" className="btn-primary" disabled={loading} onClick={() => void handleSubmit()}>
            {loading ? (mode === 'create' ? 'Creating...' : 'Sending...') : (mode === 'create' ? 'Create User' : 'Send Invite')}
          </button>
        )}
      </div>
    </ModalShell>
  );
}

function UserImportModal({ open, onClose, previewImport, importPreview, commitImport, importing, onCommitted, topOffsetPx = 68 }) {
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState('invite');
  const [defaultPassword, setDefaultPassword] = useState('');
  if (!open) return null;
  return (
    <ModalShell title="Import Users" onClose={onClose} topOffsetPx={topOffsetPx}>
      <div className="space-y-3">
        <FormInput label="CSV File" type="file" accept=".csv,text/csv" onChange={(event) => setFile(event.target.files?.[0] || null)} />
        <button type="button" className="btn-secondary" disabled={!file || importing} onClick={() => previewImport(file)}>
          Preview
        </button>

        {importPreview ? (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm dark:border-slate-700 dark:bg-slate-900">
            <p>Total: {importPreview.total_rows} | Valid: {importPreview.valid_rows} | Invalid: {importPreview.invalid_rows}</p>
            <FormInput as="select" label="Commit Mode" value={mode} onChange={(event) => setMode(event.target.value)}>
              <option value="invite">Invite Users</option>
              <option value="create">Create Directly</option>
            </FormInput>
            {mode === 'create' ? (
              <FormInput label="Default Password" type="password" value={defaultPassword} onChange={(event) => setDefaultPassword(event.target.value)} />
            ) : null}
            <button
              type="button"
              className="btn-primary"
              disabled={importing || (mode === 'create' && defaultPassword.length < 8)}
              onClick={async () => {
                await commitImport({ mode, defaultPassword });
                onCommitted?.();
              }}
            >
              {importing ? 'Committing...' : 'Commit Import'}
            </button>
          </div>
        ) : null}
      </div>
    </ModalShell>
  );
}

function ModalShell({ title, children, onClose, topOffsetPx = 68 }) {
  useEffect(() => {
    function handleEscape(event) {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose?.();
      }
    }
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  return (
    <>
      <button type="button" className="fixed bottom-0 left-0 right-0 z-40 bg-slate-950/28 backdrop-blur-[2px]" style={{ top: `${topOffsetPx}px` }} onClick={onClose} />
      <div className="fixed bottom-0 left-0 right-0 z-40 flex items-start justify-center overflow-y-auto px-0 py-0 sm:px-4 sm:py-3" style={{ top: `${topOffsetPx}px` }}>
        <Card className="min-h-full w-full rounded-none border-0 shadow-[0_32px_120px_-56px_rgba(15,23,42,0.6)] sm:min-h-0 sm:w-[92vw] sm:max-w-2xl sm:rounded-[2rem] sm:border space-y-4">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-lg font-semibold">{title}</h3>
            <button type="button" className="btn-secondary !p-2" onClick={onClose} aria-label="Close"><X size={14} /></button>
          </div>
          {children}
        </Card>
      </div>
    </>
  );
}

function formatRoleLabel(value) {
  return String(value || '')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatDate(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

function formatPercent(value) {
  const numeric = Number(value || 0);
  return `${numeric.toFixed(2)}%`;
}

function formatMilliseconds(value) {
  const numeric = Number(value || 0);
  return `${Math.round(numeric)} ms`;
}

function formatBucketTime(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatAuditMeta(actor, when) {
  const actorLabel = String(actor || '').trim() || 'Not recorded';
  if (!when) return actorLabel;
  const date = new Date(when);
  if (Number.isNaN(date.getTime())) return actorLabel;
  return `${actorLabel} @ ${date.toLocaleString()}`;
}

function getNameInitials(name) {
  const words = String(name || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);
  if (!words.length) return 'U';
  return words.map((word) => word[0]).join('').toUpperCase();
}
