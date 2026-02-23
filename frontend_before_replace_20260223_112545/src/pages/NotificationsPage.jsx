import { useMemo } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';
import { useAuth } from '../hooks/useAuth';

const filters = [
  { name: 'is_read', label: 'Read', type: 'switch' },
  { name: 'scope', label: 'Scope' }
];

const createFields = [
  { name: 'title', label: 'Title', required: true },
  { name: 'message', label: 'Message', required: true },
  { name: 'priority', label: 'Priority', defaultValue: 'normal', required: true },
  { name: 'scope', label: 'Scope', defaultValue: 'global', required: true },
  { name: 'target_user_id', label: 'Target User ID', nullable: true }
];

export default function NotificationsPage() {
  const { user } = useAuth();

  const columns = useMemo(
    () => [
      { key: 'title', label: 'Title' },
      { key: 'priority', label: 'Priority' },
      { key: 'scope', label: 'Scope' },
      { key: 'message', label: 'Message' },
      { key: 'is_read', label: 'Read', render: (row) => (row.is_read ? 'Yes' : 'No') },
      { key: 'created_at', label: 'Created At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
    ],
    []
  );

  const rowActions = useMemo(
    () => [
      {
        key: 'mark-read',
        label: 'Mark Read',
        onClick: async (row, { reload, pushToast }) => {
          if (row.is_read) {
            pushToast({ title: 'Already read', description: 'Notification is already marked as read.', variant: 'info' });
            return;
          }
          await apiClient.patch(`/notifications/${row.id}/read`);
          pushToast({ title: 'Updated', description: 'Notification marked as read.', variant: 'success' });
          await reload();
        }
      }
    ],
    []
  );

  return (
    <EntityManager
      title="Notifications"
      endpoint="/notifications/"
      filters={filters}
      createFields={createFields}
      columns={columns}
      rowActions={rowActions}
      hideCreate={user?.role === 'student'}
      createTransform={(payload) => ({
        ...payload,
        target_user_id: payload.target_user_id || null
      })}
    />
  );
}
