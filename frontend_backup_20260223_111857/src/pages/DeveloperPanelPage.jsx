import { useEffect, useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import Table from '../components/ui/Table';
import { getRecentApiTraceEntries } from '../services/apiClient';

export default function DeveloperPanelPage() {
  const [rows, setRows] = useState(() => getRecentApiTraceEntries());

  function refreshRows() {
    setRows(getRecentApiTraceEntries());
  }

  useEffect(() => {
    const timer = setInterval(() => {
      refreshRows();
    }, 1200);
    return () => clearInterval(timer);
  }, []);

  async function copy(text) {
    if (!text || !navigator?.clipboard?.writeText) {
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // no-op
    }
  }

  const columns = useMemo(
    () => [
      { key: 'at', label: 'Time', render: (row) => new Date(row.at).toLocaleString() },
      { key: 'method', label: 'Method' },
      { key: 'url', label: 'API URL' },
      { key: 'status', label: 'Status' },
      { key: 'durationMs', label: 'Duration (ms)' },
      {
        key: 'requestId',
        label: 'Request ID',
        render: (row) => (
          <button className="btn-secondary !px-2 !py-1 text-xs" onClick={() => copy(row.requestId)} title={row.requestId}>
            {row.requestId ? row.requestId.slice(0, 10) : '-'}
          </button>
        )
      },
      {
        key: 'traceId',
        label: 'Trace ID',
        render: (row) => (
          <button className="btn-secondary !px-2 !py-1 text-xs" onClick={() => copy(row.traceId)} title={row.traceId}>
            {row.traceId ? row.traceId.slice(0, 10) : '-'}
          </button>
        )
      },
      {
        key: 'errorId',
        label: 'Error ID',
        render: (row) =>
          row.errorId ? (
            <button className="btn-secondary !px-2 !py-1 text-xs" onClick={() => copy(row.errorId)} title={row.errorId}>
              {row.errorId.slice(0, 10)}
            </button>
          ) : (
            '-'
          )
      }
    ],
    []
  );

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h1 className="text-2xl font-semibold">Developer Panel</h1>
          <button className="btn-secondary" onClick={refreshRows}>Refresh</button>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          API observability stream with `request_id`, `trace_id`, status, and error IDs.
        </p>
      </Card>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Recent API Traces</h2>
        <Table columns={columns} data={rows} />
      </Card>
    </div>
  );
}
