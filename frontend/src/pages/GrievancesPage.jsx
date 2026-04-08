import React, { useEffect, useMemo, useState } from 'react';
import { CirclePlus } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import Badge from '../components/ui/Badge';
import Card from '../components/ui/Card';
import FileUpload from '../components/ui/FileUpload';
import FormInput from '../components/ui/FormInput';
import Table from '../components/ui/Table';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import {
  addGrievanceComment,
  addGrievanceInternalNote,
  createGrievance,
  forwardGrievance,
  getGrievance,
  listGrievanceForwardTargets,
  listGrievanceInbox,
  listMyGrievances,
  reopenGrievance,
  updateGrievanceStatus
} from '../services/grievancesApi';
import { formatApiError } from '../utils/apiError';

const MODE_CONFIG = {
  student: { title: 'Student Grievances', description: 'Submit new grievances and track replies.', inboxView: null },
  coordinator: { title: 'Coordinator Grievances', description: 'Manage class coordinator grievances.', inboxView: 'coordinator' },
  hod: { title: 'HOD Grievances', description: 'Handle department-level escalations.', inboxView: 'hod' },
  dean: { title: 'Dean Grievances', description: 'Handle dean-level escalations.', inboxView: 'dean' },
  assigned: { title: 'Assigned Grievances', description: 'Work on grievances forwarded to you.', inboxView: 'assigned' },
  fallback: { title: 'Fallback Grievances', description: 'Manually route or resolve failed cases.', inboxView: 'fallback' }
};

const CATEGORY_OPTIONS = ['academic', 'fees', 'facility', 'behavior', 'administration', 'other'];
const STATUS_OPTIONS = ['', 'open', 'in_progress', 'resolved', 'reopened', 'routing_failed'];

