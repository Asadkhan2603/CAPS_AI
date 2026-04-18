import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, Check, Copy, Edit3, RefreshCw, Save, ShieldAlert, X } from 'lucide-react';
import FormInput from '../../components/ui/FormInput';
import { useAuthorizedImage } from '../../hooks/useAuthorizedImage';
import { cn } from '../../utils/cn';

const PERMISSION_OPTIONS = {
  teacher: ['year_head', 'class_coordinator', 'club_coordinator'],
  student: ['club_president', 'class_representative']
};

const PERMISSION_META = {
  year_head: {
    label: 'Year Head',
    description: 'Can supervise year-level academic operations and escalations.',
    risk: 'medium'
  },
  class_coordinator: {
    label: 'Class Coordinator',
    description: 'Can manage section-level coordination and class ownership scope.',
    risk: 'high'
  },
  club_coordinator: {
    label: 'Club Coordinator',
    description: 'Can supervise club operations and activity planning support.',
    risk: 'medium'
  },
  club_president: {
    label: 'Club President',
    description: 'Can represent and operate leadership functions for one club.',
    risk: 'medium'
  },
  class_representative: {
    label: 'Class Representative',
    description: 'Can monitor section-level attendance and submission gaps for one assigned section.',
    risk: 'low'
  }
};

const DETAILS_FIELD_META = [
  { key: 'full_name', label: 'Full Name' },
  { key: 'phone', label: 'Phone' },
  { key: 'organization', label: 'Organization' }
];

function FlipButton({ checked, disabled, onClick, label }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'inline-flex items-center gap-2 rounded-full border px-2 py-1 text-xs transition',
        checked
          ? 'border-brand-400 bg-brand-100 text-brand-700 dark:border-brand-600 dark:bg-brand-900/30 dark:text-brand-300'
          : 'border-slate-300 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300',
        disabled && 'cursor-not-allowed opacity-60'
      )}
    >
      <span
        className={cn(
          'relative h-5 w-9 rounded-full transition-colors',
          checked ? 'bg-brand-500' : 'bg-slate-300 dark:bg-slate-700'
        )}
      >
        <span
          className={cn(
            'absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform',
            checked ? 'left-4' : 'left-0.5'
          )}
        />
      </span>
      <span>{label}</span>
    </button>
  );
}

