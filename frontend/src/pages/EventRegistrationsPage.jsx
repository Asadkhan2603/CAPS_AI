import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import Card from '../components/ui/Card';
import FormInput from '../components/ui/FormInput';
import Table from '../components/ui/Table';
import { apiClient } from '../services/apiClient';
import { useToast } from '../hooks/useToast';
import { useAuth } from '../hooks/useAuth';
import { formatApiError } from '../utils/apiError';
import { getEventRegistrationAvailability } from './clubs/eventRegistration';

export default function EventRegistrationsPage() {
  const { user } = useAuth();
  const { pushToast } = useToast();
  const [searchParams] = useSearchParams();
  const eventIdFromQuery = searchParams.get('event_id') || '';
  const isStudent = user?.role === 'student';

  const [rows, setRows] = useState([]);
  const [events, setEvents] = useState([]);
  const [eventFilter, setEventFilter] = useState('');
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const eventLabelById = useMemo(
    () => Object.fromEntries(events.map((item) => [item.id, item.title ? `${item.title} (${item.id})` : item.id])),
    [events]
  );
  const selectedEvent = useMemo(
    () => events.find((item) => item.id === (eventFilter || eventIdFromQuery)) || null,
    [events, eventFilter, eventIdFromQuery]
  );
  const selectedEventAvailability = useMemo(
    () => getEventRegistrationAvailability(selectedEvent),
    [selectedEvent]
  );
  const clubsRegistrationPath = useMemo(() => {
    if (selectedEvent?.id && selectedEvent?.club_id) {
      return `/clubs?tab=events&club_id=${selectedEvent.club_id}&register_event_id=${selectedEvent.id}`;
    }
    return '/clubs?tab=events';
  }, [selectedEvent]);

  const columns = useMemo(
    () => [
      { key: 'event_id', label: 'Event', render: (row) => eventLabelById[row.event_id] || row.event_id },
      { key: 'enrollment_number', label: 'Enrollment No.' },
      { key: 'full_name', label: 'Full Name', render: (row) => row.full_name || row.student_name || '-' },
      { key: 'email', label: 'Email', render: (row) => row.email || row.student_email || '-' },
      { key: 'year', label: 'Year' },
      { key: 'course_branch', label: 'Course Branch' },
      { key: 'class_name', label: 'Section' },
      { key: 'phone_number', label: 'Phone' },
      { key: 'whatsapp_number', label: 'WhatsApp' },
      { key: 'status', label: 'Status' },
      { key: 'created_at', label: 'Created At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
    ],
    [eventLabelById]
  );

  useEffect(() => {
    async function loadEvents() {
      try {
        const response = await apiClient.get('/club-events/', { params: { skip: 0, limit: 100 } });
        setEvents(response.data || []);
      } catch {
        setEvents([]);
      }
    }
    loadEvents();
  }, []);

  useEffect(() => {
    if (!eventIdFromQuery) {
      return;
    }
    setEventFilter(eventIdFromQuery);
    setSkip(0);
  }, [eventIdFromQuery]);

  async function loadData() {
    setLoading(true);
    setError('');
    try {
      const response = await apiClient.get('/event-registrations/', {
        params: {
          event_id: eventFilter || undefined,
          skip,
          limit
        }
      });
      setRows(response.data || []);
    } catch (err) {
      const detail = formatApiError(err, 'Failed to load event registrations');
      setError(detail);
      pushToast({ title: 'Load failed', description: detail, variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [skip, limit, eventFilter]);

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-4">
        <h1 className="text-2xl font-semibold">Event Registrations</h1>
        <p className="text-sm text-slate-500">
          {isStudent
            ? 'Use Clubs Hub for new event signups. This page now focuses on registration records and status tracking.'
            : 'Review registration records and enrollment status across events.'}
        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          <FormInput
            as="select"
            label="Filter Event"
            value={eventFilter}
            onChange={(e) => setEventFilter(e.target.value)}
          >
            <option value="">All Events</option>
            {events.map((item) => (
              <option key={item.id} value={item.id}>
                {item.title || item.id}
              </option>
            ))}
          </FormInput>
          <div className="flex items-end gap-2">
            <button className="btn-secondary" onClick={() => { setSkip(0); loadData(); }}>Apply</button>
          </div>
        </div>
      </Card>

      {isStudent ? (
        <Card className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold">Register From Clubs Hub</h2>
              <p className="text-sm text-slate-500">
                The canonical registration flow lives in the clubs workspace so event context, policy messaging, and club scope stay in one place.
              </p>
            </div>
            <Link className="btn-primary" to={clubsRegistrationPath}>
              {selectedEvent ? 'Open This Event In Clubs Hub' : 'Browse Events In Clubs Hub'}
            </Link>
          </div>

          {selectedEvent ? (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-200">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-base font-semibold">{selectedEvent.title}</p>
                  <p className="mt-1 text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    {selectedEvent.event_type || 'event'} • {selectedEvent.status}
                  </p>
                </div>
                <span className={`rounded-full border px-2 py-1 text-xs font-medium ${selectedEventAvailability.canRegister ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-300' : 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-300'}`}>
                  {selectedEventAvailability.label}
                </span>
              </div>
              <p className="mt-3">
                {selectedEventAvailability.canRegister
                  ? 'Registration is available from Clubs Hub right now.'
                  : selectedEventAvailability.title || 'Registration is not available right now.'}
              </p>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                <p>{selectedEvent.approval_required ? 'Approval required after submission.' : 'Instant registration on successful submission.'}</p>
                <p>{selectedEvent.payment_required ? `Payment required: INR ${selectedEvent.payment_amount ?? 0}` : 'No payment required.'}</p>
                <p>{selectedEvent.visibility === 'members_only' ? 'Visible only to club members.' : 'Publicly visible event.'}</p>
                <p>{selectedEvent.registration_end ? `Registration closes ${new Date(selectedEvent.registration_end).toLocaleString()}.` : 'No registration deadline provided.'}</p>
                <p className="md:col-span-2">If the event fills up before your turn, the clubs workspace will place you in the waitlist automatically.</p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              Select an event in the filter above to inspect its registration status, or open Clubs Hub to browse current club events.
            </p>
          )}
        </Card>
      ) : null}

      <Card className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">Registration Records</h2>
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
        <Table columns={columns} data={rows} />
      </Card>
    </div>
  );
}
