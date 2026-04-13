import { useEffect, useMemo, useRef, useState } from 'react';
import { Download, Lock, ShieldAlert, Unlock } from 'lucide-react';
import { Link } from 'react-router-dom';
import Card from '../ui/Card';
import SearchableSelect from '../ui/SearchableSelect';
import { apiClient } from '../../services/apiClient';
import { previewStudentBulkImport, commitStudentBulkImport } from '../../services/studentBulkImportApi';
import { lockSectionMapping, unlockSectionMapping } from '../../services/sectionsApi';
import { useToast } from '../../hooks/useToast';
import { formatApiError } from '../../utils/apiError';
import { downloadCreateStudentsTemplate, downloadMapExistingTemplate } from '../../utils/studentBulkTemplates';
import StudentBulkStepIndicator from './StudentBulkStepIndicator';
import StudentBulkModeSwitcher from './StudentBulkModeSwitcher';
import StudentBulkUploadHero from './StudentBulkUploadHero';
import StudentBulkValidationSummary from './StudentBulkValidationSummary';
import StudentBulkActionBar from './StudentBulkActionBar';

const STATUS_STYLES = {
  valid: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  invalid: 'bg-amber-50 text-amber-700 border-amber-200',
  blocked: 'bg-rose-50 text-rose-700 border-rose-200',
  noop: 'bg-slate-50 text-slate-700 border-slate-200',
  failed: 'bg-rose-50 text-rose-700 border-rose-200'
};

const WORKFLOW_COPY = {
  create_students: {
    templateHint: 'Includes the required identity columns and a sample row for creating global student records.',
    destinationTitle: 'Global-first onboarding',
    destinationDescription: 'Students are created centrally first, then assigned later through Section Mapping when operations are ready.',
    sectionHelper: 'No section is required in this workflow. Students stay globally available until mapped later.',
    groupHelper: 'Group overrides remain disabled until a student is placed into a section.'
  },
  map_existing: {
    templateHint: 'Includes supported lookup columns and optional group assignment for safe remapping.',
    destinationTitle: 'Choose the target section',
    destinationDescription: 'Pick the destination section first, then validate the roster before committing any placement.',
    sectionHelper: 'Choose the section that should receive the existing students in this mapping run.',
    groupHelper: 'Optional group override for students mapped into this section.'
  }
};

function toSectionOption(section) {
  const context = [section.branch_name, section.faculty_name].filter(Boolean).join(' | ');
  return {
    value: section.id,
    label: context ? `${section.name} - ${context}` : section.name,
    shortLabel: section.name,
    ...section
  };
}

function toGroupOption(group) {
  return {
    value: group.id,
    label: `${group.name} (${group.code})`,
    ...group
  };
}

function statusClass(status) {
  return STATUS_STYLES[status] || STATUS_STYLES.noop;
}

function formatTimestamp(value) {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '-' : date.toLocaleString();
}

function formatLockOwner(name, email) {
  if (name && email) return `${name} (${email})`;
  if (name) return name;
  if (email) return email;
  return 'Unknown user';
}

function getCurrentStep({ workflow, selectedSectionId, file, preview, commitResult }) {
  if (workflow === 'create_students') {
    if (commitResult) return 3;
    if (preview) return 2;
    return 1;
  }
  if (commitResult) return 4;
  if (preview) return 3;
  if (file) return 2;
  if (selectedSectionId) return 1;
  return 1;
}

