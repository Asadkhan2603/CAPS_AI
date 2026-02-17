import { useCallback, useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';

export default function AssignmentsPage() {
  const { user } = useAuth();
  const { pushToast } = useToast();
  const [pendingToggleIds, setPendingToggleIds] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [sections, setSections] = useState([]);

  useEffect(() => {
    async function loadLookups() {
      try {
        const [subjectsRes, sectionsRes] = await Promise.all([
          apiClient.get('/subjects/', { params: { skip: 0, limit: 100 } }),
          apiClient.get('/sections/', { params: { skip: 0, limit: 100 } })
        ]);
        setSubjects(subjectsRes.data || []);
        setSections(sectionsRes.data || []);
      } catch {
        setSubjects([]);
        setSections([]);
      }
    }
    loadLookups();
  }, []);

  const subjectOptions = useMemo(
    () => subjects.map((subject) => ({ value: subject.id, label: `${subject.name} (${subject.code})` })),
    [subjects]
  );
  const sectionOptions = useMemo(
    () =>
      sections.map((section) => ({
        value: section.id,
        label: `${section.name} (${section.program} - ${section.academic_year})`
      })),
    [sections]
  );
  const subjectNameById = useMemo(
    () => Object.fromEntries(subjectOptions.map((item) => [item.value, item.label])),
    [subjectOptions]
  );
  const sectionNameById = useMemo(
    () => Object.fromEntries(sectionOptions.map((item) => [item.value, item.label])),
    [sectionOptions]
  );

  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search', placeholder: 'Title' },
      { name: 'subject_id', label: 'Subject', type: 'select', options: subjectOptions, placeholder: 'All Subjects' },
      { name: 'section_id', label: 'Section', type: 'select', options: sectionOptions, placeholder: 'All Sections' },
      { name: 'status', label: 'Status', placeholder: 'open / closed' }
    ],
    [sectionOptions, subjectOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'title', label: 'Title', required: true },
      { name: 'description', label: 'Description', nullable: true },
      { name: 'subject_id', label: 'Subject', type: 'select', options: subjectOptions, nullable: true, placeholder: 'No Subject' },
      { name: 'section_id', label: 'Section', type: 'select', options: sectionOptions, nullable: true, placeholder: 'No Section' },
      { name: 'due_date', label: 'Deadline', type: 'datetime', nullable: true },
      { name: 'total_marks', label: 'Total Marks', type: 'number', min: 1, max: 1000, defaultValue: 100, required: true },
      { name: 'status', label: 'Status', defaultValue: 'open', required: true },
      { name: 'plagiarism_enabled', label: 'Plagiarism Enabled', type: 'switch', defaultValue: true, required: true }
    ],
    [sectionOptions, subjectOptions]
  );

  const onTogglePlagiarism = useCallback(async (row, nextValue) => {
    setPendingToggleIds((prev) => (prev.includes(row.id) ? prev : [...prev, row.id]));
    try {
      await apiClient.patch(`/assignments/${row.id}/plagiarism`, {
        plagiarism_enabled: nextValue
      });
      pushToast({
        title: 'Assignment updated',
        description: `Plagiarism ${nextValue ? 'enabled' : 'disabled'} for this assignment.`,
        variant: 'success'
      });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to update plagiarism toggle';
      pushToast({ title: 'Update failed', description: String(detail), variant: 'error' });
      throw err;
    } finally {
      setPendingToggleIds((prev) => prev.filter((id) => id !== row.id));
    }
  }, [pushToast]);

  const columns = useMemo(
    () => [
      { key: 'title', label: 'Title' },
      { key: 'subject_id', label: 'Subject', render: (row) => subjectNameById[row.subject_id] || row.subject_id || '-' },
      { key: 'section_id', label: 'Section', render: (row) => sectionNameById[row.section_id] || row.section_id || '-' },
      { key: 'due_date', label: 'Deadline', render: (row) => (row.due_date ? new Date(row.due_date).toLocaleString() : '-') },
      { key: 'total_marks', label: 'Marks' },
      { key: 'status', label: 'Status' },
      {
        key: 'plagiarism_enabled',
        label: 'Plagiarism',
        render: (row) => {
          if (user?.role !== 'teacher') {
            return row.plagiarism_enabled ? 'Enabled' : 'Disabled';
          }
          const checked = Boolean(row.plagiarism_enabled);
          const pending = pendingToggleIds.includes(row.id);
          return (
            <label className="inline-flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                className="peer sr-only"
                defaultChecked={checked}
                disabled={pending}
                onChange={async (e) => {
                  const input = e.target;
                  const nextValue = input.checked;
                  try {
                    await onTogglePlagiarism(row, nextValue);
                  } catch {
                    input.checked = !nextValue;
                  }
                }}
              />
              <span className="relative h-6 w-11 rounded-full bg-slate-300 transition-colors after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-transform after:content-[''] peer-checked:bg-brand-500 peer-checked:after:translate-x-5 peer-disabled:cursor-not-allowed peer-disabled:opacity-60 dark:bg-slate-700" />
              <span className="text-xs text-slate-600 dark:text-slate-300">{pending ? 'Saving...' : 'On/Off'}</span>
            </label>
          );
        }
      }
    ],
    [onTogglePlagiarism, pendingToggleIds, sectionNameById, subjectNameById, user?.role]
  );

  return (
    <EntityManager
      title="Assignments"
      endpoint="/assignments/"
      filters={filters}
      createFields={createFields}
      columns={columns}
      enableDelete
      createTransform={(payload) => ({
        ...payload,
        plagiarism_enabled: Boolean(payload.plagiarism_enabled)
      })}
    />
  );
}
