import { useMemo } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { useAuth } from '../hooks/useAuth';

const filters = [
  { name: 'scope', label: 'Scope', placeholder: 'college / year / class / subject' },
  { name: 'priority', label: 'Priority', placeholder: 'normal / urgent' },
  { name: 'include_expired', label: 'Include Expired', type: 'switch' }
];

const createFields = [
  { name: 'title', label: 'Title', required: true },
  { name: 'message', label: 'Message', required: true },
  { name: 'priority', label: 'Priority', defaultValue: 'normal', required: true },
  { name: 'scope', label: 'Scope', defaultValue: 'subject', required: true },
  { name: 'scope_ref_id', label: 'Scope Ref ID', nullable: true },
  { name: 'expires_at', label: 'Expires At', type: 'datetime', nullable: true }
];

export default function NoticesPage() {
  const { user } = useAuth();

  const columns = useMemo(
    () => [
      { key: 'title', label: 'Title' },
      { key: 'priority', label: 'Priority' },
      { key: 'scope', label: 'Scope' },
      { key: 'message', label: 'Message' },
      { key: 'expires_at', label: 'Expires At', render: (row) => (row.expires_at ? new Date(row.expires_at).toLocaleString() : '-') },
      { key: 'created_at', label: 'Created At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
    ],
    []
  );

  return (
    <EntityManager
      title="Notices"
      endpoint="/notices/"
      filters={filters}
      createFields={createFields}
      columns={columns}
      hideCreate={user?.role === 'student'}
      createTransform={(payload) => ({
        ...payload,
        scope_ref_id: payload.scope_ref_id || null,
        expires_at: payload.expires_at || null
      })}
    />
  );
}