function DestinationPanel({
  panelRef,
  modeCopy,
  sectionOptions,
  groupOptions,
  selectedSection,
  selectedSectionId,
  selectedGroup,
  selectedGroupId,
  loadSections,
  loadGroups,
  setSelectedSectionId,
  setSelectedGroupId,
  mode
}) {
  return (
    <div ref={panelRef}>
      <Card className="space-y-4 !p-4 lg:!p-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Assignment Control</p>
          <h3 className="mt-1 text-base font-semibold text-slate-950 dark:text-white">{modeCopy.destinationTitle}</h3>
          <p className="mt-1 text-sm text-slate-500">{modeCopy.destinationDescription}</p>
        </div>

        <div className="space-y-2">
          <SearchableSelect
            label="Section"
            value={selectedSectionId}
            options={sectionOptions}
            selectedLabel={selectedSection?.label || ''}
            placeholder="Search and select a section"
            loadKey={`sections-${mode}`}
            loadOptions={loadSections}
            required
            onValueChange={(value) => {
              setSelectedSectionId(value || '');
              setSelectedGroupId('');
            }}
          />
          <p className="text-sm text-slate-500">{modeCopy.sectionHelper}</p>
        </div>

        <div className="space-y-2">
          <SearchableSelect
            label="Group"
            value={selectedGroupId}
            options={groupOptions}
            selectedLabel={selectedGroup?.label || ''}
            placeholder={selectedSectionId ? 'Optional group override' : 'Select section first'}
            loadKey={`groups-${selectedSectionId}`}
            loadOptions={(query) => loadGroups(selectedSectionId, query)}
            disabled={!selectedSectionId}
            allowEmpty
            emptyLabel="No group override"
            onValueChange={(value) => setSelectedGroupId(value || '')}
          />
          <p className="text-sm text-slate-500">{modeCopy.groupHelper}</p>
        </div>

        <div className="rounded-[1.2rem] border border-slate-200 bg-slate-50/85 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Current Destination</p>
          <p className="mt-2 text-sm font-semibold text-slate-950">
            {selectedSection ? selectedSection.shortLabel || selectedSection.label : 'Section not selected'}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {selectedSection?.branch_name || selectedSection?.faculty_name
              ? [selectedSection?.branch_name, selectedSection?.faculty_name].filter(Boolean).join(' | ')
              : 'Select a section to unlock upload and validation.'}
          </p>
          <p className="mt-2 text-sm text-slate-600">
            {selectedGroup
              ? `Group override: ${selectedGroup.label}`
              : 'No group override will be applied unless one is selected here or provided in the upload.'}
          </p>
        </div>
      </Card>
    </div>
  );
}

function GlobalStudentPanel() {
  return (
    <Card className="space-y-4 !p-4 lg:!p-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Assignment Model</p>
        <h3 className="mt-1 text-base font-semibold text-slate-950 dark:text-white">Students are created as global records</h3>
        <p className="mt-1 text-sm text-slate-500">
          Admins can onboard students first, then teachers or admins can place them into sections later through Section Mapping.
        </p>
      </div>

      <div className="rounded-[1.2rem] border border-slate-200 bg-slate-50/85 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">What happens in this run</p>
        <p className="mt-2 text-sm font-semibold text-slate-950">Student accounts and profiles are created without compulsory section assignment.</p>
        <p className="mt-2 text-sm text-slate-600">
          After creation, use Section Mapping whenever you want to place these students into a section or group.
        </p>
      </div>
    </Card>
  );
}

