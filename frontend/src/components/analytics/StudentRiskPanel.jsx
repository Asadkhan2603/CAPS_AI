import { useEffect, useState } from 'react';
import { useToast } from '../../hooks/useToast';
import { apiClient } from '../../services/apiClient';
import { formatApiError } from '../../utils/apiError';
import Badge from '../ui/Badge';
import Card from '../ui/Card';

function toneForLevel(level) {
  if (level === 'critical') return 'danger';
  if (level === 'attention') return 'warning';
  return 'success';
}

function toneForInterventionStatus(status) {
  if (status === 'resolved') return 'success';
  if (status === 'in_progress') return 'info';
  return 'warning';
}

function Metric({ label, value }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-2xl font-semibold">{value ?? 0}</p>
    </Card>
  );
}

export default function StudentRiskPanel({ title = 'Student Risk Dashboard', subtitle, riskData, loading = false, error = '' }) {
  const { pushToast } = useToast();
  const [panelData, setPanelData] = useState(riskData || null);
  const [actionBusyId, setActionBusyId] = useState('');
  const [composerItemId, setComposerItemId] = useState('');
  const [composerNote, setComposerNote] = useState('');
  const [composerDueDate, setComposerDueDate] = useState('');
  const [actionError, setActionError] = useState('');

  useEffect(() => {
    setPanelData(riskData || null);
  }, [riskData]);

  const summary = panelData?.summary || {};
  const items = panelData?.items || [];

  async function refreshPanelData() {
    const response = await apiClient.get('/analytics/student-risk');
    setPanelData(response.data || null);
  }

  async function handleCreateIntervention(item) {
    if (!composerNote.trim()) {
      setActionError('Add a short outreach note before creating the intervention.');
      return;
    }

    setActionBusyId(item.student_id);
    setActionError('');
    try {
      await apiClient.post('/analytics/student-risk/interventions', {
        student_id: item.student_id,
        section_id: item.section_id,
        risk_level: item.risk_level,
        note: composerNote.trim(),
        due_date: composerDueDate ? new Date(`${composerDueDate}T12:00:00`).toISOString() : null,
        reason_summary: item.reasons || []
      });
      await refreshPanelData();
      setComposerItemId('');
      setComposerNote('');
      setComposerDueDate('');
      pushToast({
        title: 'Intervention created',
        description: `Follow-up created for ${item.student_name}.`,
        variant: 'success'
      });
    } catch (err) {
      const message = formatApiError(err, 'Failed to create intervention');
      setActionError(message);
      pushToast({
        title: 'Could not create intervention',
        description: message,
        variant: 'error'
      });
    } finally {
      setActionBusyId('');
    }
  }

  async function handleUpdateIntervention(interventionId, nextStatus, studentName) {
    setActionBusyId(interventionId);
    setActionError('');
    try {
      await apiClient.patch(`/analytics/student-risk/interventions/${interventionId}`, {
        status: nextStatus,
        resolution_note:
          nextStatus === 'resolved'
            ? 'Resolved from the student risk dashboard after outreach review.'
            : null
      });
      await refreshPanelData();
      pushToast({
        title: nextStatus === 'resolved' ? 'Intervention resolved' : 'Intervention updated',
        description:
          nextStatus === 'resolved'
            ? `${studentName} has been marked resolved.`
            : `${studentName} is now marked in progress.`,
        variant: 'success'
      });
    } catch (err) {
      const message = formatApiError(err, 'Failed to update intervention');
      setActionError(message);
      pushToast({
        title: 'Could not update intervention',
        description: message,
        variant: 'error'
      });
    } finally {
      setActionBusyId('');
    }
  }

  return (
    <div className="space-y-4">
      <Card className="space-y-2">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">{title}</h2>
            <p className="text-sm text-slate-500">{subtitle || 'Prioritize outreach using overdue work, evaluation trends, and AI flags.'}</p>
          </div>
          {riskData?.generated_at ? (
            <p className="text-xs text-slate-500">
              Updated {new Date(riskData.generated_at).toLocaleString()}
            </p>
          ) : null}
        </div>
      </Card>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Metric label="Critical Students" value={summary.critical_students} />
        <Metric label="Attention Needed" value={summary.attention_students} />
        <Metric label="Sections Impacted" value={summary.sections_impacted} />
        <Metric label="Open Interventions" value={summary.open_interventions} />
      </div>

      {loading ? (
        <Card>
          <p className="text-sm text-slate-500">Loading student risk signals...</p>
        </Card>
      ) : null}

      {error ? (
        <Card>
          <p className="text-sm text-rose-600">{error}</p>
        </Card>
      ) : null}

      {actionError ? (
        <Card>
          <p className="text-sm text-rose-600">{actionError}</p>
        </Card>
      ) : null}

      {!loading && !error ? (
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Intervention Queue</h3>
            <span className="text-xs text-slate-500">{items.length} student{items.length === 1 ? '' : 's'} surfaced</span>
          </div>
          {items.length === 0 ? (
            <p className="text-sm text-slate-500">No students are currently flagged for intervention in this scope.</p>
          ) : (
            <div className="space-y-3">
              {items.map((item) => (
                <div key={`${item.section_id}-${item.student_id}`} className="rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-base font-semibold">{item.student_name}</p>
                        <Badge variant={toneForLevel(item.risk_level)}>{item.risk_level}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-slate-500">
                        {item.roll_number || '-'} | {item.section_name || '-'}
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-500">
                      <span>Overdue: <span className="font-semibold text-slate-800 dark:text-slate-100">{item.overdue_assignments ?? 0}</span></span>
                      <span>Score: <span className="font-semibold text-slate-800 dark:text-slate-100">{item.latest_grand_total ?? '-'}</span></span>
                      <span>Attendance: <span className="font-semibold text-slate-800 dark:text-slate-100">{item.latest_attendance_percent ?? '-'}{item.latest_attendance_percent != null ? '%' : ''}</span></span>
                      <span>AI Flags: <span className="font-semibold text-slate-800 dark:text-slate-100">{(item.ai_risk_flags || []).length}</span></span>
                    </div>
                  </div>

                  {item.latest_intervention ? (
                    <div className="mt-3 rounded-2xl border border-sky-200 bg-sky-50/70 p-3 dark:border-sky-900/40 dark:bg-sky-950/20">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-slate-900 dark:text-slate-50">Active Follow-up</p>
                        <Badge variant={toneForInterventionStatus(item.latest_intervention.status)}>
                          {String(item.latest_intervention.status || 'open').replaceAll('_', ' ')}
                        </Badge>
                      </div>
                      <p className="mt-2 text-sm text-slate-700 dark:text-slate-200">
                        {item.latest_intervention.note || 'No note provided.'}
                      </p>
                      <p className="mt-2 text-xs text-slate-500">
                        Owner: {item.latest_intervention.owner_name || '-'}
                        {item.latest_intervention.due_date
                          ? ` | Due ${new Date(item.latest_intervention.due_date).toLocaleDateString()}`
                          : ''}
                      </p>
                      {item.latest_intervention.resolution_note ? (
                        <p className="mt-1 text-xs text-slate-500">
                          Resolution: {item.latest_intervention.resolution_note}
                        </p>
                      ) : null}
                      {item.latest_intervention.status === 'open' ? (
                        <div className="mt-3 flex flex-wrap gap-2">
                          <button
                            type="button"
                            className="btn-secondary"
                            disabled={actionBusyId === item.latest_intervention.id}
                            onClick={() =>
                              handleUpdateIntervention(
                                item.latest_intervention.id,
                                'in_progress',
                                item.student_name
                              )
                            }
                          >
                            Start Work
                          </button>
                          <button
                            type="button"
                            className="btn-primary"
                            disabled={actionBusyId === item.latest_intervention.id}
                            onClick={() =>
                              handleUpdateIntervention(
                                item.latest_intervention.id,
                                'resolved',
                                item.student_name
                              )
                            }
                          >
                            Mark Resolved
                          </button>
                        </div>
                      ) : null}
                      {item.latest_intervention.status === 'in_progress' ? (
                        <div className="mt-3">
                          <button
                            type="button"
                            className="btn-primary"
                            disabled={actionBusyId === item.latest_intervention.id}
                            onClick={() =>
                              handleUpdateIntervention(
                                item.latest_intervention.id,
                                'resolved',
                                item.student_name
                              )
                            }
                          >
                            Mark Resolved
                          </button>
                        </div>
                      ) : null}
                    </div>
                  ) : null}

                  {(item.reasons || []).length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {item.reasons.map((reason) => (
                        <span key={reason} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                          {reason}
                        </span>
                      ))}
                    </div>
                  ) : null}

                  <div className="mt-3 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-950/20 dark:text-amber-100">
                    {item.recommended_action}
                  </div>

                  {item.can_create_intervention ? (
                    <div className="mt-3 space-y-3">
                      {composerItemId === item.student_id ? (
                        <div className="rounded-2xl border border-slate-200 p-3 dark:border-slate-700">
                          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">
                            Follow-up note
                          </label>
                          <textarea
                            className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-950"
                            rows={3}
                            value={composerNote}
                            onChange={(event) => setComposerNote(event.target.value)}
                            placeholder="Capture the outreach plan, owner context, or coordinator handoff."
                          />
                          <label className="mt-3 block text-sm font-medium text-slate-700 dark:text-slate-200">
                            Target due date
                          </label>
                          <input
                            type="date"
                            className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-950"
                            value={composerDueDate}
                            onChange={(event) => setComposerDueDate(event.target.value)}
                          />
                          <div className="mt-3 flex flex-wrap gap-2">
                            <button
                              type="button"
                              className="btn-primary"
                              disabled={actionBusyId === item.student_id}
                              onClick={() => handleCreateIntervention(item)}
                            >
                              Save Follow-up
                            </button>
                            <button
                              type="button"
                              className="btn-secondary"
                              disabled={actionBusyId === item.student_id}
                              onClick={() => {
                                setComposerItemId('');
                                setComposerNote('');
                                setComposerDueDate('');
                                setActionError('');
                              }}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={() => {
                            setComposerItemId(item.student_id);
                            setComposerNote('');
                            setComposerDueDate('');
                            setActionError('');
                          }}
                        >
                          Create Follow-up
                        </button>
                      )}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </Card>
      ) : null}
    </div>
  );
}