export default function UserDetailOverlay({
  open = true,
  topOffsetPx = 68,
  batches,
  clubs,
  close,
  departments,
  faculties,
  getEffectiveExtensions,
  getEffectiveScope,
  programs,
  savePermissions,
  savingIds,
  sections,
  selectedTab,
  selectedUser,
  semesters,
  setSelectedTab,
  specializations,
  toggleExtension,
  updateClassCoordinatorScope,
  updateClubPresidentScope,
  updateClassRepresentativeScope,
  activityItems = [],
  activityLoading = false,
  refreshActivity,
  onStatusChange,
  permissionTemplates = [],
  applyPermissionTemplate,
  createPermissionTemplate,
  updatePermissionTemplate,
  deletePermissionTemplate,
  permissionTemplateSaving = false,
  resetPermissionDraft,
  onSaveDetails,
  detailsSaving = false,
  capabilities = {}
}) {
  const [reason, setReason] = useState('');
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [riskReason, setRiskReason] = useState('');
  const [detailsEditing, setDetailsEditing] = useState(false);
  const [detailsReason, setDetailsReason] = useState('');
  const [showDetailsDiff, setShowDetailsDiff] = useState(false);
  const [detailsDraft, setDetailsDraft] = useState(() => buildDetailsDraft(selectedUser));
  const [emailCopied, setEmailCopied] = useState(false);
  const [templateName, setTemplateName] = useState('');
  const [templateDescription, setTemplateDescription] = useState('');
  const [templateAdminType, setTemplateAdminType] = useState('');
  const [templateActionError, setTemplateActionError] = useState('');
  const dialogRef = useRef(null);
  const closeButtonRef = useRef(null);
  const resolvedCapabilities = {
    workspace: true,
    activity: true,
    bulk_operations: true,
    permission_templates: true,
    invitations: true,
    import_export: true,
    inline_editing: true,
    compact_density: true,
    responsive_workflows: true,
    ...(capabilities || {})
  };
  const canActivity = resolvedCapabilities.activity !== false;
  const canPermissionTemplates = resolvedCapabilities.permission_templates !== false;
  const canInlineEditing = resolvedCapabilities.inline_editing !== false;
  const tabs = [
    { key: 'details', label: 'Details' },
    { key: 'permissions', label: 'Permissions' },
    ...(canActivity ? [{ key: 'activity', label: 'Activity' }] : []),
    { key: 'risk', label: 'Risk Actions' }
  ];

  const avatarSrc = useAuthorizedImage(selectedUser?.avatar_url, selectedUser?.avatar_updated_at);
  const selectedPermissions = selectedUser ? getEffectiveExtensions(selectedUser) : [];
  const selectedScope = selectedUser ? getEffectiveScope(selectedUser) : {};
  const basePermissions = selectedUser?.extended_roles || [];
  const baseScope = selectedUser?.role_scope || {};
  const hasPermissionDiff = hasArrayDifference(selectedPermissions, basePermissions);
  const hasScopeDiff = stableSerialize(selectedScope) !== stableSerialize(baseScope);
  const hasPendingPermissionChanges = hasPermissionDiff || hasScopeDiff;
  const allowedPermissions = selectedUser ? PERMISSION_OPTIONS[selectedUser.role] || [] : [];
  const classScope = selectedScope.class_coordinator || {};
  const clubScope = selectedScope.club_president || {};
  const representativeScope = selectedScope.class_representative || {};
  const programMap = Object.fromEntries(programs.map((item) => [item.id, item.name]));
  const availableDepartments = departments.filter(
    (item) => !classScope.faculty_id || item.faculty_id === classScope.faculty_id
  );
  const availablePrograms = programs.filter(
    (item) => !classScope.department_id || item.department_id === classScope.department_id
  );
  const availableSpecializations = specializations.filter(
    (item) => !classScope.program_id || item.program_id === classScope.program_id
  );
  const availableBatches = batches.filter(
    (item) =>
      (!classScope.program_id || item.program_id === classScope.program_id) &&
      (!classScope.specialization_id || item.specialization_id === classScope.specialization_id)
  );
  const availableSemesters = semesters.filter((item) => !classScope.batch_id || item.batch_id === classScope.batch_id);
  const availableSections = sections.filter((item) => {
    if (classScope.faculty_id && item.faculty_id !== classScope.faculty_id) return false;
    if (classScope.department_id && item.department_id !== classScope.department_id) return false;
    if (classScope.program_id && item.program_id !== classScope.program_id) return false;
    if (classScope.specialization_id && item.specialization_id !== classScope.specialization_id) return false;
    if (classScope.batch_id && item.batch_id !== classScope.batch_id) return false;
    if (classScope.semester_id && item.semester_id !== classScope.semester_id) return false;
    return true;
  });

  const templatesForRole = useMemo(
    () => (selectedUser ? permissionTemplates.filter((item) => item.role === selectedUser.role) : []),
    [permissionTemplates, selectedUser?.role]
  );
  const selectedTemplate = useMemo(
    () => templatesForRole.find((item) => item.id === selectedTemplateId) || null,
    [templatesForRole, selectedTemplateId]
  );
  const detailsChanges = useMemo(
    () => computeDetailsChanges(selectedUser, detailsDraft),
    [selectedUser, detailsDraft]
  );
  const effectiveAccessChips = useMemo(
    () => buildEffectiveAccessChips({ selectedUser, selectedPermissions, selectedScope, sections, clubs }),
    [selectedUser, selectedPermissions, selectedScope, sections, clubs]
  );
  const riskSummary = useMemo(() => getRiskSummary(selectedPermissions), [selectedPermissions]);

  useEffect(() => {
    setDetailsDraft(buildDetailsDraft(selectedUser));
    setDetailsEditing(false);
    setShowDetailsDiff(false);
    setDetailsReason('');
    setSelectedTemplateId('');
    setRiskReason('');
    setReason('');
    setTemplateName('');
    setTemplateDescription('');
    setTemplateAdminType(selectedUser?.admin_type || '');
    setTemplateActionError('');
    setEmailCopied(false);
  }, [selectedUser?.id]);

  useEffect(() => {
    if (!selectedUser) return;
    if (!selectedTemplate) {
      setTemplateName('');
      setTemplateDescription('');
      setTemplateAdminType(selectedUser.admin_type || '');
      return;
    }
    setTemplateName(selectedTemplate.name || '');
    setTemplateDescription(selectedTemplate.description || '');
    setTemplateAdminType(selectedTemplate.admin_type || '');
    setTemplateActionError('');
  }, [selectedTemplate, selectedUser?.id, selectedUser?.admin_type]);

  useEffect(() => {
    if (!canActivity && selectedTab === 'activity') {
      setSelectedTab?.('details');
    }
  }, [canActivity, selectedTab, setSelectedTab]);

  useEffect(() => {
    if (canInlineEditing) return;
    setDetailsEditing(false);
    setShowDetailsDiff(false);
    setDetailsReason('');
  }, [canInlineEditing]);

  useEffect(() => {
    if (!selectedUser) return undefined;
    const dialogElement = dialogRef.current;
    const focusTarget = closeButtonRef.current || getFocusableElements(dialogElement)[0];
    if (focusTarget && typeof focusTarget.focus === 'function') {
      window.setTimeout(() => focusTarget.focus(), 0);
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        event.preventDefault();
        close?.();
        return;
      }
      if (event.key !== 'Tab') return;
      const focusable = getFocusableElements(dialogElement);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    }

    dialogElement?.addEventListener('keydown', handleKeyDown);
    return () => {
      dialogElement?.removeEventListener('keydown', handleKeyDown);
    };
  }, [selectedUser?.id, close]);

  if (!open || !selectedUser) return null;

  function handleTemplateApply() {
    const template = selectedTemplate;
    if (!template) return;
    applyPermissionTemplate?.(selectedUser, template);
    setTemplateActionError('');
  }

  function buildTemplatePayload() {
    const trimmedName = String(templateName || '').trim();
    if (!trimmedName) {
      throw new Error('Template name is required.');
    }
    const templateScope = { ...(selectedScope || {}) };
    if ((selectedPermissions || []).includes('class_representative')) {
      delete templateScope.class_representative;
    }
    return {
      name: trimmedName,
      description: String(templateDescription || '').trim() || null,
      role: selectedUser.role,
      admin_type: String(templateAdminType || '').trim() || null,
      extended_roles: selectedPermissions,
      role_scope: templateScope
    };
  }

  async function handleCreateTemplate() {
    if (!canPermissionTemplates) return;
    setTemplateActionError('');
    try {
      const created = await createPermissionTemplate?.(buildTemplatePayload());
      if (created?.id) {
        setSelectedTemplateId(created.id);
      }
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Failed to create template';
      setTemplateActionError(String(detail));
    }
  }

  async function handleUpdateTemplate() {
    if (!canPermissionTemplates || !selectedTemplateId) return;
    setTemplateActionError('');
    try {
      await updatePermissionTemplate?.(selectedTemplateId, buildTemplatePayload());
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Failed to update template';
      setTemplateActionError(String(detail));
    }
  }

  async function handleDeleteTemplate() {
    if (!canPermissionTemplates || !selectedTemplateId || !selectedTemplate) return;
    const confirmed = window.confirm(`Delete template "${selectedTemplate.name}"?`);
    if (!confirmed) return;
    setTemplateActionError('');
    try {
      await deletePermissionTemplate?.(selectedTemplateId);
      setSelectedTemplateId('');
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Failed to delete template';
      setTemplateActionError(String(detail));
    }
  }

  async function handleStatusToggle(isActive) {
    if (!riskReason.trim()) return;
    await onStatusChange?.(isActive, riskReason.trim());
    setRiskReason('');
  }

  async function handleCopyEmail() {
    const email = String(selectedUser?.email || '').trim();
    if (!email) return;
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(email);
        setEmailCopied(true);
        window.setTimeout(() => setEmailCopied(false), 1800);
      }
    } catch {
      setEmailCopied(false);
    }
  }

  function handleStartDetailsEdit() {
    if (!canInlineEditing) return;
    setDetailsDraft(buildDetailsDraft(selectedUser));
    setShowDetailsDiff(false);
    setDetailsEditing(true);
  }

  function handleCancelDetailsEdit() {
    setDetailsDraft(buildDetailsDraft(selectedUser));
    setDetailsReason('');
    setShowDetailsDiff(false);
    setDetailsEditing(false);
  }

  function handlePreviewDetailsDiff() {
    if (!detailsChanges.length) return;
    setShowDetailsDiff(true);
  }

  async function handleSaveDetails() {
    if (!canInlineEditing) return;
    if (!detailsChanges.length) return;
    const payload = buildDetailsPayload(selectedUser, detailsDraft, detailsReason);
    await onSaveDetails?.(payload);
    setDetailsReason('');
    setShowDetailsDiff(false);
    setDetailsEditing(false);
  }

  async function handleSavePermissions() {
    await savePermissions(selectedUser, reason.trim());
    setReason('');
  }

  function handleResetPermissionChanges() {
    resetPermissionDraft?.(selectedUser);
    setReason('');
    setSelectedTemplateId('');
  }

  return (
    <>
      <button
        type="button"
        className="fixed bottom-0 left-0 right-0 z-30 bg-slate-950/28 backdrop-blur-[2px]"
        style={{ top: `${topOffsetPx}px` }}
        onClick={close}
        aria-hidden="true"
      />
      <div
        data-testid="users-detail-overlay-shell"
        className="fixed bottom-0 left-0 right-0 z-40 flex items-start justify-center overflow-hidden px-0 py-0 sm:px-4 sm:py-3"
        style={{ top: `${topOffsetPx}px` }}
      >
        <aside
          ref={dialogRef}
          data-testid="users-detail-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="users-detail-overlay-title"
          className="flex h-full w-full flex-col overflow-hidden bg-white text-slate-900 shadow-[0_32px_120px_-56px_rgba(15,23,42,0.6)] dark:bg-slate-950 dark:text-slate-100 sm:h-[calc(100%-24px)] sm:w-[92vw] sm:max-w-[980px] sm:rounded-[2rem] sm:border sm:border-slate-200/80 xl:w-[calc(100vw-140px)] xl:max-w-[1120px] dark:sm:border-slate-800"
        >
          <div className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/95 backdrop-blur dark:border-slate-800 dark:bg-slate-950/95">
            <div className="flex flex-wrap items-start justify-between gap-4 px-4 py-4 sm:px-6 sm:py-5">
              <div className="flex min-w-0 items-start gap-4">
                {avatarSrc ? (
                  <img
                    src={avatarSrc}
                    alt={`${selectedUser.full_name || 'User'} profile`}
                    className="h-14 w-14 rounded-2xl border border-slate-200 object-cover shadow-sm dark:border-slate-700"
                  />
                ) : (
                  <span className="inline-flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-200 bg-slate-100 text-lg font-semibold uppercase text-slate-600 shadow-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                    {getNameInitials(selectedUser.full_name)}
                  </span>
                )}
                <div className="min-w-0 space-y-3">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 id="users-detail-overlay-title" className="truncate text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50 md:text-[2rem]">
                        {selectedUser.full_name}
                      </h2>
                      <Chip label={riskSummary.label} tone={riskSummary.tone} />
                    </div>
                    <div className="flex flex-wrap items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
                      <span className="truncate">{selectedUser.email || '-'}</span>
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] font-medium text-slate-600 transition hover:border-brand-200 hover:text-brand-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-brand-800 dark:hover:text-brand-300"
                        onClick={handleCopyEmail}
                      >
                        {emailCopied ? <Check size={12} /> : <Copy size={12} />}
                        {emailCopied ? 'Copied' : 'Copy email'}
                      </button>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Chip label={formatRoleLabel(selectedUser.role)} />
                    {selectedUser.admin_type ? <Chip label={formatRoleLabel(selectedUser.admin_type)} tone="success" /> : null}
                    <Chip label={selectedUser.is_active === false ? 'Inactive' : 'Active'} tone={selectedUser.is_active === false ? 'high' : 'success'} />
                  </div>
                </div>
              </div>
              <button ref={closeButtonRef} type="button" className="btn-secondary !p-2" onClick={close} aria-label="Close user details">
                <X size={16} />
              </button>
            </div>

            <div className="grid gap-2 border-t border-slate-200/80 px-4 py-3 sm:grid-cols-3 sm:px-6 dark:border-slate-800">
              <MetricPill label="Last Active" value={formatDate(selectedUser.last_active_at)} />
              <MetricPill label="Created" value={formatDate(selectedUser.created_at)} />
              <MetricPill label="Extended Roles" value={selectedPermissions.length ? `${selectedPermissions.length} assigned` : 'None'} />
            </div>

            <div className="border-t border-slate-200/80 px-3 py-2 lg:hidden dark:border-slate-800">
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {tabs.map((tab) => (
                  <button
                    key={tab.key}
                    type="button"
                    className={cn(
                      'rounded-2xl border px-3 py-2 text-sm font-medium transition',
                      selectedTab === tab.key
                        ? 'border-brand-200 bg-brand-50 text-brand-700 dark:border-brand-800 dark:bg-brand-950/30 dark:text-brand-300'
                        : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:text-slate-100'
                    )}
                    onClick={() => setSelectedTab(tab.key)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="min-h-0 flex-1 lg:grid lg:grid-cols-[12rem_minmax(0,1fr)]">
            <nav className="hidden border-r border-slate-200 bg-slate-50/80 p-4 dark:border-slate-800 dark:bg-slate-900/40 lg:flex lg:flex-col lg:gap-1">
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  className={cn(
                    'flex items-center justify-between rounded-2xl px-3 py-2 text-left text-sm font-medium transition',
                    selectedTab === tab.key
                      ? 'bg-brand-50 text-brand-700 ring-1 ring-brand-200 dark:bg-brand-950/30 dark:text-brand-300 dark:ring-brand-900/60'
                      : 'text-slate-600 hover:bg-white hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-900 dark:hover:text-slate-100'
                  )}
                  onClick={() => setSelectedTab(tab.key)}
                >
                  <span>{tab.label}</span>
                  {selectedTab === tab.key ? <span className="h-2 w-2 rounded-full bg-current" /> : null}
                </button>
              ))}
            </nav>

            <div className="min-h-0 overflow-y-auto">
              <div className="space-y-5 px-4 py-4 sm:px-6 sm:py-5">

                {selectedTab === 'details' ? (
                  <div className="space-y-4">
                    {!detailsEditing ? (
                      <>
                        <div className="grid gap-4 xl:grid-cols-2">
                          <SectionCard title="Contact" description="Primary identity and reachability details.">
                            <DetailItem label="Full Name" value={selectedUser.full_name} />
                            <DetailItem label="Email" value={selectedUser.email} />
                            <DetailItem label="Phone" value={selectedUser.profile?.phone} />
                          </SectionCard>
                          <SectionCard title="Organization" description="Workspace-owned organization context.">
                            <DetailItem label="Department" value={selectedUser.profile?.department || selectedUser.department} />
                            <DetailItem label="Designation" value={selectedUser.profile?.designation || selectedUser.designation} />
                            <DetailItem label="Organization" value={selectedUser.profile?.organization} />
                          </SectionCard>
                          <SectionCard title="Account Metadata" description="Status, role, and account chronology.">
                            <DetailItem label="Role" value={formatRoleLabel(selectedUser.role)} />
                            <DetailItem label="Admin Type" value={selectedUser.admin_type ? formatRoleLabel(selectedUser.admin_type) : '-'} />
                            <DetailItem label="Account Status" value={selectedUser.is_active === false ? 'Inactive' : 'Active'} />
                            <DetailItem label="Last Active" value={formatDate(selectedUser.last_active_at)} />
                            <DetailItem label="Created" value={formatDate(selectedUser.created_at)} />
                            <DetailItem label="Updated" value={formatDate(selectedUser.updated_at)} />
                          </SectionCard>
                          <SectionCard title="Governance Context" description="Permission and lifecycle audit visibility.">
                            <DetailItem label="Effective Access" value={effectiveAccessChips.length ? effectiveAccessChips.map((chip) => chip.label).join(' | ') : 'Base access only'} />
                            <DetailItem label="Permission Changes" value={formatAuditMeta(selectedUser.last_permission_change_by, selectedUser.last_permission_change_at)} />
                            <DetailItem label="Status Changes" value={formatAuditMeta(selectedUser.last_status_change_by, selectedUser.last_status_change_at)} />
                          </SectionCard>
                        </div>
                        {canInlineEditing ? (
                          <div className="flex justify-end">
                            <button type="button" className="btn-secondary" onClick={handleStartDetailsEdit}>
                              <Edit3 size={14} />
                              Edit Safe Fields
                            </button>
                          </div>
                        ) : (
                          <div className="rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                            Inline profile editing is disabled by feature flag.
                          </div>
                        )}
                      </>
                    ) : (
                      <>
                        <div className="grid gap-4 xl:grid-cols-2">
                          <SectionCard title="Editable Fields" description="Only drawer-owned safe profile fields can be changed here.">
                            <div className="grid gap-3">
                              <FormInput
                                label="Full Name"
                                value={detailsDraft.full_name}
                                onChange={(event) => setDetailsDraft((prev) => ({ ...prev, full_name: event.target.value }))}
                              />
                              <FormInput
                                label="Phone"
                                value={detailsDraft.phone}
                                onChange={(event) => setDetailsDraft((prev) => ({ ...prev, phone: event.target.value }))}
                              />
                              <FormInput
                                label="Organization"
                                value={detailsDraft.organization}
                                onChange={(event) => setDetailsDraft((prev) => ({ ...prev, organization: event.target.value }))}
                              />
                            </div>
                          </SectionCard>
                          <SectionCard title="Locked Workspace Fields" description="Quick-edit fields stay owned by the table workspace.">
                            <DetailItem label="Email" value={selectedUser.email} />
                            <DetailItem label="Department" value={selectedUser.profile?.department || selectedUser.department} />
                            <DetailItem label="Designation" value={selectedUser.profile?.designation || selectedUser.designation} />
                            <DetailItem label="Role" value={formatRoleLabel(selectedUser.role)} />
                          </SectionCard>
                        </div>

                        <FormInput
                          label="Change Reason (Optional)"
                          value={detailsReason}
                          onChange={(event) => setDetailsReason(event.target.value)}
                          placeholder="Reason for this profile edit"
                        />

                        {showDetailsDiff ? (
                          <SectionCard
                            title="Diff Preview"
                            description="Review the before and after values before saving the profile update."
                            tone="brand"
                          >
                            <div className="space-y-3">
                              {detailsChanges.map((change) => (
                                <div key={change.key} className="rounded-2xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-900">
                                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{change.label}</p>
                                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Before: {change.from || '-'}</p>
                                  <p className="mt-1 text-sm font-medium text-slate-800 dark:text-slate-100">After: {change.to || '-'}</p>
                                </div>
                              ))}
                            </div>
                          </SectionCard>
                        ) : null}

                        <StickyFooter>
                          <button type="button" className="btn-secondary" onClick={handleCancelDetailsEdit} disabled={detailsSaving}>
                            Cancel
                          </button>
                          {!showDetailsDiff ? (
                            <button type="button" className="btn-secondary" onClick={handlePreviewDetailsDiff} disabled={!detailsChanges.length || detailsSaving}>
                              Preview Changes
                            </button>
                          ) : (
                            <>
                              <button type="button" className="btn-secondary" onClick={() => setShowDetailsDiff(false)} disabled={detailsSaving}>
                                Back To Edit
                              </button>
                              <button type="button" className="btn-primary" onClick={handleSaveDetails} disabled={!detailsChanges.length || detailsSaving}>
                                <Save size={14} />
                                {detailsSaving ? 'Saving...' : 'Confirm Save'}
                              </button>
                            </>
                          )}
                        </StickyFooter>
                      </>
                    )}
                  </div>
                ) : null}

                {selectedTab === 'permissions' ? (
                  <div className="space-y-4">
                    <SectionCard
                      title="Current Access Summary"
                      description="Role, effective access, and current governance metadata."
                      tone="brand"
                    >
                      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                        <InfoBlock label="Base Role" value={formatRoleLabel(selectedUser.role)} />
                        <InfoBlock label="Admin Type" value={selectedUser.admin_type ? formatRoleLabel(selectedUser.admin_type) : '-'} />
                        <InfoBlock label="Extended Roles" value={selectedPermissions.length ? selectedPermissions.map(formatRoleLabel).join(', ') : 'None'} />
                        <InfoBlock label="Risk Level" value={riskSummary.label.replace('Risk: ', '')} />
                      </div>
                      {effectiveAccessChips.length ? (
                        <div className="mt-4 space-y-2">
                          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Effective Access Preview</p>
                          <div className="flex flex-wrap gap-2">
                            {effectiveAccessChips.map((chip) => (
                              <Chip key={chip.key} tone={chip.tone} label={chip.label} />
                            ))}
                          </div>
                        </div>
                      ) : null}
                      <div className="mt-4 grid gap-3 sm:grid-cols-2">
                        <InfoBlock label="Last Changed By" value={selectedUser.last_permission_change_by || 'Not recorded'} />
                        <InfoBlock label="Last Changed At" value={formatDate(selectedUser.last_permission_change_at)} />
                      </div>
                    </SectionCard>

                    {canPermissionTemplates ? (
                      <SectionCard
                        title="Permission Templates"
                        description="Apply or manage reusable drafts for this role."
                      >
                        <div className="grid gap-3 sm:grid-cols-2">
                          <FormInput
                            as="select"
                            label="Template Library"
                            value={selectedTemplateId}
                            onChange={(event) => setSelectedTemplateId(event.target.value)}
                          >
                            <option value="">Select template</option>
                            {templatesForRole.map((template) => (
                              <option key={template.id} value={template.id}>
                                {template.name}
                              </option>
                            ))}
                          </FormInput>
                          <FormInput
                            label="Template Name"
                            value={templateName}
                            onChange={(event) => setTemplateName(event.target.value)}
                            placeholder="Template name"
                          />
                          <FormInput
                            label="Admin Type (Optional)"
                            value={templateAdminType}
                            onChange={(event) => setTemplateAdminType(event.target.value)}
                            placeholder="Template admin type"
                          />
                          <FormInput
                            as="textarea"
                            label="Template Description (Optional)"
                            value={templateDescription}
                            onChange={(event) => setTemplateDescription(event.target.value)}
                            placeholder="What this template grants and where to use it"
                            className="min-h-[84px] sm:col-span-2"
                          />
                        </div>
                        {!templatesForRole.length ? (
                          <div className="mt-3 rounded-[1.25rem] border border-dashed border-slate-300 bg-slate-50 px-3 py-3 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                            No templates for {formatRoleLabel(selectedUser.role)} yet.
                          </div>
                        ) : null}
                        {templateActionError ? (
                          <div className="mt-3 rounded-[1.25rem] border border-rose-200 bg-rose-50 px-3 py-3 text-xs text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-300">
                            {templateActionError}
                          </div>
                        ) : null}
                        <div className="mt-4 flex flex-wrap justify-end gap-2">
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={handleTemplateApply}
                            disabled={!selectedTemplateId || savingIds.includes(selectedUser.id) || permissionTemplateSaving}
                          >
                            Apply Template
                          </button>
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={handleCreateTemplate}
                            disabled={savingIds.includes(selectedUser.id) || permissionTemplateSaving}
                          >
                            {permissionTemplateSaving ? 'Saving...' : 'Save As New Template'}
                          </button>
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={handleUpdateTemplate}
                            disabled={!selectedTemplateId || savingIds.includes(selectedUser.id) || permissionTemplateSaving}
                          >
                            Update Template
                          </button>
                          <button
                            type="button"
                            className="btn-secondary !border-rose-300 !text-rose-700 dark:!border-rose-900/50 dark:!text-rose-300"
                            onClick={handleDeleteTemplate}
                            disabled={!selectedTemplateId || savingIds.includes(selectedUser.id) || permissionTemplateSaving}
                          >
                            Delete Template
                          </button>
                        </div>
                      </SectionCard>
                    ) : (
                      <div className="rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                        Permission templates are disabled by feature flag.
                      </div>
                    )}

                    <SectionCard
                      title="Extended Role Upgrade"
                      description="Enable role upgrades and provide the required scope before saving."
                    >
                      {allowedPermissions.length ? (
                        <div className="grid gap-3 sm:grid-cols-2">
                          {allowedPermissions.map((permission) => {
                            const meta = PERMISSION_META[permission] || {
                              label: formatRoleLabel(permission),
                              description: 'Additional access extension for this user role.',
                              risk: 'low'
                            };
                            const enabled = selectedPermissions.includes(permission);
                            return (
                              <div
                                key={permission}
                                className={cn(
                                  'rounded-[1.25rem] border px-4 py-4 transition',
                                  enabled
                                    ? 'border-brand-300 bg-brand-50/60 shadow-[0_18px_40px_-32px_rgba(59,130,246,0.35)] dark:border-brand-800/50 dark:bg-brand-950/20'
                                    : 'border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900'
                                )}
                              >
                                <div className="flex items-start justify-between gap-3">
                                  <div className="space-y-2">
                                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{meta.label}</p>
                                    <p className="text-xs text-slate-500 dark:text-slate-400">{meta.description}</p>
                                    <Chip label={`Risk: ${meta.risk}`} tone={meta.risk} />
                                  </div>
                                  <FlipButton
                                    checked={enabled}
                                    disabled={savingIds.includes(selectedUser.id)}
                                    onClick={() => toggleExtension(selectedUser, permission)}
                                    label={enabled ? 'Enabled' : 'Enable'}
                                  />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="rounded-[1.25rem] border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                          This role does not support upgrade permissions.
                        </div>
                      )}

                      {hasPendingPermissionChanges ? (
                        <div className="mt-4 rounded-[1.25rem] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
                          You have unsaved permission or scope changes.
                        </div>
                      ) : null}
                    </SectionCard>

                    {(selectedUser.role === 'teacher' && selectedPermissions.includes('class_coordinator')) || (selectedUser.role === 'student' && (selectedPermissions.includes('club_president') || selectedPermissions.includes('class_representative'))) ? (
                      <SectionCard
                        title="Scope Requirements"
                        description="Required assignment scope for the selected elevated role."
                      >
                        {selectedUser.role === 'teacher' && selectedPermissions.includes('class_coordinator') ? (
                          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                            <FormInput as="select" label="Faculty" value={classScope.faculty_id || ''} onChange={(event) => updateClassCoordinatorScope(selectedUser, { faculty_id: event.target.value || null, department_id: null, program_id: null, specialization_id: null, batch_id: null, semester_id: null, class_id: null })}>
                              <option value="">Select Faculty</option>
                              {faculties.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                            </FormInput>
                            <FormInput as="select" label="Department" value={classScope.department_id || ''} onChange={(event) => updateClassCoordinatorScope(selectedUser, { department_id: event.target.value || null, program_id: null, specialization_id: null, batch_id: null, semester_id: null, class_id: null })}>
                              <option value="">Select Department</option>
                              {availableDepartments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                            </FormInput>
                            <FormInput as="select" label="Program" value={classScope.program_id || ''} onChange={(event) => updateClassCoordinatorScope(selectedUser, { program_id: event.target.value || null, specialization_id: null, batch_id: null, semester_id: null, class_id: null })}>
                              <option value="">Select Program</option>
                              {availablePrograms.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                            </FormInput>
                            <FormInput as="select" label="Specialization" value={classScope.specialization_id || ''} onChange={(event) => updateClassCoordinatorScope(selectedUser, { specialization_id: event.target.value || null, batch_id: null, semester_id: null, class_id: null })}>
                              <option value="">Select Specialization</option>
                              {availableSpecializations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                            </FormInput>
                            <FormInput as="select" label="Batch" value={classScope.batch_id || ''} onChange={(event) => updateClassCoordinatorScope(selectedUser, { batch_id: event.target.value || null, semester_id: null, class_id: null })}>
                              <option value="">Select Batch</option>
                              {availableBatches.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                            </FormInput>
                            <FormInput as="select" label="Semester" value={classScope.semester_id || ''} onChange={(event) => updateClassCoordinatorScope(selectedUser, { semester_id: event.target.value || null, class_id: null })}>
                              <option value="">Select Semester</option>
                              {availableSemesters.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                            </FormInput>
                            <FormInput
                              as="select"
                              label="Section"
                              value={classScope.class_id || ''}
                              onChange={(event) => {
                                const classId = event.target.value || null;
                                const classDoc = sections.find((item) => item.id === classId);
                                updateClassCoordinatorScope(selectedUser, {
                                  class_id: classId,
                                  faculty_id: classDoc?.faculty_id || classScope.faculty_id || null,
                                  department_id: classDoc?.department_id || classScope.department_id || null,
                                  program_id: classDoc?.program_id || classScope.program_id || null,
                                  specialization_id: classDoc?.specialization_id || classScope.specialization_id || null,
                                  batch_id: classDoc?.batch_id || classScope.batch_id || null,
                                  semester_id: classDoc?.semester_id || classScope.semester_id || null
                                });
                              }}
                            >
                              <option value="">Select Section</option>
                              {availableSections.map((item) => (
                                <option key={item.id} value={item.id}>{item.name} | {programMap[item.program_id] || '-'} | {semesters.find((semester) => semester.id === item.semester_id)?.label || '-'}</option>
                              ))}
                            </FormInput>
                          </div>
                        ) : null}

                        {selectedUser.role === 'student' && selectedPermissions.includes('club_president') ? (
                          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                            <FormInput as="select" label="Club" value={clubScope.club_id || ''} onChange={(event) => updateClubPresidentScope(selectedUser, { club_id: event.target.value || null })}>
                              <option value="">Select Club</option>
                              {clubs.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                            </FormInput>
                          </div>
                        ) : null}

                        {selectedUser.role === 'student' && selectedPermissions.includes('class_representative') ? (
                          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                            <FormInput
                              as="select"
                              label="Section"
                              value={representativeScope.class_id || ''}
                              onChange={(event) => {
                                const classId = event.target.value || null;
                                const sectionDoc = sections.find((item) => item.id === classId);
                                updateClassRepresentativeScope(selectedUser, {
                                  class_id: classId,
                                  faculty_id: sectionDoc?.faculty_id || null,
                                  department_id: sectionDoc?.department_id || null,
                                  program_id: sectionDoc?.program_id || null,
                                  specialization_id: sectionDoc?.specialization_id || null,
                                  batch_id: sectionDoc?.batch_id || null,
                                  semester_id: sectionDoc?.semester_id || null,
                                });
                              }}
                            >
                              <option value="">Select Section</option>
                              {sections.map((item) => (
                                <option key={item.id} value={item.id}>{item.name}</option>
                              ))}
                            </FormInput>
                            <FormInput
                              as="select"
                              label="Seat"
                              value={representativeScope.seat || ''}
                              onChange={(event) => updateClassRepresentativeScope(selectedUser, { seat: event.target.value || null })}
                            >
                              <option value="">Select Seat</option>
                              <option value="cr_1">CR-1</option>
                              <option value="cr_2">CR-2</option>
                            </FormInput>
                          </div>
                        ) : null}
                      </SectionCard>
                    ) : null}

                    <SectionCard
                      title="Change Reason"
                      description="Optional audit context for the permission draft you are saving."
                    >
                      <FormInput
                        label="Change Reason (Optional)"
                        value={reason}
                        onChange={(event) => setReason(event.target.value)}
                        placeholder="Reason for permission updates"
                      />
                    </SectionCard>

                    <StickyFooter>
                      <button type="button" className="btn-secondary" disabled={savingIds.includes(selectedUser.id) || !hasPendingPermissionChanges} onClick={handleResetPermissionChanges}>
                        Revert Draft
                      </button>
                      <button type="button" className="btn-primary" disabled={savingIds.includes(selectedUser.id) || !hasPendingPermissionChanges} onClick={handleSavePermissions}>
                        {savingIds.includes(selectedUser.id) ? 'Saving...' : 'Save Permissions'}
                      </button>
                    </StickyFooter>
                  </div>
                ) : null}
                {selectedTab === 'activity' ? (
                  <SectionCard
                    title="User Activity Timeline"
                    description="Recent audited actions for this user."
                    headerAction={(
                      <button type="button" className="btn-secondary" onClick={() => refreshActivity?.()} disabled={activityLoading}>
                        <RefreshCw size={14} />
                        {activityLoading ? 'Refreshing...' : 'Refresh Activity'}
                      </button>
                    )}
                  >
                    {activityLoading ? (
                      <p className="text-sm text-slate-500 dark:text-slate-400">Loading activity...</p>
                    ) : null}
                    {!activityLoading && !activityItems.length ? (
                      <div className="rounded-[1.25rem] border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                        No activity records found for this user.
                      </div>
                    ) : null}
                    {activityItems.length ? (
                      <div className="relative ml-2 space-y-4 border-l border-slate-200 pl-5 dark:border-slate-800">
                        {activityItems.map((item) => (
                          <div key={item.id || `${item.action || 'action'}-${item.created_at || ''}`} className="relative">
                            <span className="absolute -left-[1.48rem] top-1.5 h-2.5 w-2.5 rounded-full border border-white bg-brand-400 shadow dark:border-slate-950" />
                            <div className="rounded-[1.25rem] border border-slate-200 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-900">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                                  {formatRoleLabel(item.action || item.action_type || 'activity')}
                                </p>
                                <span className={cn('rounded-full px-2 py-1 text-[11px] font-semibold uppercase tracking-wide', severityTone(item.severity))}>
                                  {item.severity || 'info'}
                                </span>
                              </div>
                              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                                Actor: {resolveActivityActor(item)}
                              </p>
                              <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">{item.detail || item.reason || 'No additional detail'}</p>
                              <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">{formatDate(item.created_at)}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </SectionCard>
                ) : null}

                {selectedTab === 'risk' ? (
                  <div className="space-y-4">
                    <SectionCard
                      title="High Impact Actions"
                      description="Lifecycle actions are intentionally separated from routine profile and permission edits."
                      tone="danger"
                    >
                      <div className="flex items-start gap-3 rounded-[1.25rem] border border-rose-200 bg-rose-50/80 px-4 py-4 text-sm text-rose-800 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-200">
                        <ShieldAlert size={16} className="mt-0.5" />
                        <div>
                          <p className="font-semibold">Status changes are audited</p>
                          <p className="mt-1 text-xs">
                            Deactivation or reactivation requires a reason and is fully audited.
                          </p>
                        </div>
                      </div>

                      <div className="grid gap-3 sm:grid-cols-2">
                        <DetailItem label="Current Status" value={selectedUser.is_active === false ? 'Inactive' : 'Active'} />
                        <DetailItem label="Last Status Change" value={formatAuditMeta(selectedUser.last_status_change_by, selectedUser.last_status_change_at)} />
                      </div>

                      <SectionCard
                        title={selectedUser.is_active === false ? 'Reactivate this user' : 'Deactivate this user'}
                        description={selectedUser.is_active === false ? 'Restores access after review approval.' : 'Removes active access until the account is reviewed and reactivated.'}
                      >
                        <FormInput
                          label="Reason"
                          value={riskReason}
                          onChange={(event) => setRiskReason(event.target.value)}
                          placeholder="Required reason for status change"
                        />
                        {!riskReason.trim() ? (
                          <div className="flex items-start gap-2 rounded-[1.25rem] border border-amber-200 bg-amber-50 px-3 py-3 text-xs text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
                            <AlertTriangle size={14} className="mt-0.5" />
                            Reason is required before changing status.
                          </div>
                        ) : null}
                        <div className="rounded-[1.25rem] border border-slate-200 bg-slate-50 px-4 py-4 dark:border-slate-700 dark:bg-slate-900">
                          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Confirmation</p>
                          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                            {selectedUser.is_active === false
                              ? 'This will restore access for the selected user.'
                              : 'This will remove active access for the selected user until reactivated.'}
                          </p>
                        </div>
                      </SectionCard>
                    </SectionCard>

                    <StickyFooter>
                      {selectedUser.is_active === false ? (
                        <button type="button" className="btn-primary" disabled={!riskReason.trim()} onClick={() => handleStatusToggle(true)}>
                          Reactivate User
                        </button>
                      ) : (
                        <button type="button" className="btn-secondary !border-rose-300 !text-rose-700 dark:!border-rose-900/50 dark:!text-rose-300" disabled={!riskReason.trim()} onClick={() => handleStatusToggle(false)}>
                          Deactivate User
                        </button>
                      )}
                    </StickyFooter>
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}

function InfoBlock({ label, value }) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-sm font-medium text-slate-800 dark:text-slate-100">{value || '-'}</p>
    </div>
  );
}

function MetricPill({ label, value }) {
  return (
    <div className="rounded-[1.25rem] border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-900 dark:text-slate-100">{value || '-'}</p>
    </div>
  );
}

function SectionCard({ title, description, children, headerAction = null, tone = 'default' }) {
  const toneClass =
    tone === 'brand'
      ? 'border-brand-200/80 bg-brand-50/60 dark:border-brand-900/40 dark:bg-brand-950/20'
      : tone === 'danger'
        ? 'border-rose-200/80 bg-rose-50/50 dark:border-rose-900/40 dark:bg-rose-950/10'
        : 'border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/80';

  return (
    <section className={cn('rounded-[1.65rem] border px-4 py-4 shadow-[0_18px_60px_-50px_rgba(15,23,42,0.45)] sm:px-5', toneClass)}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
          {description ? <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p> : null}
        </div>
        {headerAction}
      </div>
      <div className="mt-4 space-y-3">{children}</div>
    </section>
  );
}

function DetailItem({ label, value }) {
  return (
    <div className="rounded-[1.15rem] border border-slate-200/80 bg-slate-50/80 px-4 py-3 dark:border-slate-800 dark:bg-slate-950/50">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-sm font-medium text-slate-900 dark:text-slate-100 break-words">{value || '-'}</p>
    </div>
  );
}

function StickyFooter({ children }) {
  return (
    <div className="sticky bottom-0 z-10 -mx-4 border-t border-slate-200/80 bg-white/95 px-4 py-3 backdrop-blur sm:-mx-6 sm:px-6 dark:border-slate-800 dark:bg-slate-950/95">
      <div className="flex flex-wrap justify-end gap-2">{children}</div>
    </div>
  );
}

function Chip({ label, tone = 'neutral' }) {
  const toneClass =
    tone === 'high'
      ? 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-300'
      : tone === 'medium'
        ? 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-300'
        : tone === 'success'
          ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/20 dark:text-emerald-300'
          : 'border-slate-200 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200';
  return <span className={cn('rounded-full border px-2 py-1 text-xs font-medium', toneClass)}>{label}</span>;
}

function buildDetailsDraft(user) {
  return {
    full_name: user?.full_name || '',
    phone: user?.profile?.phone || '',
    organization: user?.profile?.organization || ''
  };
}

function computeDetailsChanges(user, draft) {
  if (!user) return [];
  const current = buildDetailsDraft(user);
  return DETAILS_FIELD_META.reduce((acc, field) => {
    const from = String(current[field.key] || '').trim();
    const to = String(draft[field.key] || '').trim();
    if (from === to) return acc;
    acc.push({ key: field.key, label: field.label, from, to });
    return acc;
  }, []);
}

function buildDetailsPayload(user, draft, reason) {
  const changes = computeDetailsChanges(user, draft);
  const payload = {};
  changes.forEach((item) => {
    payload[item.key] = item.to || null;
  });
  if (reason && reason.trim()) {
    payload.change_reason = reason.trim();
  }
  return payload;
}

function buildEffectiveAccessChips({ selectedUser, selectedPermissions, selectedScope, sections, clubs }) {
  if (!selectedUser) return [];
  const chips = [
    { key: `role-${selectedUser.role}`, label: `Base: ${formatRoleLabel(selectedUser.role)}`, tone: 'neutral' }
  ];
  if (selectedUser.admin_type) {
    chips.push({
      key: `admin-type-${selectedUser.admin_type}`,
      label: `Admin Type: ${formatRoleLabel(selectedUser.admin_type)}`,
      tone: 'success'
    });
  }
  (selectedPermissions || []).forEach((permission) => {
    const meta = PERMISSION_META[permission];
    chips.push({
      key: `extension-${permission}`,
      label: `Extension: ${meta?.label || formatRoleLabel(permission)}`,
      tone: meta?.risk || 'medium'
    });
  });
  const classId = selectedScope?.class_coordinator?.class_id;
  if (classId) {
    const section = sections.find((item) => item.id === classId);
    chips.push({ key: `section-${classId}`, label: `Section: ${section?.name || classId}`, tone: 'medium' });
  }
  const clubId = selectedScope?.club_president?.club_id;
  if (clubId) {
    const club = clubs.find((item) => item.id === clubId);
    chips.push({ key: `club-${clubId}`, label: `Club: ${club?.name || clubId}`, tone: 'medium' });
  }
  const representativeClassId = selectedScope?.class_representative?.class_id;
  if (representativeClassId) {
    const section = sections.find((item) => item.id === representativeClassId);
    chips.push({
      key: `representative-section-${representativeClassId}`,
      label: `CR Section: ${section?.name || representativeClassId}`,
      tone: 'low'
    });
  }
  const representativeSeat = selectedScope?.class_representative?.seat;
  if (representativeSeat) {
    chips.push({
      key: `representative-seat-${representativeSeat}`,
      label: `Seat: ${String(representativeSeat).replace('_', '-').toUpperCase()}`,
      tone: 'low'
    });
  }
  return chips;
}

function getRiskSummary(permissions = []) {
  if ((permissions || []).includes('class_coordinator')) {
    return { label: 'Risk: High', tone: 'high' };
  }
  if ((permissions || []).includes('class_representative')) {
    return { label: 'Risk: Low', tone: 'success' };
  }
  if ((permissions || []).some((permission) => ['year_head', 'club_coordinator', 'club_president'].includes(permission))) {
    return { label: 'Risk: Medium', tone: 'medium' };
  }
  return { label: 'Risk: Baseline', tone: 'success' };
}

function resolveActivityActor(item) {
  return (
    item?.actor_name ||
    item?.actor ||
    item?.performed_by ||
    item?.created_by ||
    item?.user_name ||
    item?.email ||
    'System'
  );
}

function hasArrayDifference(left = [], right = []) {
  if (left.length !== right.length) return true;
  const leftSorted = [...left].sort();
  const rightSorted = [...right].sort();
  return leftSorted.some((item, index) => item !== rightSorted[index]);
}

function stableSerialize(value) {
  return JSON.stringify(sortDeep(value));
}

function sortDeep(value) {
  if (Array.isArray(value)) {
    return value.map(sortDeep);
  }
  if (value && typeof value === 'object') {
    return Object.keys(value)
      .sort()
      .reduce((acc, key) => {
        acc[key] = sortDeep(value[key]);
        return acc;
      }, {});
  }
  return value ?? null;
}

function formatRoleLabel(value) {
  return String(value || '')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
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

function formatDate(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

function formatAuditMeta(actor, when) {
  const actorLabel = String(actor || '').trim() || 'Not recorded';
  if (!when) return actorLabel;
  const date = new Date(when);
  if (Number.isNaN(date.getTime())) return actorLabel;
  return `${actorLabel} @ ${date.toLocaleString()}`;
}

function severityTone(value) {
  if (value === 'high') {
    return 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-300';
  }
  if (value === 'medium') {
    return 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-300';
  }
  return 'border-slate-200 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200';
}

function getFocusableElements(root) {
  if (!root || typeof root.querySelectorAll !== 'function') return [];
  return Array.from(
    root.querySelectorAll(
      'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'
    )
  ).filter((element) => !element.hasAttribute('aria-hidden'));
}
