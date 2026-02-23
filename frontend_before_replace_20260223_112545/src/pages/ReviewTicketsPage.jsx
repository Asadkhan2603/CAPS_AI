import { useEffect, useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import FormInput from '../components/ui/FormInput';
import Table from '../components/ui/Table';
import { apiClient } from '../services/apiClient';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';

export default function ReviewTicketsPage() {
  const { user } = useAuth();
  const { pushToast } = useToast();
  const [rows, setRows] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({ evaluation_id: '', reason: '' });
  const [evaluations, setEvaluations] = useState([]);

  useEffect(() => {
    async function loadEvaluations() {
      try {
        const response = await apiClient.get('/evaluations/', { params: { skip: 0, limit: 100 } });
        setEvaluations(response.data || []);
      } catch {
        setEvaluations([]);
      }
    }
    loadEvaluations();
  }, []);

  const columns = useMemo(
    () => [
      { key: 'evaluation_id', label: 'Evaluation ID' },
      { key: 'status', label: 'Status' },
      { key: 'reason', label: 'Reason' },
      { key: 'requested_by_user_id', label: 'Requested By' },
      {
        key: 'created_at',
        label: 'Created At',
        render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-')
      }
    ],
    []
  );

  async function loadData() {
    setLoading(true);
    setError('');
    try {
      const response = await apiClient.get('/review-tickets/', {
        params: { status: statusFilter || undefined, skip, limit }
      });
      setRows(response.data);
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to load review tickets';
      setError(String(detail));
      pushToast({ title: 'Load failed', description: String(detail), variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [skip, limit]);

  async function onCreateTicket(event) {
    event.preventDefault();
    if (user?.role !== 'teacher') {
      return;
    }
    try {
      await apiClient.post('/review-tickets/', form);
      setForm({ evaluation_id: '', reason: '' });
      pushToast({ title: 'Requested', description: 'Reopen request submitted.', variant: 'success' });
      await loadData();
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to create review ticket';
      pushToast({ title: 'Request failed', description: String(detail), variant: 'error' });
    }
  }

  async function onAdminDecision(row, action) {
    try {
      const reason = action === 'approve' ? 'Approved after verification' : 'Rejected after verification';
      await apiClient.patch(`/review-tickets/${row.id}/${action}`, { reason });
      pushToast({
        title: action === 'approve' ? 'Approved' : 'Rejected',
        description: `Review ticket ${action}d successfully.`,
        variant: 'success'
      });
      await loadData();
    } catch (err) {
      const detail = err?.response?.data?.detail || `Failed to ${action} review ticket`;
      pushToast({ title: 'Action failed', description: String(detail), variant: 'error' });
    }
  }

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-4">
        <h1 className="text-2xl font-semibold">Review Tickets</h1>
        <div className="grid gap-3 sm:grid-cols-3">
          <FormInput
            label="Status Filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            placeholder="pending / approved / rejected"
          />
          <div className="flex items-end gap-2">
            <button className="btn-secondary" onClick={() => { setSkip(0); loadData(); }}>Apply</button>
          </div>
        </div>
      </Card>

      {user?.role === 'teacher' ? (
        <Card className="space-y-3">
          <h2 className="text-lg font-semibold">Create Reopen Request</h2>
          <form onSubmit={onCreateTicket} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <FormInput as="select" label="Evaluation" required value={form.evaluation_id} onChange={(e) => setForm((p) => ({ ...p, evaluation_id: e.target.value }))}>
              <option value="">Select Evaluation</option>
              {evaluations.map((item) => (
                <option key={item.id} value={item.id}>
                  {`${item.id} | Total: ${item.grand_total ?? '-'} | ${item.grade ?? ''}`}
                </option>
              ))}
            </FormInput>
            <FormInput
              label="Reason"
              required
              value={form.reason}
              onChange={(e) => setForm((p) => ({ ...p, reason: e.target.value }))}
            />
            <div className="flex items-end">
              <button type="submit" className="btn-primary w-full">Submit Request</button>
            </div>
          </form>
        </Card>
      ) : null}

      <Card className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">Ticket List</h2>
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
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}
        <Table
          columns={columns}
          data={rows}
          rowActions={
            user?.role === 'admin'
              ? [
                  {
                    key: 'approve',
                    label: 'Approve',
                    className: 'text-emerald-600 dark:text-emerald-300',
                    onClick: (row) => onAdminDecision(row, 'approve')
                  },
                  {
                    key: 'reject',
                    label: 'Reject',
                    className: 'text-rose-600 dark:text-rose-300',
                    onClick: (row) => onAdminDecision(row, 'reject')
                  }
                ]
              : []
          }
        />
      </Card>
    </div>
  );
}
