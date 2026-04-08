import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import Card from '../components/ui/Card';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';

export default function ClubEventsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [clubs, setClubs] = useState([]);
  const requestedClubId = searchParams.get('club_id') || '';

  useEffect(() => {
    async function loadClubs() {
      try {
        const response = await apiClient.get('/clubs/', { params: { skip: 0, limit: 100 } });
        setClubs(response.data || []);
      } catch {
        setClubs([]);
      }
    }

    loadClubs();
  }, []);

  const selectedClub = useMemo(
    () => clubs.find((club) => club.id === requestedClubId) || null,
    [clubs, requestedClubId]
  );

  const clubOptions = useMemo(
    () => clubs.map((club) => ({ value: club.id, label: club.name })),
    [clubs]
  );

  const clubNameById = useMemo(
    () => Object.fromEntries(clubOptions.map((item) => [item.value, item.label])),
    [clubOptions]
  );

  const filters = useMemo(
    () => [
      { name: 'club_id', label: 'Club', type: 'select', options: clubOptions, placeholder: 'All Clubs', defaultValue: requestedClubId },
      { name: 'status', label: 'Status', placeholder: 'open / closed / archived' }
    ],
    [clubOptions, requestedClubId]
  );

  const columns = useMemo(() => {
    return [
      { key: 'club_id', label: 'Club', render: (row) => clubNameById[row.club_id] || row.club_id },
      { key: 'title', label: 'Title' },
      { key: 'status', label: 'Status' },
      { key: 'event_type', label: 'Type', render: (row) => row.event_type || '-' },
      {
        key: 'registration_enabled',
        label: 'Registration',
        render: (row) => (row.registration_enabled ? 'Enabled' : 'Disabled')
      },
      {
        key: 'visibility',
        label: 'Visibility',
        render: (row) => (row.visibility === 'members_only' ? 'Members Only' : 'Public')
      },
      { key: 'capacity', label: 'Capacity' },
      { key: 'event_date', label: 'Event Date', render: (row) => (row.event_date ? new Date(row.event_date).toLocaleString() : '-') }
    ];
  }, [clubNameById]);

  const rowActions = useMemo(
    () => [
      {
        key: 'open-club-workspace',
        label: 'Open In Clubs Hub',
        onClick: (row) => navigate(`/clubs?tab=events&club_id=${row.club_id}`)
      },
      {
        key: 'open-records',
        label: 'Open Records',
        onClick: (row) => navigate(`/event-registrations?event_id=${row.id}`)
      }
    ],
    [navigate]
  );

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <h1 className="text-2xl font-semibold">Club Event Inventory</h1>
            <p className="max-w-3xl text-sm text-slate-500">
              This page is now the staff-only cross-club inventory and handoff surface. Browse events across clubs here,
              then move into the selected-club Event Center inside Clubs Hub for creation, lifecycle changes, enrollments,
              attendance, and certificates.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link className="btn-primary" to={selectedClub ? `/clubs?tab=events&club_id=${selectedClub.id}` : '/clubs?tab=events'}>
              {selectedClub ? 'Open Selected Club In Clubs Hub' : 'Open Clubs Hub Event Center'}
            </Link>
            <Link className="btn-secondary" to="/event-registrations">
              Open Registration Records
            </Link>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/60">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Primary workflow</p>
            <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-slate-100">Clubs Hub Event Center</p>
            <p className="mt-1 text-sm text-slate-500">Selected-club context for creation, lifecycle actions, enrollments, attendance, and certificates.</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/60">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">This page</p>
            <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-slate-100">Inventory and handoff</p>
            <p className="mt-1 text-sm text-slate-500">Browse events across clubs, then jump into the right club workspace or registration records.</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/60">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Filtered club</p>
            <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-slate-100">{selectedClub?.name || 'All clubs'}</p>
            <p className="mt-1 text-sm text-slate-500">
              {selectedClub ? `Use this inventory to inspect ${selectedClub.name}, then continue operations in Clubs Hub.` : 'Choose a club filter to narrow the inventory and handoff into its workspace.'}
            </p>
          </div>
        </div>
      </Card>

      <EntityManager
        title="Club Event Inventory"
        endpoint="/club-events/"
        filters={filters}
        columns={columns}
        hideCreate
        enableDelete={false}
        rowActions={rowActions}
      />
    </div>
  );
}
