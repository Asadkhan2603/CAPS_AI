import { useMemo } from 'react';
import EntityManager from '../components/ui/EntityManager';

const filters = [
  { name: 'actor_user_id', label: 'Actor' },
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
      { key: 'actor_label', label: 'Actor', render: (row) => row.actor_label || row.actor_user_id || '-' },
      { key: 'action', label: 'Action' },
      { key: 'severity', label: 'Severity' },
      { key: 'entity_label', label: 'Entity', render: (row) => row.entity_label || row.entity_type || '-' },
      { key: 'resource_type', label: 'Resource' },
      { key: 'public_id', label: 'Short ID', render: (row) => row.public_id || row.entity_id || '-' },
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
