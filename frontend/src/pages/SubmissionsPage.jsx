import { useEffect, useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import FormInput from '../components/ui/FormInput';
import FileUpload from '../components/ui/FileUpload';
import Table from '../components/ui/Table';
import { apiClient } from '../services/apiClient';
import { useToast } from '../hooks/useToast';

export default function SubmissionsPage() {
  const { pushToast } = useToast();
  const [rows, setRows] = useState([]);
  const [assignmentIdFilter, setAssignmentIdFilter] = useState('');
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState('idle');
  const [form, setForm] = useState({ assignment_id: '', notes: '', file: null });

  const columns = useMemo(
    () => [
      { key: 'assignment_id', label: 'Assignment ID' },
      { key: 'original_filename', label: 'File' },
      { key: 'file_size_bytes', label: 'Size (bytes)' },
      { key: 'status', label: 'Status' },
      { key: 'created_at', label: 'Created At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
    ],
    []
  );

  async function loadData() {
    setLoading(true);
    setError('');
    try {
      const response = await apiClient.get('/submissions/', {
        params: { assignment_id: assignmentIdFilter || undefined, skip, limit }
      });
      setRows(response.data);
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

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-4">
        <h1 className="text-2xl font-semibold">Submissions</h1>
        <div className="grid gap-3 sm:grid-cols-3">
          <FormInput
            label="Filter Assignment ID"
            value={assignmentIdFilter}
            onChange={(e) => setAssignmentIdFilter(e.target.value)}
            placeholder="asg-001"
          />
          <div className="flex items-end gap-2">
            <button className="btn-secondary" onClick={() => { setSkip(0); loadData(); }}>Apply</button>
          </div>
        </div>
      </Card>

      <Card className="space-y-4">
        <h2 className="text-lg font-semibold">Upload File</h2>
        <form onSubmit={onUpload} className="grid gap-4 lg:grid-cols-2">
          <div className="space-y-3">
            <FormInput label="Assignment ID" name="assignment_id" required value={form.assignment_id} onChange={(e) => setForm((p) => ({ ...p, assignment_id: e.target.value }))} />
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
        <Table columns={columns} data={rows} />
      </Card>
    </div>
  );
}