function CoordinatorLockPanel({ selectedSection, locking, handleLockToggle }) {
  if (!selectedSection) return null;

  return (
    <Card className={`!p-5 ${selectedSection.mapping_locked ? '!border-amber-200 !bg-amber-50/90' : '!border-emerald-200 !bg-emerald-50/90'}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-2 text-sm font-semibold text-slate-900">
            {selectedSection.mapping_locked ? <Lock size={16} /> : <Unlock size={16} />}
            {selectedSection.mapping_locked ? 'Section mapping is locked' : 'Section mapping is unlocked'}
          </div>
          <p className="text-sm text-slate-600">
            {selectedSection.mapping_locked
              ? `${formatLockOwner(selectedSection.mapping_locked_by_name, selectedSection.mapping_locked_by_email)} locked this section on ${formatTimestamp(selectedSection.mapping_locked_at)}.`
              : 'Lock the section after a successful mapping cycle to prevent accidental cross-section mapping conflicts.'}
          </p>
          {selectedSection.mapping_lock_reason ? (
            <p className="text-xs text-slate-500">Reason: {selectedSection.mapping_lock_reason}</p>
          ) : null}
        </div>
        <button
          type="button"
          className="btn-secondary inline-flex items-center gap-2 !rounded-2xl"
          disabled={locking}
          onClick={() => handleLockToggle(!selectedSection.mapping_locked)}
        >
          {selectedSection.mapping_locked ? <Unlock size={16} /> : <Lock size={16} />}
          {selectedSection.mapping_locked ? 'Unlock Section' : 'Lock Section'}
        </button>
      </div>
    </Card>
  );
}

function PreviewTable({ preview }) {
  const [statusFilter, setStatusFilter] = useState('all');
  const filteredRows = useMemo(() => {
    if (statusFilter === 'all') return preview.rows;
    return preview.rows.filter((row) => row.status === statusFilter);
  }, [preview.rows, statusFilter]);
  const filterItems = [
    { value: 'all', label: 'All', count: preview.rows.length },
    { value: 'valid', label: 'Valid', count: preview.summary.valid_rows || 0 },
    { value: 'invalid', label: 'Invalid', count: preview.summary.invalid_rows || 0 },
    { value: 'blocked', label: 'Blocked', count: preview.summary.blocked_rows || 0 },
    { value: 'noop', label: 'No-op', count: preview.summary.noop_rows || 0 }
  ];

  return (
    <Card className="space-y-4 !p-5 lg:!p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Preview Results</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950 dark:text-white">Validation preview</h2>
          <p className="mt-1 text-sm text-slate-500">
            Destination: {preview.section?.name || 'Global student creation'}
            {preview.section?.mapping_locked
              ? ` | Locked by ${formatLockOwner(preview.section.mapping_locked_by_name, preview.section.mapping_locked_by_email)}`
              : ''}
          </p>
          <p className="mt-2 text-sm text-slate-700">
            {preview.summary.valid_rows} rows ready, {preview.summary.invalid_rows + preview.summary.blocked_rows} need attention,{' '}
            {preview.summary.noop_rows} unchanged.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-sm">
          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-emerald-700">Valid {preview.summary.valid_rows}</span>
          <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-amber-700">Invalid {preview.summary.invalid_rows}</span>
          <span className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-rose-700">Blocked {preview.summary.blocked_rows}</span>
          <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-slate-700">No-op {preview.summary.noop_rows}</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {filterItems.map((item) => {
          const active = statusFilter === item.value;
          return (
            <button
              key={item.value}
              type="button"
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors ${
                active
                  ? 'border-brand-300 bg-brand-600 text-white'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-brand-200 hover:text-brand-700'
              }`}
              onClick={() => setStatusFilter(item.value)}
            >
              {item.label} {item.count}
            </button>
          );
        })}
      </div>

      <div className="overflow-x-auto rounded-[1.35rem] border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="sticky top-0 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Row</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Identifier</th>
              <th className="px-4 py-3">Current</th>
              <th className="px-4 py-3">Target</th>
              <th className="px-4 py-3">Reason</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {filteredRows.map((row) => (
              <tr key={`${row.row_number}-${row.identifier}`}>
                <td className="px-4 py-3 font-medium">{row.row_number}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium capitalize ${statusClass(row.status)}`}>
                    {row.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="font-medium text-slate-800">{row.full_name || row.student_name || '-'}</div>
                  <div className="text-xs text-slate-500">{row.action}</div>
                </td>
                <td className="px-4 py-3 text-slate-600">
                  {row.email || row.enrollment_number || row.roll_number || row.student_id || '-'}
                </td>
                <td className="px-4 py-3 text-slate-600">
                  <div>{row.current_section_name || 'Unmapped'}</div>
                </td>
                <td className="px-4 py-3 text-slate-600">
                  <div>{row.target_section_name}</div>
                  <div className="text-xs text-slate-500">{row.target_group_name || 'No group'}</div>
                </td>
                <td className="px-4 py-3 text-slate-600">
                  {row.messages?.length ? (
                    <ul className="space-y-1">
                      {row.messages.map((message) => (
                        <li key={message} className="flex items-start gap-2">
                          <ShieldAlert size={14} className="mt-0.5 shrink-0 text-slate-400" />
                          <span>{message}</span>
                        </li>
                      ))}
                    </ul>
                  ) : <span className="text-slate-400">Ready</span>}
                </td>
              </tr>
            ))}
            {!filteredRows.length ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-sm text-slate-500">
                  No rows match this filter.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function CommitResultCard({ commitResult, workflow }) {
  if (!commitResult) return null;

  const committedRows = Number(commitResult.summary?.committed_rows || 0);
  const cleanupHref = `/enrollments?cleanup=unmapped&source=bulk-create&committed=${committedRows}`;

  return (
    <Card className="space-y-4 !p-5 lg:!p-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Commit Result</p>
        <h2 className="mt-1 text-lg font-semibold text-slate-950 dark:text-white">Import completed safely</h2>
      </div>
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        {Object.entries(commitResult.summary).map(([key, value]) => (
          <div key={key} className="rounded-[1.2rem] border border-slate-200 bg-slate-50 p-3">
            <p className="text-[11px] uppercase tracking-wide text-slate-500">{key.replaceAll('_', ' ')}</p>
            <p className="mt-1 text-xl font-semibold text-slate-900">{value}</p>
          </div>
        ))}
      </div>
      {commitResult.temporary_password ? (
        <div className="rounded-[1.35rem] border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <p className="font-medium">Temporary password</p>
          <p className="mt-1 font-mono">{commitResult.temporary_password}</p>
          <p className="mt-2 text-xs">{commitResult.credential_notice}</p>
        </div>
      ) : null}
      {workflow === 'create_students' ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-[1.35rem] border border-sky-200 bg-sky-50 p-4">
          <div>
            <p className="text-sm font-semibold text-sky-900">Next step: place newly created students into sections</p>
            <p className="mt-1 text-sm text-sky-800">
              Jump straight into enrollment cleanup and review unmapped students after this bulk create run.
            </p>
          </div>
          <Link className="btn-secondary !border-sky-300 !bg-white !text-sky-800 hover:!bg-sky-100" to={cleanupHref}>
            Open Enrollment Cleanup
          </Link>
        </div>
      ) : null}
    </Card>
  );
}

export default function StudentBulkWorkflow({ mode = 'admin' }) {
  const isAdminMode = mode === 'admin';
  const defaultWorkflow = isAdminMode ? 'create_students' : 'map_existing';
  const { pushToast } = useToast();
  const previewTableRef = useRef(null);
  const destinationPanelRef = useRef(null);
  const [workflow, setWorkflow] = useState(defaultWorkflow);
  const [sectionOptions, setSectionOptions] = useState([]);
  const [groupOptions, setGroupOptions] = useState([]);
  const [selectedSectionId, setSelectedSectionId] = useState('');
  const [selectedGroupId, setSelectedGroupId] = useState('');
  const [allowAdminOverride, setAllowAdminOverride] = useState(false);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [commitResult, setCommitResult] = useState(null);
  const [previewing, setPreviewing] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [locking, setLocking] = useState(false);

  useEffect(() => {
    setWorkflow(defaultWorkflow);
  }, [defaultWorkflow]);

  async function loadSections(query = '') {
    const response = await apiClient.get('/sections/', {
      params: {
        skip: 0,
        limit: 50,
        is_active: true,
        q: query || undefined
      }
    });
    const rows = Array.isArray(response.data) ? response.data : [];
    setSectionOptions((prev) => {
      const merged = new Map(prev.map((item) => [item.value, item]));
      rows.forEach((row) => merged.set(row.id, toSectionOption(row)));
      return Array.from(merged.values());
    });
    return rows.map(toSectionOption);
  }

  async function loadGroups(sectionId, query = '') {
    if (!sectionId) return [];
    const response = await apiClient.get('/groups/', {
      params: {
        skip: 0,
        limit: 50,
        is_active: true,
        section_id: sectionId,
        q: query || undefined
      }
    });
    const rows = Array.isArray(response.data) ? response.data : [];
    const options = rows.map(toGroupOption);
    setGroupOptions(options);
    return options;
  }

  useEffect(() => {
    loadSections().catch(() => {
      setSectionOptions([]);
    });
  }, []);

  useEffect(() => {
    if (!selectedSectionId) {
      setSelectedGroupId('');
      setGroupOptions([]);
      return;
    }
    loadGroups(selectedSectionId).catch(() => {
      setSelectedGroupId('');
      setGroupOptions([]);
    });
  }, [selectedSectionId]);

  useEffect(() => {
    setPreview(null);
    setCommitResult(null);
  }, [selectedSectionId, selectedGroupId, workflow, allowAdminOverride, file]);

  const selectedSection = useMemo(
    () => sectionOptions.find((option) => String(option.value) === String(selectedSectionId)) || null,
    [sectionOptions, selectedSectionId]
  );
  const selectedGroup = useMemo(
    () => groupOptions.find((option) => String(option.value) === String(selectedGroupId)) || null,
    [groupOptions, selectedGroupId]
  );
  const requiresDestination = workflow === 'map_existing';
  const canCommit = Boolean(preview?.summary?.valid_rows);
  const previewDisabledReason = requiresDestination && !selectedSectionId
    ? 'Select a section to unlock validation.'
    : !file
      ? 'Upload a file to enable validation.'
      : '';
  const commitDisabledReason = !preview
    ? 'Run validation before import.'
    : !canCommit
      ? 'Only rows marked valid can be imported.'
      : '';
  const currentStep = getCurrentStep({ workflow, selectedSectionId, file, preview, commitResult });
  const stepItems = workflow === 'create_students'
    ? [
        { title: 'Upload', description: 'Upload the student sheet for global account creation.' },
        { title: 'Validate', description: 'Review duplicates and invalid rows before commit.' },
        { title: 'Import', description: 'Create only the safe, valid student records.' }
      ]
    : [
        { title: 'Choose Section', description: 'Choose the target section and optional group.' },
        { title: 'Upload', description: 'Upload the roster sheet for validation.' },
        { title: 'Validate', description: 'Review blocked and invalid rows before commit.' },
        { title: 'Import', description: 'Write only the safe, valid rows.' }
      ];
  const pageTitle = isAdminMode ? 'Bulk Onboarding' : 'Section Mapping';
  const pageDescription = isAdminMode
    ? 'Create students globally, validate the sheet, and continue into Section Mapping only when placement is needed.'
    : 'Map existing students into your section with a controlled preview-and-commit workflow.';
  const modeCopy = WORKFLOW_COPY[workflow] || WORKFLOW_COPY.create_students;

  async function handlePreview() {
    if (requiresDestination && !selectedSectionId) {
      pushToast({ title: 'Select section', description: 'Choose a section before previewing the upload.', variant: 'warning' });
      return;
    }
    if (!file) {
      pushToast({ title: 'Choose file', description: 'Upload a CSV or XLSX file first.', variant: 'warning' });
      return;
    }
    setPreviewing(true);
    try {
      const response = await previewStudentBulkImport({
        workflow,
        sectionId: requiresDestination ? selectedSectionId : '',
        groupId: requiresDestination ? selectedGroupId || '' : '',
        file,
        allowAdminOverride
      });
      setPreview(response.data);
      setCommitResult(null);
      pushToast({ title: 'Preview ready', description: 'Review valid, invalid, and blocked rows before committing.', variant: 'success' });
    } catch (err) {
      pushToast({ title: 'Preview failed', description: formatApiError(err, 'Failed to preview student upload'), variant: 'error' });
    } finally {
      setPreviewing(false);
    }
  }

  async function handleCommit() {
    if (!canCommit) {
      pushToast({ title: 'Nothing to commit', description: 'Preview the file first and make sure at least one row is valid.', variant: 'warning' });
      return;
    }
    setCommitting(true);
    try {
      const response = await commitStudentBulkImport({
        workflow,
        sectionId: requiresDestination ? selectedSectionId : '',
        groupId: requiresDestination ? selectedGroupId || '' : '',
        file,
        allowAdminOverride
      });
      setCommitResult(response.data);
      pushToast({ title: 'Import committed', description: `${response.data.summary.committed_rows} rows were processed safely.`, variant: 'success' });
      await loadSections();
      if (selectedSectionId) {
        await loadGroups(selectedSectionId);
      }
      if (workflow === 'create_students') {
        pushToast({
          title: 'Placement cleanup ready',
          description: 'Use Enrollment Cleanup next to place newly created students into their sections.',
          variant: 'info'
        });
      }
    } catch (err) {
      pushToast({ title: 'Commit failed', description: formatApiError(err, 'Failed to commit student upload'), variant: 'error' });
    } finally {
      setCommitting(false);
    }
  }

  async function handleLockToggle(nextLocked) {
    if (!selectedSectionId) return;
    setLocking(true);
    try {
      const reason = window.prompt(nextLocked ? 'Optional lock reason' : 'Optional unlock reason', '') || '';
      const response = nextLocked
        ? await lockSectionMapping(selectedSectionId, reason)
        : await unlockSectionMapping(selectedSectionId, reason);
      const updated = toSectionOption(response.data);
      setSectionOptions((prev) => prev.map((item) => (item.value === updated.value ? updated : item)));
      pushToast({
        title: nextLocked ? 'Section locked' : 'Section unlocked',
        description: `${updated.shortLabel || updated.label} mapping state updated successfully.`,
        variant: 'success'
      });
    } catch (err) {
      pushToast({
        title: nextLocked ? 'Lock failed' : 'Unlock failed',
        description: formatApiError(err, `Failed to ${nextLocked ? 'lock' : 'unlock'} section mapping`),
        variant: 'error'
      });
    } finally {
      setLocking(false);
    }
  }

  function scrollToIssues() {
    previewTableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function requestDestinationSelection() {
    destinationPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    window.setTimeout(() => {
      const input = destinationPanelRef.current?.querySelector('input');
      input?.focus();
    }, 150);
  }

  return (
    <div className="page-canvas page-fade mx-auto w-full max-w-[1580px]">
      <div className="page-surface space-y-5 !p-4 lg:!p-5">
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.8fr)_320px] xl:items-start">
          <div className="space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0 flex-1 space-y-2">
                <div className="inline-flex items-center rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
                  Guided Bulk Workflow
                </div>
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h1 className="text-[1.9rem] font-semibold tracking-tight text-slate-950 dark:text-white">{pageTitle}</h1>
                    <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">{pageDescription}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Link className="btn-secondary !rounded-xl !px-3.5 !py-2.5" to="/students">Student Directory</Link>
                    {isAdminMode ? (
                      <Link className="btn-secondary !rounded-xl !px-3.5 !py-2.5" to="/students/section-mapping">Section Mapping</Link>
                    ) : (
                      <Link className="btn-secondary !rounded-xl !px-3.5 !py-2.5" to="/students/bulk-import">Bulk Onboarding</Link>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(330px,0.9fr)] xl:items-start">
              <div className="rounded-[1.4rem] border border-slate-200/80 bg-slate-50/75 p-3.5">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Workflow Progress</p>
                    <p className="mt-1 text-sm text-slate-500">
                      {workflow === 'create_students'
                        ? 'Upload, validate, and import global student records.'
                        : 'Choose the section, validate the roster, and commit only safe rows.'}
                    </p>
                  </div>
                  <div className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-600">
                    Step {currentStep} of {stepItems.length}
                  </div>
                </div>
                <StudentBulkStepIndicator steps={stepItems} currentStep={currentStep} />
              </div>

              {isAdminMode ? (
                <div className="rounded-[1.4rem] border border-slate-200/80 bg-slate-50/75 p-3.5">
                  <StudentBulkModeSwitcher workflow={workflow} onChange={setWorkflow} />
                </div>
              ) : (
                <div className="rounded-[1.4rem] border border-slate-200/80 bg-slate-50/75 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Workflow Mode</p>
                  <h3 className="mt-1 text-base font-semibold text-slate-950 dark:text-white">Map Existing Students</h3>
                  <p className="mt-1 text-sm text-slate-500">
                    Coordinators can map only existing student records into their allowed section. New account creation stays admin-only.
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="rounded-[1.45rem] border border-slate-200/80 bg-gradient-to-br from-slate-50 via-white to-white p-4 shadow-[0_24px_60px_-42px_rgba(15,23,42,0.35)]">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Template Kit</p>
                <h3 className="mt-1 text-base font-semibold text-slate-950 dark:text-white">Use the correct upload sheet</h3>
              </div>
              <div className="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-[11px] font-semibold text-sky-700">
                Safe import
              </div>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-500">{modeCopy.templateHint}</p>
            <button
              type="button"
              className="btn-secondary mt-4 inline-flex w-full items-center justify-center gap-2 !rounded-xl !px-4 !py-2.5"
              onClick={() => (workflow === 'create_students' ? downloadCreateStudentsTemplate() : downloadMapExistingTemplate())}
            >
              <Download size={16} />
              Download upload template
            </button>
            <div className="mt-4 grid gap-2 text-sm text-slate-600">
              <div className="rounded-[1rem] border border-slate-200 bg-white/75 px-3 py-2.5">
                Validation blocks duplicates, unsafe remaps, and incomplete rows before import.
              </div>
              <div className="rounded-[1rem] border border-slate-200 bg-slate-50 px-3 py-2.5">
                {workflow === 'create_students'
                  ? 'Continue into Section Mapping later when placement is ready.'
                  : 'Selected destination and optional group override apply only to valid rows.'}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.85fr)_320px] xl:items-start">
        <div className="page-surface space-y-4 !p-4 lg:!p-5">
          <StudentBulkUploadHero
            workflow={workflow}
            file={file}
            onFileSelect={setFile}
            onRemoveFile={() => setFile(null)}
            disabled={requiresDestination && !selectedSectionId}
            onRequestDestination={requestDestinationSelection}
          />

          <div className="h-px bg-gradient-to-r from-slate-200 via-slate-200 to-transparent" />

          <div className="space-y-3">
            <StudentBulkValidationSummary
              workflow={workflow}
              file={file}
              preview={preview}
              selectedSection={selectedSection ? { ...selectedSection, label: selectedSection.shortLabel || selectedSection.label } : null}
              selectedGroupLabel={selectedGroup?.label}
              onViewIssues={scrollToIssues}
              compact
              embedded
            />

            {isAdminMode && workflow === 'map_existing' ? (
              <label className="inline-flex items-start gap-3 rounded-[1.2rem] border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-900">
                <input
                  type="checkbox"
                  checked={allowAdminOverride}
                  onChange={(event) => setAllowAdminOverride(event.target.checked)}
                  className="mt-1"
                />
                <span>
                  Allow explicit admin override for locked sections or cross-section mappings.
                  <span className="mt-1 block text-xs text-amber-800/80">Use only after review. Every override is audited.</span>
                </span>
              </label>
            ) : null}

            <StudentBulkActionBar
              previewing={previewing}
              committing={committing}
              canCommit={canCommit}
              hasPreview={Boolean(preview)}
              hasFile={Boolean(file)}
              onPreview={handlePreview}
              onCommit={handleCommit}
              compact
              embedded
              previewDisabledReason={previewDisabledReason}
              commitDisabledReason={commitDisabledReason}
            />
          </div>
        </div>

        <div className="space-y-4">
          {requiresDestination ? (
            <DestinationPanel
              panelRef={destinationPanelRef}
              modeCopy={modeCopy}
              sectionOptions={sectionOptions}
              groupOptions={groupOptions}
              selectedSection={selectedSection}
              selectedSectionId={selectedSectionId}
              selectedGroup={selectedGroup}
              selectedGroupId={selectedGroupId}
              loadSections={loadSections}
              loadGroups={loadGroups}
              setSelectedSectionId={setSelectedSectionId}
              setSelectedGroupId={setSelectedGroupId}
              mode={mode}
            />
          ) : (
            <GlobalStudentPanel />
          )}

          {!isAdminMode ? (
            <CoordinatorLockPanel
              selectedSection={selectedSection}
              locking={locking}
              handleLockToggle={handleLockToggle}
            />
          ) : null}
        </div>
      </div>

      {preview ? (
        <div ref={previewTableRef}>
          <PreviewTable preview={preview} />
        </div>
      ) : null}

      <CommitResultCard commitResult={commitResult} workflow={workflow} />
    </div>
  );
}
