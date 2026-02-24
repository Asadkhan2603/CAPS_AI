import { useMemo } from 'react';
import EntityManager from '../components/ui/EntityManager';

const filters = [
  { name: 'actor_user_id', label: 'Actor User ID' },
  { name: 'entity_type', label: 'Entity Type' },
  { name: 'resource_type', label: 'Resource Type' },
  { name: 'action', label: 'Action' },
  { name: 'severity', label: 'Severity', placeholder: 'low / medium / high' },
  { name: 'created_from', label: 'Created From', type: 'datetime' },
  { name: 'created_to', label: 'Created To', type: 'datetime' }
];

export default function AuditLogsPage() {
  const columns = useMemo(
    () => [
      { key: 'actor_user_id', label: 'Actor' },
      { key: 'action', label: 'Action' },
      { key: 'severity', label: 'Severity' },
      { key: 'entity_type', label: 'Entity' },
      { key: 'resource_type', label: 'Resource' },
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
