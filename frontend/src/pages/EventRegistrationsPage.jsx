import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import Card from '../components/ui/Card';
import FormInput from '../components/ui/FormInput';
import FileUpload from '../components/ui/FileUpload';
import Table from '../components/ui/Table';
import { apiClient } from '../services/apiClient';
import { useToast } from '../hooks/useToast';
import { useAuth } from '../hooks/useAuth';
import { formatApiError } from '../utils/apiError';

const initialForm = {
  event_id: '',
  enrollment_number: '',
  full_name: '',
  email: '',
  year: '',
  course_branch: '',
  section: '',
  phone_number: '',
  whatsapp_number: '',
  payment_qr_code: '',
  payment_receipt: null
};

export default function EventRegistrationsPage() {
  const { user } = useAuth();
  const { pushToast } = useToast();
  const [searchParams] = useSearchParams();
  const eventIdFromQuery = searchParams.get('event_id') || '';
  const isStudent = user?.role === 'student';

  const [rows, setRows] = useState([]);
  const [events, setEvents] = useState([]);
  const [eventFilter, setEventFilter] = useState('');
  const [form, setForm] = useState(initialForm);
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [submitStatus, setSubmitStatus] = useState('idle');
  const [submitProgress, setSubmitProgress] = useState(0);

  const eventLabelById = useMemo(
    () => Object.fromEntries(events.map((item) => [item.id, item.title ? `${item.title} (${item.id})` : item.id])),
    [events]
  );

  const columns = useMemo(
    () => [
      { key: 'event_id', label: 'Event', render: (row) => eventLabelById[row.event_id] || row.event_id },
      { key: 'enrollment_number', label: 'Enrollment No.' },
      { key: 'full_name', label: 'Full Name', render: (row) => row.full_name || row.student_name || '-' },
      { key: 'email', label: 'Email', render: (row) => row.email || row.student_email || '-' },
      { key: 'year', label: 'Year' },
      { key: 'course_branch', label: 'Course Branch' },
      { key: 'section', label: 'Section' },
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
    setForm((prev) => ({ ...prev, event_id: eventIdFromQuery }));
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

  async function onSubmitRegistration(event) {
    event.preventDefault();
    setError('');
    setSubmitStatus('uploading');
    setSubmitProgress(15);

    try {
      const multipart = new FormData();
      multipart.append('event_id', form.event_id);
      multipart.append('enrollment_number', form.enrollment_number);
      multipart.append('full_name', form.full_name);
      multipart.append('email', form.email);
      multipart.append('year', form.year);
      multipart.append('course_branch', form.course_branch);
      multipart.append('section', form.section);
      multipart.append('phone_number', form.phone_number);
      multipart.append('whatsapp_number', form.whatsapp_number);
      if (form.payment_qr_code) {
        multipart.append('payment_qr_code', form.payment_qr_code);
      }
      if (form.payment_receipt) {
        multipart.append('payment_receipt', form.payment_receipt);
      }

      setSubmitProgress(65);
      await apiClient.post('/event-registrations/submit', multipart, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setSubmitProgress(100);
      setSubmitStatus('success');
      setForm(initialForm);
      pushToast({ title: 'Registered', description: 'Event registration submitted successfully.', variant: 'success' });
      await loadData();
    } catch (err) {
      const detail = formatApiError(err, 'Failed to submit event registration');
      setError(detail);
      setSubmitStatus('error');
      pushToast({ title: 'Registration failed', description: detail, variant: 'error' });
    }
  }

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-4">
        <h1 className="text-2xl font-semibold">Event Registrations</h1>
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
          <h2 className="text-lg font-semibold">Register For Event</h2>
          <form onSubmit={onSubmitRegistration} className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-3">
              <FormInput
                as="select"
                label="Event"
                required
                value={form.event_id}
                onChange={(e) => setForm((p) => ({ ...p, event_id: e.target.value }))}
              >
                <option value="">Select Event</option>
                {events.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.title || item.id}
                  </option>
                ))}
              </FormInput>
              <FormInput label="Enrollment Number" required value={form.enrollment_number} onChange={(e) => setForm((p) => ({ ...p, enrollment_number: e.target.value }))} />
              <FormInput label="Full Name" required value={form.full_name} onChange={(e) => setForm((p) => ({ ...p, full_name: e.target.value }))} />
              <FormInput label="Email" required type="email" value={form.email} onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))} />
              <FormInput label="Year" required value={form.year} onChange={(e) => setForm((p) => ({ ...p, year: e.target.value }))} />
              <FormInput label="Course Branch" required value={form.course_branch} onChange={(e) => setForm((p) => ({ ...p, course_branch: e.target.value }))} />
              <FormInput label="Section" required value={form.section} onChange={(e) => setForm((p) => ({ ...p, section: e.target.value }))} />
              <FormInput label="Phone Number" required value={form.phone_number} onChange={(e) => setForm((p) => ({ ...p, phone_number: e.target.value }))} />
              <FormInput label="WhatsApp Number" required value={form.whatsapp_number} onChange={(e) => setForm((p) => ({ ...p, whatsapp_number: e.target.value }))} />
              <FormInput label="Payment QR Code (Optional)" value={form.payment_qr_code} onChange={(e) => setForm((p) => ({ ...p, payment_qr_code: e.target.value }))} />
              <button className="btn-primary" type="submit">Submit Registration</button>
            </div>

            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Payment Receipt (Optional)</p>
              <FileUpload
                accept=".png,.jpg,.jpeg,.pdf"
                onFileSelect={(file) => setForm((prev) => ({ ...prev, payment_receipt: file }))}
                progress={submitProgress}
                status={submitStatus}
              />
            </div>
          </form>
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
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
