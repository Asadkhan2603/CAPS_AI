import { useMemo } from 'react';
import EntityManager from '../components/ui/EntityManager';

const filters = [
  { name: 'actor_user_id', label: 'Actor User ID' },
  { name: 'entity_type', label: 'Entity Type' },
  { name: 'action', label: 'Action' }
];

export default function AuditLogsPage() {
  const columns = useMemo(
    () => [
      { key: 'actor_user_id', label: 'Actor' },
      { key: 'action', label: 'Action' },
      { key: 'entity_type', label: 'Entity' },
      { key: 'entity_id', label: 'Entity ID' },
      { key: 'detail', label: 'Detail' },
      { key: 'created_at', label: 'Created At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
    ],
    []
  );

  return (
    <EntityManager
      title="Audit Logs"
      endpoint="/audit-logs/"
      filters={filters}
      columns={columns}
      hideCreate
      pageSizeOptions={[10, 25, 50, 100]}
    />
  );
}

