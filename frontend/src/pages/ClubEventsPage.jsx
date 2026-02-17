import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { useNavigate } from 'react-router-dom';
import Modal from '../components/ui/Modal';
import Table from '../components/ui/Table';
import { formatApiError } from '../utils/apiError';

const filters = [
  { name: 'club_id', label: 'Club ID' },
  { name: 'status', label: 'Status', placeholder: 'open / closed / archived' }
];

const createFields = [
  { name: 'club_id', label: 'Club ID', required: true },
  { name: 'title', label: 'Title', required: true },
  { name: 'description', label: 'Description', nullable: true },
  { name: 'event_date', label: 'Event Date & Time', type: 'datetime', nullable: true },
  { name: 'capacity', label: 'Capacity', type: 'number', min: 1, max: 5000, defaultValue: 100, required: true }
];

export default function ClubEventsPage() {
  const { user } = useAuth();
  const { pushToast } = useToast();
  const navigate = useNavigate();
  const [managedClubIds, setManagedClubIds] = useState([]);
  const [clubs, setClubs] = useState([]);
  const [enrollmentModalEvent, setEnrollmentModalEvent] = useState(null);
  const [enrollments, setEnrollments] = useState([]);
  const [loadingEnrollments, setLoadingEnrollments] = useState(false);
  const canRegister = user?.role === 'student';
  const isTeacher = user?.role === 'teacher';

  useEffect(() => {
    async function loadClubs() {
      try {
        const response = await apiClient.get('/clubs/', { params: { skip: 0, limit: 100 } });
        setClubs(response.data || []);
      } catch {
        setClubs([]);
      }
    }

    async function loadManagedClubs() {
      if (!isTeacher || !user?.id) {
        setManagedClubIds([]);
        return;
      }
      try {
        const response = await apiClient.get('/clubs/', { params: { skip: 0, limit: 100 } });
        const items = response.data || [];
        const mine = items
          .filter((club) => club.coordinator_user_id === user.id)
          .map((club) => club.id);
        setManagedClubIds(mine);
      } catch {
        setManagedClubIds([]);
      }
    }
    loadClubs();
    loadManagedClubs();
  }, [isTeacher, user?.id]);

  const clubOptions = useMemo(
    () => clubs.map((club) => ({ value: club.id, label: club.name })),
    [clubs]
  );
  const clubNameById = useMemo(
    () => Object.fromEntries(clubOptions.map((item) => [item.value, item.label])),
    [clubOptions]
  );

  const columns = useMemo(
    () => {
      const baseColumns = [
        { key: 'club_id', label: 'Club', render: (row) => clubNameById[row.club_id] || row.club_id },
        { key: 'title', label: 'Title' },
        { key: 'status', label: 'Status' },
        { key: 'capacity', label: 'Capacity' },
        { key: 'event_date', label: 'Event Date', render: (row) => (row.event_date ? new Date(row.event_date).toLocaleString() : '-') }
      ];

      const registerColumn = canRegister
        ? [
            {
              key: 'register',
              label: 'Register',
              render: (row) => (
                <button
                  className="btn-secondary !px-2 !py-1 text-xs"
                  disabled={row.status !== 'open'}
                  onClick={() => navigate(`/event-registrations?event_id=${row.id}`)}
                >
                  Register Now
                </button>
              )
            }
          ]
        : [];

      return [
        ...baseColumns,
        ...registerColumn,
        { key: 'result_summary', label: 'Result', render: (row) => row.result_summary || '-' }
      ];
    },
    [canRegister, clubNameById]
  );

  const rowActions = useMemo(() => {
    if (!['admin', 'teacher'].includes(user?.role || '')) {
      return [];
    }
    return [
      {
        key: 'toggle-status',
        label: 'Open/Close',
        onClick: async (row, { reload, pushToast }) => {
          if (isTeacher && !managedClubIds.includes(row.club_id)) {
            pushToast({
              title: 'Not allowed',
              description: 'You can manage events only for clubs assigned to you.',
              variant: 'error'
            });
            return;
          }
          const nextStatus = row.status === 'open' ? 'closed' : 'open';
          if (row.status === 'archived') {
            pushToast({
              title: 'Archived event',
              description: 'Unarchive the event before changing open/closed status.',
              variant: 'error'
            });
            return;
          }
          await apiClient.put(`/club-events/${row.id}`, { status: nextStatus });
          pushToast({
            title: 'Event updated',
            description: `Event status changed to ${nextStatus}.`,
            variant: 'success'
          });
          await reload();
        }
      },
      {
        key: 'archive-toggle',
        label: 'Archive/Restore',
        onClick: async (row, { reload, pushToast }) => {
          if (isTeacher && !managedClubIds.includes(row.club_id)) {
            pushToast({
              title: 'Not allowed',
              description: 'You can manage events only for clubs assigned to you.',
              variant: 'error'
            });
            return;
          }
          const nextStatus = row.status === 'archived' ? 'open' : 'archived';
          await apiClient.put(`/club-events/${row.id}`, { status: nextStatus });
          pushToast({
            title: 'Event updated',
            description: nextStatus === 'archived' ? 'Event archived successfully.' : 'Event restored to open status.',
            variant: 'success'
          });
          await reload();
        }
      },
      {
        key: 'view-enrollments',
        label: 'View Enrollments',
        onClick: async (row, { pushToast }) => {
          if (isTeacher && !managedClubIds.includes(row.club_id)) {
            pushToast({
              title: 'Not allowed',
              description: 'You can view enrollments only for clubs assigned to you.',
              variant: 'error'
            });
            return;
          }
          setEnrollmentModalEvent(row);
          setLoadingEnrollments(true);
          try {
            const response = await apiClient.get('/event-registrations/', {
              params: { event_id: row.id, skip: 0, limit: 100 }
            });
            setEnrollments(response.data || []);
          } catch (err) {
            pushToast({
              title: 'Load failed',
              description: formatApiError(err, 'Failed to load event enrollments'),
              variant: 'error'
            });
            setEnrollments([]);
          } finally {
            setLoadingEnrollments(false);
          }
        }
      }
    ];
  }, [isTeacher, managedClubIds, user?.role]);

  const enrollmentColumns = useMemo(
    () => [
      { key: 'student_name', label: 'Student', render: (row) => row.student_name || row.student_user_id },
      { key: 'student_email', label: 'Email', render: (row) => row.student_email || '-' },
      { key: 'status', label: 'Status' },
      { key: 'created_at', label: 'Registered At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
    ],
    []
  );

  return (
    <>
      <EntityManager
        title="Club Events"
        endpoint="/club-events/"
        filters={filters.map((field) =>
          field.name === 'club_id'
            ? { ...field, label: 'Club', type: 'select', options: clubOptions, placeholder: 'All Clubs' }
            : field
        )}
        createFields={createFields.map((field) =>
          field.name === 'club_id'
            ? { ...field, label: 'Club', type: 'select', options: clubOptions }
            : field
        )}
        columns={columns}
        hideCreate={user?.role === 'student' || (isTeacher && managedClubIds.length === 0)}
        enableDelete={user?.role === 'admin'}
        rowActions={rowActions}
        createTransform={(payload) => ({
          ...payload,
          event_date: payload.event_date || null
        })}
      />

      <Modal
        open={Boolean(enrollmentModalEvent)}
        title={`Enrollments: ${enrollmentModalEvent?.title || ''}`}
        onClose={() => {
          setEnrollmentModalEvent(null);
          setEnrollments([]);
          setLoadingEnrollments(false);
        }}
      >
        <div className="space-y-3">
          {loadingEnrollments ? <p className="text-sm text-slate-500">Loading enrollments...</p> : null}
          <Table columns={enrollmentColumns} data={enrollments} />
        </div>
      </Modal>
    </>
  );
}
