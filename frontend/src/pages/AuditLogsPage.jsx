import React, { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import EntityManager from '../components/ui/EntityManager';

export default function AuditLogsPage() {
  const [searchParams] = useSearchParams();

  const filters = useMemo(
    () => [
      { name: 'actor_user_id', label: 'Actor', defaultValue: searchParams.get('actor_user_id') || '' },
      { name: 'entity_type', label: 'Entity Type', defaultValue: searchParams.get('entity_type') || '' },
      { name: 'resource_type', label: 'Resource Type', defaultValue: searchParams.get('resource_type') || '' },
      { name: 'action', label: 'Action', defaultValue: searchParams.get('action') || '' },
      { name: 'severity', label: 'Severity', placeholder: 'low / medium / high', defaultValue: searchParams.get('severity') || '' },
      { name: 'created_from', label: 'Created From', type: 'datetime', defaultValue: searchParams.get('created_from') || '' },
      { name: 'created_to', label: 'Created To', type: 'datetime', defaultValue: searchParams.get('created_to') || '' }
    ],
    [searchParams]
  );

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
