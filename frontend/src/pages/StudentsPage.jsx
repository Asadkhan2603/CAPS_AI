import { useEffect, useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import EntityManager from '../components/ui/EntityManager';
import Modal from '../components/ui/Modal';
import { apiClient } from '../services/apiClient';
import { getSections } from '../services/sectionsApi';
import { useToast } from '../hooks/useToast';
import { formatApiError } from '../utils/apiError';

function prettyLabel(value) {
  return String(value || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function countByCollection(referenceCounts = []) {
  return referenceCounts.reduce((total, entry) => total + Number(entry.count || 0), 0);
}

export default function StudentsPage() {
  const { pushToast } = useToast();
  const [sections, setSections] = useState([]);
  const [groups, setGroups] = useState([]);
  const [duplicateAudit, setDuplicateAudit] = useState(null);
  const [duplicateCases, setDuplicateCases] = useState([]);
  const [entityRefreshKey, setEntityRefreshKey] = useState(0);
  const [mergeModalOpen, setMergeModalOpen] = useState(false);
  const [activeMergeCase, setActiveMergeCase] = useState(null);
  const [mergePreview, setMergePreview] = useState(null);
  const [mergePrimaryId, setMergePrimaryId] = useState('');
  const [mergeForm, setMergeForm] = useState(null);
  const [mergeReason, setMergeReason] = useState('');
  const [mergeLoading, setMergeLoading] = useState(false);
  const [mergeSaving, setMergeSaving] = useState(false);
  const [mergeError, setMergeError] = useState('');

  async function loadStudentContext() {
    try {
      const [sectionsRes, groupsRes, duplicateAuditRes, duplicateCasesRes] = await Promise.allSettled([
        getSections({ skip: 0, limit: 100 }),
        apiClient.get('/groups/', { params: { skip: 0, limit: 100, is_active: true } }),
        apiClient.get('/students/duplicate-audit'),
        apiClient.get('/students/duplicate-cases', { params: { limit: 12 } })
      ]);
      setSections(sectionsRes.status === 'fulfilled' ? sectionsRes.value.data || [] : []);
      setGroups(groupsRes.status === 'fulfilled' ? groupsRes.value.data || [] : []);
      setDuplicateAudit(duplicateAuditRes.status === 'fulfilled' ? duplicateAuditRes.value.data || null : null);
      setDuplicateCases(duplicateCasesRes.status === 'fulfilled' ? duplicateCasesRes.value.data || [] : []);
    } catch {
      setSections([]);
      setGroups([]);
      setDuplicateAudit(null);
      setDuplicateCases([]);
    }
  }

  useEffect(() => {
    loadStudentContext();
  }, []);

  async function loadMergePreview(caseItem, preferredPrimaryStudentId = null) {
    if (!caseItem?.member_student_ids?.length) {
      return;
    }
    setMergeLoading(true);
    setMergeError('');
    try {
      const response = await apiClient.post('/students/merge/preview', {
        seed_student_ids: caseItem.member_student_ids,
        preferred_primary_student_id: preferredPrimaryStudentId
      });
      const preview = response.data;
      setMergePreview(preview);
      setMergePrimaryId(preview.suggested_primary_student_id || '');
      setMergeForm(preview.resolved_profile || null);
    } catch (error) {
      const message = formatApiError(error, 'Failed to load merge preview');
      setMergeError(message);
      pushToast({ title: 'Merge preview failed', description: message, variant: 'error' });
    } finally {
      setMergeLoading(false);
    }
  }

  function openMergeCase(caseItem) {
    setActiveMergeCase(caseItem);
    setMergeModalOpen(true);
    setMergePreview(null);
    setMergePrimaryId('');
    setMergeForm(null);
    setMergeReason('');
    setMergeError('');
    loadMergePreview(caseItem);
  }

  function closeMergeModal() {
    setMergeModalOpen(false);
    setActiveMergeCase(null);
    setMergePreview(null);
    setMergePrimaryId('');
    setMergeForm(null);
    setMergeReason('');
    setMergeError('');
    setMergeLoading(false);
    setMergeSaving(false);
  }

  const sectionOptions = useMemo(
    () =>
      sections.map((item) => ({
        value: item.id,
        label: item.name
      })),
    [sections]
  );

  const sectionNameById = useMemo(
    () => Object.fromEntries(sectionOptions.map((item) => [item.value, item.label])),
    [sectionOptions]
  );
  const groupOptions = useMemo(
    () =>
      groups.map((item) => ({
        value: item.id,
        label: item.name,
        section_id: item.section_id
      })),
    [groups]
  );
  const groupNameById = useMemo(
    () => Object.fromEntries(groups.map((item) => [item.id, item.name])),
    [groups]
  );

  const mergeGroupOptions = useMemo(() => {
    if (!mergeForm?.class_id) {
      return groupOptions;
    }
    return groupOptions.filter((item) => String(item.section_id) === String(mergeForm.class_id));
  }, [groupOptions, mergeForm?.class_id]);

  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search', placeholder: 'Name / roll / email' },
      { name: 'class_id', label: 'Section', type: 'select', options: sectionOptions, placeholder: 'All Sections' },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [sectionOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'full_name', label: 'Full Name', required: true },
      { name: 'roll_number', label: 'Roll Number', required: true },
      { name: 'email', label: 'Email', nullable: true },
      { name: 'class_id', label: 'Section', type: 'select', options: sectionOptions, nullable: true, placeholder: 'No Section' },
      {
        name: 'group_id',
        label: 'Group',
        type: 'select',
        options: groupOptions,
        nullable: true,
        placeholder: 'No Group',
        dependsOn: 'class_id',
        optionMatchKey: 'section_id',
        requireParentSelection: true
      }
    ],
    [groupOptions, sectionOptions]
  );

  const editFields = useMemo(
    () => [
      ...createFields,
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: true }
    ],
    [createFields]
  );

  const columns = useMemo(
    () => [
      { key: 'full_name', label: 'Name' },
      { key: 'roll_number', label: 'Roll Number' },
      { key: 'email', label: 'Email' },
      {
        key: 'class_id',
        label: 'Section',
        render: (row) => {
          const canonical = row.canonical_class_id || row.class_id;
          const label = sectionNameById[canonical] || canonical || '-';
          return row.placement_source === 'enrollment' && row.class_id && row.class_id !== row.canonical_class_id ? `${label} (Enrollment)` : label;
        }
      },
      { key: 'group_id', label: 'Group', render: (row) => groupNameById[row.group_id] || row.group_id || '-' },
      { key: 'is_active', label: 'Active', render: (row) => (row.is_active ? 'Yes' : 'No') }
    ],
    [groupNameById, sectionNameById]
  );

  function updateMergeForm(fieldName, value) {
    setMergeForm((current) => {
      if (!current) {
        return current;
      }
      if (fieldName === 'class_id') {
        return {
          ...current,
          class_id: value || null,
          group_id: null
        };
      }
      return {
        ...current,
        [fieldName]: value || null
      };
    });
  }

  async function handlePrimaryChange(nextPrimaryId) {
    setMergePrimaryId(nextPrimaryId);
    if (activeMergeCase) {
      await loadMergePreview(activeMergeCase, nextPrimaryId);
    }
  }

  async function handleMergeExecute() {
    if (!mergePreview || !mergeForm) {
      return;
    }
    setMergeSaving(true);
    setMergeError('');
    try {
      const response = await apiClient.post('/students/merge/execute', {
        primary_student_id: mergePrimaryId,
        duplicate_student_ids: (mergePreview.member_student_ids || []).filter((studentId) => studentId !== mergePrimaryId),
        resolved_profile: {
          ...mergeForm,
          is_active: true
        },
        reason: mergeReason,
        confirm_hard_delete: true
      });
      pushToast({
        title: 'Student profiles merged',
        description: `Deleted ${response.data.deleted_student_ids?.length || 0} duplicate profiles and kept one canonical student record.`,
        variant: 'success'
      });
      closeMergeModal();
      await loadStudentContext();
      setEntityRefreshKey((value) => value + 1);
    } catch (error) {
      const message = formatApiError(error, 'Failed to execute student merge');
      setMergeError(message);
      pushToast({ title: 'Student merge failed', description: message, variant: 'error' });
    } finally {
      setMergeSaving(false);
    }
  }

  return (
    <div className="space-y-3">
      {duplicateAudit ? (
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            {[
              ['Total Students', duplicateAudit.summary?.total_students || 0],
              ['Duplicate Groups', duplicateAudit.summary?.duplicate_groups || 0],
              ['Roll Duplicates', duplicateAudit.summary?.roll_number_groups || 0],
              ['Email Duplicates', duplicateAudit.summary?.email_groups || 0],
              ['User Link Duplicates', duplicateAudit.summary?.user_id_groups || 0],
            ].map(([label, value]) => (
              <Card key={label} className="!p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
                <p className="mt-1 text-2xl font-semibold">{value}</p>
              </Card>
            ))}
          </div>

          <Card className="space-y-3">
            <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <h2 className="text-lg font-semibold">Duplicate Audit</h2>
                <p className="text-sm text-slate-500">
                  These student profiles share the same roll number, email, or linked student user. Review and merge them before they fragment attendance, results, enrollments, or grievances.
                </p>
              </div>
              <button type="button" className="btn-secondary" onClick={loadStudentContext}>
                Refresh Audit
              </button>
            </div>

            {duplicateCases?.length ? (
              <div className="grid gap-3 xl:grid-cols-2">
                {duplicateCases.map((caseItem) => (
                  <div key={caseItem.case_id} className="rounded-2xl border border-slate-200 px-4 py-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <h3 className="font-medium text-slate-900">Merge Case</h3>
                        <p className="text-sm text-slate-500">
                          Linked by {caseItem.matched_by?.map(prettyLabel).join(', ') || 'duplicate signals'}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
                          {caseItem.member_student_ids?.length || 0} profiles
                        </span>
                        <button type="button" className="btn-primary" onClick={() => openMergeCase(caseItem)}>
                          Review Merge
                        </button>
                      </div>
                    </div>

                    <div className="mt-3 grid gap-3 sm:grid-cols-3">
                      <div className="rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Suggested Primary</p>
                        <p className="mt-1 text-sm font-medium text-slate-900">
                          {caseItem.members?.find((member) => member.id === caseItem.suggested_primary_student_id)?.full_name || 'Suggested primary'}
                        </p>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Conflicts</p>
                        <p className="mt-1 text-sm font-medium text-slate-900">{caseItem.conflicts?.length || 0} fields</p>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2">
                        <p className="text-xs uppercase tracking-wide text-slate-500">References</p>
                        <p className="mt-1 text-sm font-medium text-slate-900">{countByCollection(caseItem.reference_counts)} linked rows</p>
                      </div>
                    </div>

                    <div className="mt-3 space-y-2">
                      {(caseItem.members || []).slice(0, 4).map((student) => (
                        <div key={student.id} className="rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2 text-sm">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="font-medium text-slate-900">{student.full_name}</p>
                              <p className="text-xs text-slate-500">
                                Roll {student.roll_number || '-'} - Email {student.email || '-'}
                              </p>
                              <p className="text-xs text-slate-500">
                                User {student.user_id || '-'} - Section {sectionNameById[student.class_id] || student.class_id || 'None'}
                              </p>
                            </div>
                            {student.id === caseItem.suggested_primary_student_id ? (
                              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                                Suggested primary
                              </span>
                            ) : null}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm text-emerald-800">
                No duplicate merge cases are currently available for admin resolution.
              </div>
            )}
          </Card>
        </div>
      ) : null}

      <EntityManager
        key={`students-${entityRefreshKey}`}
        title="Students"
        endpoint="/students/"
        filters={filters}
        createFields={createFields}
        editFields={editFields}
        columns={columns}
        enableEdit
        enableDelete
        createTransform={(payload) => ({
          ...payload,
          email: payload.email || null,
          class_id: payload.class_id || null,
          group_id: payload.group_id || null
        })}
        updateTransform={(payload) => ({
          ...payload,
          email: payload.email || null,
          class_id: payload.class_id || null,
          group_id: payload.group_id || null
        })}
      />

      <Modal open={mergeModalOpen} title="Merge Student Profiles" onClose={closeMergeModal} size="large">
        <div className="space-y-4">
          {mergeLoading ? (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-600">
              Loading merge preview...
            </div>
          ) : null}

          {mergeError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-700">
              {mergeError}
            </div>
          ) : null}

          {mergePreview && mergeForm ? (
            <>
              <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-800">
                This merge rewrites student-linked records across the academic module and permanently deletes the losing profiles after verification succeeds.
              </div>

              {mergePreview.warnings?.length ? (
                <Card className="space-y-2">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">Warnings</h3>
                  <div className="space-y-1 text-sm text-slate-600">
                    {mergePreview.warnings.map((warning) => (
                      <p key={warning}>- {warning}</p>
                    ))}
                  </div>
                </Card>
              ) : null}

              <div className="grid gap-4 xl:grid-cols-[1.3fr_1fr]">
                <Card className="space-y-3">
                  <div>
                    <h3 className="text-base font-semibold">Primary Profile</h3>
                    <p className="text-sm text-slate-500">
                      Pick the canonical student record, then adjust any conflicting profile fields before the merge runs.
                    </p>
                  </div>
                  <div className="space-y-2">
                    {(mergePreview.members || []).map((member) => (
                      <label key={member.id} className="flex cursor-pointer items-start gap-3 rounded-2xl border border-slate-200 px-3 py-3">
                        <input
                          type="radio"
                          name="merge-primary"
                          checked={mergePrimaryId === member.id}
                          onChange={() => handlePrimaryChange(member.id)}
                          className="mt-1"
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-medium text-slate-900">{member.full_name}</p>
                            {member.id === mergePreview.suggested_primary_student_id ? (
                              <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
                                Suggested
                              </span>
                            ) : null}
                            {!member.is_active ? (
                              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                                Inactive
                              </span>
                            ) : null}
                          </div>
                          <p className="text-xs text-slate-500">
                            Roll {member.roll_number || '-'} - Email {member.email || '-'}
                          </p>
                          <p className="text-xs text-slate-500">
                            User {member.user_id || '-'} - Section {sectionNameById[member.class_id] || member.class_id || 'None'}
                          </p>
                        </div>
                      </label>
                    ))}
                  </div>
                </Card>

                <Card className="space-y-3">
                  <div>
                    <h3 className="text-base font-semibold">Reference Impact</h3>
                    <p className="text-sm text-slate-500">
                      These rows will be rewritten or deduplicated before the losing student profiles are deleted.
                    </p>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {(mergePreview.reference_counts || []).map((entry) => (
                      <div key={entry.collection} className="rounded-2xl border border-slate-200 bg-slate-50/70 px-3 py-3">
                        <p className="text-xs uppercase tracking-wide text-slate-500">{prettyLabel(entry.collection)}</p>
                        <p className="mt-1 text-xl font-semibold text-slate-900">{entry.count}</p>
                      </div>
                    ))}
                    {!mergePreview.reference_counts?.length ? (
                      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm text-emerald-800 sm:col-span-2">
                        No linked student-id rows need rewriting for this merge case.
                      </div>
                    ) : null}
                  </div>
                  <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-700">
                    Hard delete target: {(mergePreview.hard_delete_ids || []).length} duplicate student profiles.
                  </div>
                </Card>
              </div>

              <Card className="space-y-3">
                <div>
                  <h3 className="text-base font-semibold">Resolved Canonical Profile</h3>
                  <p className="text-sm text-slate-500">
                    Admin-reviewed fields define the single surviving student profile after merge.
                  </p>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-700">Full Name</span>
                    <input className="w-full rounded-xl border border-slate-300 px-3 py-2" value={mergeForm.full_name || ''} onChange={(event) => updateMergeForm('full_name', event.target.value)} />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-700">Roll Number</span>
                    <input className="w-full rounded-xl border border-slate-300 px-3 py-2" value={mergeForm.roll_number || ''} onChange={(event) => updateMergeForm('roll_number', event.target.value)} />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-700">Email</span>
                    <input className="w-full rounded-xl border border-slate-300 px-3 py-2" value={mergeForm.email || ''} onChange={(event) => updateMergeForm('email', event.target.value)} />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-700">Student User ID</span>
                    <input className="w-full rounded-xl border border-slate-300 px-3 py-2" value={mergeForm.user_id || ''} onChange={(event) => updateMergeForm('user_id', event.target.value)} />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-700">Section</span>
                    <select className="w-full rounded-xl border border-slate-300 px-3 py-2" value={mergeForm.class_id || ''} onChange={(event) => updateMergeForm('class_id', event.target.value)}>
                      <option value="">No Section</option>
                      {sectionOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-700">Group</span>
                    <select className="w-full rounded-xl border border-slate-300 px-3 py-2" value={mergeForm.group_id || ''} onChange={(event) => updateMergeForm('group_id', event.target.value)}>
                      <option value="">No Group</option>
                      {mergeGroupOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                {mergePreview.conflicts?.length ? (
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                    <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-600">Detected Conflicts</h4>
                    <div className="mt-3 space-y-3">
                      {mergePreview.conflicts.map((conflict) => (
                        <div key={conflict.field} className="rounded-xl border border-slate-200 bg-white px-3 py-3">
                          <p className="font-medium text-slate-900">{prettyLabel(conflict.field)}</p>
                          <div className="mt-2 space-y-1 text-sm text-slate-600">
                            {conflict.values.map((value, index) => (
                              <p key={`${conflict.field}-${value.value || 'empty'}-${index}`}>
                                {value.value || '(empty)'} - {value.student_ids.length} profile(s)
                              </p>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </Card>

              <Card className="space-y-3">
                <label className="space-y-1 text-sm">
                  <span className="font-medium text-slate-700">Merge reason</span>
                  <textarea
                    className="min-h-28 w-full rounded-2xl border border-slate-300 px-3 py-2"
                    placeholder="Explain why these profiles are duplicates and why this canonical profile is correct."
                    value={mergeReason}
                    onChange={(event) => setMergeReason(event.target.value)}
                  />
                </label>
                <div className="flex flex-wrap items-center justify-end gap-2">
                  <button type="button" className="btn-secondary" onClick={closeMergeModal} disabled={mergeSaving}>
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={mergeSaving || mergeLoading || !mergeReason.trim() || !mergePrimaryId}
                    onClick={handleMergeExecute}
                  >
                    {mergeSaving ? 'Merging...' : 'Merge and Hard Delete Duplicates'}
                  </button>
                </div>
              </Card>
            </>
          ) : null}
        </div>
      </Modal>
    </div>
  );
}