function toTitle(value) {
  return String(value || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatTimestamp(value) {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '-' : date.toLocaleString();
}

function statusVariant(status) {
  if (status === 'resolved') return 'success';
  if (status === 'routing_failed') return 'danger';
  if (status === 'reopened') return 'warning';
  if (status === 'in_progress') return 'info';
  return 'default';
}

function eventVariant(kind) {
  if (kind === 'resolved') return 'success';
  if (kind === 'routing_failed') return 'danger';
  if (kind === 'internal_note') return 'warning';
  return 'default';
}

export default function GrievancesPage({ mode = 'student' }) {
  const config = MODE_CONFIG[mode] || MODE_CONFIG.student;
  const isStudentMode = mode === 'student';
  const isStaffMode = !isStudentMode;
  const canForward = ['coordinator', 'hod', 'dean', 'fallback'].includes(mode);
  const canResolve = ['coordinator', 'hod', 'dean', 'fallback'].includes(mode);
  const { user } = useAuth();
  const { pushToast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const highlightedId = searchParams.get('highlight') || searchParams.get('grievance') || '';

  const [rows, setRows] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [filters, setFilters] = useState({ status: '', q: '', onlyOverdue: false });
  const [createForm, setCreateForm] = useState({ category: 'academic', title: '', description: '', attachment: null });
  const [commentMessage, setCommentMessage] = useState('');
  const [internalNoteMessage, setInternalNoteMessage] = useState('');
  const [reopenMessage, setReopenMessage] = useState('');
  const [forwardState, setForwardState] = useState({ targetUserId: '', note: '' });
  const [forwardTargets, setForwardTargets] = useState([]);

  async function loadRows(nextFilters = filters) {
    setLoading(true);
    try {
      const params = {};
      if (nextFilters.status) params.status = nextFilters.status;
      if (nextFilters.q && isStaffMode) params.q = nextFilters.q;
      if (nextFilters.onlyOverdue && isStaffMode) params.only_overdue = true;
      const data = isStudentMode ? await listMyGrievances(params) : await listGrievanceInbox({ ...params, view: config.inboxView });
      setRows(data);
      const nextId =
        (highlightedId && data.some((item) => item.id === highlightedId) && highlightedId) ||
        (selectedId && data.some((item) => item.id === selectedId) && selectedId) ||
        data[0]?.id ||
        '';
      setSelectedId(nextId);
    } catch (err) {
      pushToast({ title: 'Load failed', description: formatApiError(err, 'Failed to load grievances'), variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  async function loadDetail(grievanceId) {
    if (!grievanceId) {
      setSelected(null);
      return;
    }
    setDetailLoading(true);
    try {
      const data = await getGrievance(grievanceId);
      setSelected(data);
      if (highlightedId) {
        const nextParams = new URLSearchParams(searchParams);
        nextParams.delete('highlight');
        nextParams.delete('grievance');
        setSearchParams(nextParams, { replace: true });
      }
    } catch (err) {
      setSelected(null);
      pushToast({ title: 'Load failed', description: formatApiError(err, 'Failed to load grievance detail'), variant: 'error' });
    } finally {
      setDetailLoading(false);
    }
  }

  async function loadForwardTargets() {
    if (!canForward) {
      setForwardTargets([]);
      return;
    }
    try {
      setForwardTargets(await listGrievanceForwardTargets());
    } catch {
      setForwardTargets([]);
    }
  }

  useEffect(() => {
    loadRows(filters);
  }, [mode]);

  useEffect(() => {
    loadDetail(selectedId);
  }, [selectedId]);

  useEffect(() => {
    loadForwardTargets();
  }, [mode]);

  const columns = useMemo(
    () => [
      { key: 'public_id', label: 'ID', render: (row) => row.public_id || row.id },
      { key: 'title', label: 'Title' },
      { key: 'student_label', label: 'Student', render: (row) => row.student_label || '-' },
      { key: 'current_stage', label: 'Stage', render: (row) => toTitle(row.current_stage) },
      { key: 'status', label: 'Status', render: (row) => <Badge variant={statusVariant(row.status)}>{toTitle(row.status)}</Badge> },
      {
        key: 'stage_due_at',
        label: 'Due',
        render: (row) => (
          <div className="space-y-1">
            <div>{formatTimestamp(row.stage_due_at)}</div>
            {row.is_overdue ? <span className="text-xs font-medium text-rose-600">Overdue</span> : null}
          </div>
        )
      }
    ],
    []
  );

  const forwardOptions = useMemo(
    () => forwardTargets.map((item) => ({ value: item.id, label: `${item.full_name} (${item.role}${item.admin_type ? `/${item.admin_type}` : ''})` })),
    [forwardTargets]
  );

  async function refresh(grievanceId, payload = null) {
    await loadRows(filters);
    if (payload) {
      setSelected(payload);
      setSelectedId(payload.id);
    } else if (grievanceId) {
      await loadDetail(grievanceId);
    }
  }

  async function onCreate(event) {
    event.preventDefault();
    setSubmitting(true);
    try {
      const created = await createGrievance(createForm);
      setCreateForm({ category: 'academic', title: '', description: '', attachment: null });
      pushToast({ title: 'Submitted', description: 'Grievance submitted successfully.', variant: 'success' });
      await refresh(created.id, created);
    } catch (err) {
      pushToast({ title: 'Submit failed', description: formatApiError(err, 'Failed to submit grievance'), variant: 'error' });
    } finally {
      setSubmitting(false);
    }
  }

  async function onPublicComment(event) {
    event.preventDefault();
    if (!selectedId || !commentMessage.trim()) return;
    setSubmitting(true);
    try {
      const updated = await addGrievanceComment(selectedId, commentMessage.trim());
      setCommentMessage('');
      pushToast({ title: 'Updated', description: 'Public reply added.', variant: 'success' });
      await refresh(selectedId, updated);
    } catch (err) {
      pushToast({ title: 'Reply failed', description: formatApiError(err, 'Failed to add reply'), variant: 'error' });
    } finally {
      setSubmitting(false);
    }
  }

  async function onInternalNote(event) {
    event.preventDefault();
    if (!selectedId || !internalNoteMessage.trim()) return;
    setSubmitting(true);
    try {
      const updated = await addGrievanceInternalNote(selectedId, internalNoteMessage.trim());
      setInternalNoteMessage('');
      pushToast({ title: 'Saved', description: 'Internal note added.', variant: 'success' });
      await refresh(selectedId, updated);
    } catch (err) {
      pushToast({ title: 'Save failed', description: formatApiError(err, 'Failed to add internal note'), variant: 'error' });
    } finally {
      setSubmitting(false);
    }
  }

  async function onForward(event) {
    event.preventDefault();
    if (!selectedId || !forwardState.targetUserId) return;
    setSubmitting(true);
    try {
      const updated = await forwardGrievance(selectedId, forwardState.targetUserId, forwardState.note.trim());
      setForwardState({ targetUserId: '', note: '' });
      pushToast({ title: 'Forwarded', description: 'Resolver assigned successfully.', variant: 'success' });
      await refresh(selectedId, updated);
    } catch (err) {
      pushToast({ title: 'Forward failed', description: formatApiError(err, 'Failed to forward grievance'), variant: 'error' });
    } finally {
      setSubmitting(false);
    }
  }

  async function onStatusChange(nextStatus) {
    if (!selectedId) return;
    const resolutionNote = nextStatus === 'resolved' ? window.prompt('Add a public resolution note', '') || '' : '';
    setSubmitting(true);
    try {
      const updated = await updateGrievanceStatus(selectedId, nextStatus, resolutionNote);
      pushToast({ title: 'Updated', description: `Grievance marked ${toTitle(nextStatus)}.`, variant: 'success' });
      await refresh(selectedId, updated);
    } catch (err) {
      pushToast({ title: 'Update failed', description: formatApiError(err, 'Failed to update grievance'), variant: 'error' });
    } finally {
      setSubmitting(false);
    }
  }

  async function onReopen(event) {
    event.preventDefault();
    if (!selectedId) return;
    setSubmitting(true);
    try {
      const updated = await reopenGrievance(selectedId, reopenMessage.trim());
      setReopenMessage('');
      pushToast({ title: 'Reopened', description: 'Grievance reopened successfully.', variant: 'success' });
      await refresh(selectedId, updated);
    } catch (err) {
      pushToast({ title: 'Reopen failed', description: formatApiError(err, 'Failed to reopen grievance'), variant: 'error' });
    } finally {
      setSubmitting(false);
    }
  }

  function onBannerCreateClick() {
    pushToast({
      title: 'CREATE',
      description: 'Create button is clickable. The grievance banner shortcut will be connected next.',
      variant: 'info'
    });
  }

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-slate-950 dark:text-white">{config.title}</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">{config.description}</p>
          </div>
          {isStudentMode ? (
            <button
              type="button"
              aria-label="CREATE"
              title="CREATE"
              className="flex w-[62px] shrink-0 flex-col items-center gap-1 rounded-[1.1rem] border border-slate-200/80 bg-white/75 px-2 py-1.5 text-center text-[11px] font-semibold leading-tight text-slate-800 shadow-[inset_0_1px_0_rgba(255,255,255,0.95),0_14px_30px_-22px_rgba(15,23,42,0.45)] backdrop-blur-md transition-all duration-200 hover:-translate-y-0.5 hover:border-sky-300/80 hover:bg-white hover:text-sky-700 hover:shadow-[inset_0_1px_0_rgba(255,255,255,1),0_18px_34px_-20px_rgba(14,165,233,0.35)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:border-slate-700/80 dark:bg-slate-900/70 dark:text-slate-100 dark:shadow-[inset_0_1px_0_rgba(255,255,255,0.04),0_16px_30px_-22px_rgba(2,6,23,0.8)] dark:hover:border-sky-500/70 dark:hover:bg-slate-900 dark:hover:text-sky-300"
              onClick={onBannerCreateClick}
            >
              <CirclePlus size={24} strokeWidth={1.9} />
              <span>CREATE</span>
            </button>
          ) : null}
        </div>
      </Card>

      {isStudentMode ? (
        <Card className="space-y-4">
          <h2 className="text-lg font-semibold text-slate-950 dark:text-white">Submit New Grievance</h2>
          <form className="space-y-4" onSubmit={onCreate}>
            <div className="grid gap-3 md:grid-cols-2">
              <FormInput as="select" label="Category" value={createForm.category} onChange={(event) => setCreateForm((prev) => ({ ...prev, category: event.target.value }))}>
                {CATEGORY_OPTIONS.map((item) => (
                  <option key={item} value={item}>{toTitle(item)}</option>
                ))}
              </FormInput>
              <FormInput label="Title" value={createForm.title} onChange={(event) => setCreateForm((prev) => ({ ...prev, title: event.target.value }))} required />
            </div>
            <FormInput as="textarea" rows={5} label="Description" value={createForm.description} onChange={(event) => setCreateForm((prev) => ({ ...prev, description: event.target.value }))} required />
            <div className="space-y-2">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Attachment</span>
              <FileUpload accept=".png,.jpg,.jpeg,.pdf,.doc,.docx,.txt,.md" onFileSelect={(file) => setCreateForm((prev) => ({ ...prev, attachment: file || null }))} />
              {createForm.attachment ? <p className="text-xs text-slate-500 dark:text-slate-400">Selected: {createForm.attachment.name}</p> : null}
            </div>
            <div className="flex justify-end"><button className="btn-primary" type="submit" disabled={submitting}>{submitting ? 'Submitting...' : 'Submit Grievance'}</button></div>
          </form>
        </Card>
      ) : null}

      <Card className="space-y-4">
        <div className="flex flex-wrap items-end gap-3">
          <FormInput as="select" label="Status" value={filters.status} onChange={(event) => setFilters((prev) => ({ ...prev, status: event.target.value }))}>
            {STATUS_OPTIONS.map((item) => (
              <option key={item} value={item}>{item ? toTitle(item) : 'All Statuses'}</option>
            ))}
          </FormInput>
          {isStaffMode ? <FormInput label="Search" value={filters.q} onChange={(event) => setFilters((prev) => ({ ...prev, q: event.target.value }))} /> : null}
          {isStaffMode ? (
            <label className="mt-5 flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              <input type="checkbox" checked={filters.onlyOverdue} onChange={(event) => setFilters((prev) => ({ ...prev, onlyOverdue: event.target.checked }))} />
              Overdue only
            </label>
          ) : null}
          <button className="btn-secondary mt-5" onClick={() => loadRows(filters)} disabled={loading}>Refresh</button>
        </div>
        {loading ? <p className="text-sm text-slate-500 dark:text-slate-400">Loading grievances...</p> : null}
        <Table columns={columns} data={rows} rowActions={[{ key: 'open', label: (row) => (row.id === selectedId ? 'Opened' : 'Open'), onClick: (row) => setSelectedId(row.id), disabled: (row) => row.id === selectedId }]} />
      </Card>

      <Card className="space-y-4">
        <h2 className="text-lg font-semibold text-slate-950 dark:text-white">Grievance Detail</h2>
        {detailLoading ? <p className="text-sm text-slate-500 dark:text-slate-400">Loading detail...</p> : null}
        {!detailLoading && !selected ? <p className="text-sm text-slate-500 dark:text-slate-400">Select a grievance to inspect the full timeline.</p> : null}
        {!detailLoading && selected ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Badge variant={statusVariant(selected.status)}>{toTitle(selected.status)}</Badge>
              <Badge>{toTitle(selected.current_stage)}</Badge>
              {selected.is_overdue ? <Badge variant="danger">Overdue</Badge> : null}
            </div>
            <div className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
              <div className="text-lg font-semibold text-slate-950 dark:text-white">{selected.title}</div>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{selected.description}</p>
              <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500 dark:text-slate-400">
                <span>Student: {selected.student_label || '-'}</span>
                <span>Section: {selected.section_name || '-'}</span>
                <span>Department: {selected.department_name || '-'}</span>
                <span>Forwarded To: {selected.assigned_resolver_label || '-'}</span>
              </div>
              <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-500 dark:text-slate-400">
                <span>Created: {formatTimestamp(selected.created_at)}</span>
                <span>Due: {formatTimestamp(selected.stage_due_at)}</span>
                <span>Resolved: {formatTimestamp(selected.resolved_at)}</span>
              </div>
              {selected.attachment_url ? <a className="mt-3 inline-flex text-sm font-medium text-brand-700 hover:underline dark:text-brand-300" href={selected.attachment_url} target="_blank" rel="noreferrer">Open Attachment: {selected.attachment_filename || 'Attachment'}</a> : null}
            </div>
            <div className="grid gap-4 xl:grid-cols-[1.35fr_0.95fr]">
              <div className="space-y-3 rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
                {(selected.timeline || []).map((entry) => (
                  <div key={entry.entry_id} className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
                    <div className="flex flex-wrap gap-2">
                      <Badge variant={eventVariant(entry.kind)}>{toTitle(entry.kind)}</Badge>
                      {entry.visibility === 'internal' ? <Badge variant="warning">Internal</Badge> : null}
                      {entry.stage ? <Badge>{toTitle(entry.stage)}</Badge> : null}
                    </div>
                    <p className="mt-3 text-sm text-slate-700 dark:text-slate-200">{entry.message}</p>
                    <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-500 dark:text-slate-400">
                      <span>Actor: {entry.actor_label || 'System'}</span>
                      {entry.forwarded_to_label ? <span>Forwarded To: {entry.forwarded_to_label}</span> : null}
                      <span>{formatTimestamp(entry.created_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="space-y-4">
                <Card className="space-y-3">
                  <form className="space-y-3" onSubmit={onPublicComment}>
                    <FormInput as="textarea" rows={4} label="Public Reply" value={commentMessage} onChange={(event) => setCommentMessage(event.target.value)} />
                    <div className="flex justify-end"><button className="btn-primary" type="submit" disabled={submitting || !commentMessage.trim()}>Add Public Reply</button></div>
                  </form>
                </Card>
                {isStaffMode ? (
                  <Card className="space-y-3">
                    <form className="space-y-3" onSubmit={onInternalNote}>
                      <FormInput as="textarea" rows={4} label="Internal Note" value={internalNoteMessage} onChange={(event) => setInternalNoteMessage(event.target.value)} />
                      <div className="flex justify-end"><button className="btn-secondary" type="submit" disabled={submitting || !internalNoteMessage.trim()}>Save Note</button></div>
                    </form>
                  </Card>
                ) : null}
                {canForward ? (
                  <Card className="space-y-3">
                    <form className="space-y-3" onSubmit={onForward}>
                      <FormInput as="select" label="Forward To" value={forwardState.targetUserId} onChange={(event) => setForwardState((prev) => ({ ...prev, targetUserId: event.target.value }))}>
                        <option value="">Select teacher or admin</option>
                        {forwardOptions.map((item) => (
                          <option key={item.value} value={item.value}>{item.label}</option>
                        ))}
                      </FormInput>
                      <FormInput as="textarea" rows={3} label="Forward Note" value={forwardState.note} onChange={(event) => setForwardState((prev) => ({ ...prev, note: event.target.value }))} />
                      <div className="flex justify-end"><button className="btn-secondary" type="submit" disabled={submitting || !forwardState.targetUserId}>Forward</button></div>
                    </form>
                  </Card>
                ) : null}
                {canResolve ? (
                  <Card className="space-y-3">
                    <div className="flex flex-wrap gap-2">
                      <button className="btn-secondary" type="button" disabled={submitting || selected.status === 'in_progress'} onClick={() => onStatusChange('in_progress')}>Mark In Progress</button>
                      <button className="btn-primary" type="button" disabled={submitting || selected.status === 'resolved'} onClick={() => onStatusChange('resolved')}>Resolve</button>
                    </div>
                  </Card>
                ) : null}
                {isStudentMode && selected.status === 'resolved' ? (
                  <Card className="space-y-3">
                    <form className="space-y-3" onSubmit={onReopen}>
                      <FormInput as="textarea" rows={3} label="Reopen Reason" value={reopenMessage} onChange={(event) => setReopenMessage(event.target.value)} />
                      <div className="flex justify-end"><button className="btn-primary" type="submit" disabled={submitting}>Reopen</button></div>
                    </form>
                  </Card>
                ) : null}
              </div>
            </div>
          </div>
        ) : null}
      </Card>
    </div>
  );
}
