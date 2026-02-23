import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock3, FileCheck2, Files, Search } from 'lucide-react';
import Card from '../components/ui/Card';
import FormInput from '../components/ui/FormInput';
import FileUpload from '../components/ui/FileUpload';
import Table from '../components/ui/Table';
import Badge from '../components/ui/Badge';
import { apiClient } from '../services/apiClient';
import { useToast } from '../hooks/useToast';
import { useAuth } from '../hooks/useAuth';

export default function SubmissionsPage() {
  const navigate = useNavigate();
  const { pushToast } = useToast();
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [assignmentIdFilter, setAssignmentIdFilter] = useState('');
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState('idle');
  const [form, setForm] = useState({ assignment_id: '', notes: '', file: null });
  const [assignments, setAssignments] = useState([]);
  const [studentQuery, setStudentQuery] = useState('');
  const [studentStatusFilter, setStudentStatusFilter] = useState('');
  const [bulkRunning, setBulkRunning] = useState(false);
  const canUploadSubmission = user?.role === 'student';
  const canRunAi = user?.role === 'admin' || user?.role === 'teacher';
  const canOpenEvaluationConsole = user?.role === 'admin' || user?.role === 'teacher';
  const canViewTeacherMarks = user?.role === 'admin';
  const isStudent = user?.role === 'student';
  const assignmentLabelById = useMemo(
    () =>
      Object.fromEntries(
        assignments.map((item) => [item.id, item.title ? `${item.title} (${item.id})` : item.id])
      ),
    [assignments]
  );

  const columns = useMemo(
    () => {
      const baseColumns = [
        {
          key: 'assignment_id',
          label: 'Assignment',
          render: (row) => assignmentLabelById[row.assignment_id] || row.assignment_id
        },
        { key: 'original_filename', label: 'File' },
        { key: 'file_size_bytes', label: 'Size (bytes)' },
        { key: 'status', label: 'Status' },
        { key: 'ai_status', label: 'AI Status' },
        { key: 'ai_score', label: 'AI Score', render: (row) => (row.ai_score ?? '-') },
        { key: 'ai_provider', label: 'AI Provider', render: (row) => row.ai_provider || '-' },
        {
          key: 'ai_feedback',
          label: 'AI Feedback',
          render: (row) => {
            const text = row.ai_feedback || '-';
            if (!row.ai_feedback) return text;
            return text.length > 120 ? `${text.slice(0, 120)}...` : text;
          }
        }
      ];

      const marksColumns = canViewTeacherMarks
        ? [
            { key: 'teacher_marks', label: 'Teacher Marks', render: (row) => (row.teacher_marks ?? '-') },
            { key: 'grade', label: 'Grade', render: (row) => (row.grade ?? '-') },
            { key: 'marks_status', label: 'Marks Status', render: (row) => (row.marks_status ?? '-') }
          ]
        : [];

      return [
        ...baseColumns,
        ...marksColumns,
        { key: 'created_at', label: 'Created At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
      ];
    },
    [assignmentLabelById, canViewTeacherMarks]
  );

  const studentColumns = useMemo(
    () => [
      {
        key: 'assignment_id',
        label: 'Assignment',
        render: (row) => assignmentLabelById[row.assignment_id] || row.assignment_id
      },
      { key: 'original_filename', label: 'File' },
      {
        key: 'status',
        label: 'Submission',
        render: (row) => (
          <Badge variant={row.status === 'submitted' ? 'success' : 'default'}>
            {row.status || 'unknown'}
          </Badge>
        )
      },
      {
        key: 'ai_status',
        label: 'AI Review',
        render: (row) => {
          const value = row.ai_status || 'pending';
          const variant = value === 'completed' ? 'success' : value === 'failed' ? 'danger' : value === 'running' ? 'info' : 'warning';
          return <Badge variant={variant}>{value}</Badge>;
        }
      },
      {
        key: 'created_at',
        label: 'Uploaded',
        render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-')
      }
    ],
    [assignmentLabelById]
  );

  useEffect(() => {
    async function loadAssignments() {
      try {
        const response = await apiClient.get('/assignments/', { params: { skip: 0, limit: 100 } });
        setAssignments(response.data || []);
      } catch {
        setAssignments([]);
      }
    }
    loadAssignments();
  }, []);

  async function loadData() {
    setLoading(true);
    setError('');
    try {
      const submissionsResponse = await apiClient.get('/submissions/', {
        params: { assignment_id: assignmentIdFilter || undefined, skip, limit }
      });
      const submissions = submissionsResponse.data || [];

      if (canViewTeacherMarks && submissions.length > 0) {
        const evaluationsResponse = await apiClient.get('/evaluations/', {
          params: { skip: 0, limit: 100 }
        });
        const evaluations = evaluationsResponse.data || [];
        const evaluationBySubmissionId = new Map();
        evaluations.forEach((item) => {
          if (item?.submission_id && !evaluationBySubmissionId.has(item.submission_id)) {
            evaluationBySubmissionId.set(item.submission_id, item);
          }
        });

        const merged = submissions.map((submission) => {
          const evaluation = evaluationBySubmissionId.get(submission.id);
          return {
            ...submission,
            teacher_marks: evaluation?.grand_total ?? null,
            grade: evaluation?.grade ?? null,
            marks_status: evaluation ? (evaluation.is_finalized ? 'Finalized' : 'Draft') : null
          };
        });
        setRows(merged);
      } else {
        setRows(submissions);
      }
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to load submissions';
      setError(String(detail));
      pushToast({ title: 'Load failed', description: String(detail), variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [skip, limit]);

  async function onUpload(event) {
    event.preventDefault();
    if (!form.assignment_id) {
      setError('Please choose an assignment');
      return;
    }
    if (!form.file) {
      setError('Please choose a file before uploading');
      return;
    }

    setUploadStatus('uploading');
    setUploadProgress(20);
    setError('');

    try {
      const multipart = new FormData();
      multipart.append('assignment_id', form.assignment_id);
      if (form.notes) {
        multipart.append('notes', form.notes);
      }
      multipart.append('file', form.file);

      setUploadProgress(60);
      await apiClient.post('/submissions/upload', multipart, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setUploadProgress(100);
      setUploadStatus('success');
      setForm({ assignment_id: '', notes: '', file: null });
      pushToast({ title: 'Upload complete', description: 'Submission uploaded successfully.', variant: 'success' });
      await loadData();
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to upload submission';
      setError(String(detail));
      setUploadStatus('error');
      pushToast({ title: 'Upload failed', description: String(detail), variant: 'error' });
    }
  }

  async function onAiEvaluate(row) {
    try {
      await apiClient.post(`/submissions/${row.id}/ai-evaluate`, null, {
        params: { force: row.ai_status === 'completed' }
      });
      pushToast({ title: 'AI evaluated', description: 'AI suggestion generated for submission.', variant: 'success' });
      await loadData();
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.response?.data?.message || 'Failed to run AI evaluation';
      pushToast({ title: 'AI evaluation failed', description: String(detail), variant: 'error' });
    }
  }

  async function onRunPendingAi() {
    setBulkRunning(true);
    try {
      const response = await apiClient.post('/submissions/ai-evaluate/pending', null, {
        params: {
          assignment_id: assignmentIdFilter || undefined,
          limit: 50
        }
      });
      const count = response?.data?.count ?? 0;
      pushToast({
        title: 'Bulk AI completed',
        description: `${count} pending submissions evaluated.`,
        variant: 'success'
      });
      await loadData();
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.response?.data?.message || 'Failed to run bulk AI evaluation';
      pushToast({ title: 'Bulk AI failed', description: String(detail), variant: 'error' });
    } finally {
      setBulkRunning(false);
    }
  }

  const studentVisibleRows = useMemo(() => {
    return rows.filter((row) => {
      const matchesStatus = !studentStatusFilter || row.status === studentStatusFilter || row.ai_status === studentStatusFilter;
      if (!matchesStatus) return false;
      if (!studentQuery.trim()) return true;
      const q = studentQuery.toLowerCase();
      const hay = `${assignmentLabelById[row.assignment_id] || row.assignment_id || ''} ${row.original_filename || ''}`.toLowerCase();
      return hay.includes(q);
    });
  }, [assignmentLabelById, rows, studentQuery, studentStatusFilter]);

  const studentSummary = useMemo(() => {
    const total = rows.length;
    const submitted = rows.filter((item) => item.status === 'submitted').length;
    const aiDone = rows.filter((item) => item.ai_status === 'completed').length;
    const pendingAi = rows.filter((item) => item.ai_status === 'pending' || item.ai_status === 'running').length;
    return { total, submitted, aiDone, pendingAi };
  }, [rows]);

  if (isStudent) {
    return (
      <div className="space-y-5 page-fade">
        <Card className="space-y-2">
          <h1 className="text-2xl font-semibold">My Submissions</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Upload assignment files, track review progress, and monitor AI status.
          </p>
        </Card>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Card className="!p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Total Files</p>
            <p className="mt-1 text-3xl font-bold">{studentSummary.total}</p>
            <p className="mt-1 inline-flex items-center gap-1 text-xs text-slate-500"><Files size={12} /> All uploads</p>
          </Card>
          <Card className="!p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Submitted</p>
            <p className="mt-1 text-3xl font-bold">{studentSummary.submitted}</p>
            <p className="mt-1 inline-flex items-center gap-1 text-xs text-emerald-600"><FileCheck2 size={12} /> Successfully submitted</p>
          </Card>
          <Card className="!p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">AI Reviewed</p>
            <p className="mt-1 text-3xl font-bold">{studentSummary.aiDone}</p>
            <p className="mt-1 text-xs text-brand-600">Completed AI checks</p>
          </Card>
          <Card className="!p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Pending AI</p>
            <p className="mt-1 text-3xl font-bold">{studentSummary.pendingAi}</p>
            <p className="mt-1 inline-flex items-center gap-1 text-xs text-amber-600"><Clock3 size={12} /> Waiting for processing</p>
          </Card>
        </div>

        <Card className="space-y-4">
          <h2 className="text-lg font-semibold">Upload Assignment</h2>
          <form onSubmit={onUpload} className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-3">
              <FormInput
                as="select"
                label="Assignment"
                name="assignment_id"
                required
                value={form.assignment_id}
                onChange={(e) => setForm((p) => ({ ...p, assignment_id: e.target.value }))}
              >
                <option value="">Select Assignment</option>
                {assignments.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.title || item.id}
                  </option>
                ))}
              </FormInput>
              <FormInput label="Notes (Optional)" name="notes" value={form.notes} onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))} />
              <button className="btn-primary" type="submit">Upload Submission</button>
              <p className="text-xs text-slate-500">Allowed file types: PDF, DOCX, TXT, MD. Max size 10MB.</p>
            </div>
            <FileUpload
              onFileSelect={(file) => setForm((prev) => ({ ...prev, file }))}
              progress={uploadProgress}
              status={uploadStatus}
            />
          </form>
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
        </Card>

        <Card className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold">Submission Records</h2>
            <button className="btn-secondary" onClick={() => { setSkip(0); loadData(); }}>Refresh</button>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="block space-y-1 sm:col-span-2">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Search</span>
              <span className="relative block">
                <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  className="input pl-8"
                  placeholder="Search by assignment or file"
                  value={studentQuery}
                  onChange={(e) => setStudentQuery(e.target.value)}
                />
              </span>
            </label>
            <FormInput as="select" label="Status" value={studentStatusFilter} onChange={(e) => setStudentStatusFilter(e.target.value)}>
              <option value="">All</option>
              <option value="submitted">Submitted</option>
              <option value="pending">AI Pending</option>
              <option value="running">AI Running</option>
              <option value="completed">AI Completed</option>
              <option value="failed">AI Failed</option>
            </FormInput>
          </div>

          {loading ? <p className="text-sm text-slate-500">Loading...</p> : null}
          <Table columns={studentColumns} data={studentVisibleRows} />
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h1 className="text-2xl font-semibold">Submissions</h1>
            {(user?.role === 'teacher' || user?.role === 'admin') ? (
              <p className="text-xs text-slate-500 dark:text-slate-400">
                AI Assisted Evaluation Console open karne ke liye table me <strong>Evaluate</strong> action use karein.
              </p>
            ) : null}
          </div>
          {canRunAi ? (
            <button className="btn-secondary" onClick={onRunPendingAi} disabled={bulkRunning}>
              {bulkRunning ? 'Running AI...' : 'Run AI For Pending'}
            </button>
          ) : null}
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <FormInput
            as="select"
            label="Filter Assignment"
            value={assignmentIdFilter}
            onChange={(e) => setAssignmentIdFilter(e.target.value)}
          >
            <option value="">All Assignments</option>
            {assignments.map((item) => (
              <option key={item.id} value={item.id}>
                {item.title || item.id}
              </option>
            ))}
          </FormInput>
          <div className="flex items-end gap-2">
            <button className="btn-secondary" onClick={() => { setSkip(0); loadData(); }}>Apply</button>
          </div>
        </div>
      </Card>

      {canUploadSubmission ? (
        <Card className="space-y-4">
          <h2 className="text-lg font-semibold">Upload File</h2>
          <form onSubmit={onUpload} className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-3">
              <FormInput
                as="select"
                label="Assignment"
                name="assignment_id"
                required
                value={form.assignment_id}
                onChange={(e) => setForm((p) => ({ ...p, assignment_id: e.target.value }))}
              >
                <option value="">Select Assignment</option>
                {assignments.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.title || item.id}
                  </option>
                ))}
              </FormInput>
              <FormInput label="Notes" name="notes" value={form.notes} onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))} />
              <button className="btn-primary" type="submit">Upload Submission</button>
            </div>
            <FileUpload
              onFileSelect={(file) => setForm((prev) => ({ ...prev, file }))}
              progress={uploadProgress}
              status={uploadStatus}
            />
          </form>
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
        </Card>
      ) : null}

      <Card className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">Submission Records</h2>
          <div className="flex items-center gap-2">
            <button className="btn-secondary" disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - limit))}>Prev</button>
            <span className="text-xs text-slate-500">skip: {skip}</span>
            <button className="btn-secondary" onClick={() => setSkip(skip + limit)}>Next</button>
            <select className="input w-24" value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={20}>20</option>
            </select>
          </div>
        </div>

        {loading ? <p className="text-sm text-slate-500">Loading...</p> : null}
        <Table
          columns={columns}
          data={rows}
          rowActions={
            canRunAi || canOpenEvaluationConsole
              ? [
                  ...(canOpenEvaluationConsole
                    ? [
                        {
                          key: 'evaluate-console',
                          label: 'Evaluate',
                          className: 'text-emerald-700 dark:text-emerald-300',
                          onClick: (row) => navigate(`/submissions/${row.id}/evaluate`)
                        }
                      ]
                    : []),
                  ...(canRunAi
                    ? [
                        {
                          key: 'ai-evaluate',
                          label: 'Run/Rerun AI',
                          className: 'text-brand-600 dark:text-brand-300',
                          onClick: onAiEvaluate
                        }
                      ]
                    : [])
                ]
              : []
          }
        />
      </Card>
    </div>
  );
}
