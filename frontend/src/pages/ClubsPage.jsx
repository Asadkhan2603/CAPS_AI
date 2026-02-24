import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import Card from '../components/ui/Card';
import FormInput from '../components/ui/FormInput';
import Modal from '../components/ui/Modal';
import Table from '../components/ui/Table';
import { apiClient } from '../services/apiClient';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { formatApiError } from '../utils/apiError';

const tabs = [
  { key: 'overview', label: 'Overview' },
  { key: 'members', label: 'Members' },
  { key: 'events', label: 'Events' },
  { key: 'announcements', label: 'Announcements' },
  { key: 'analytics', label: 'Analytics' }
];
const ALL_CLUBS_VALUE = '__all__';

const clubStatusOptions = ['draft', 'pending_activation', 'active', 'registration_closed', 'closed', 'suspended', 'archived', 'dormant'];
const activeClubStatuses = new Set(['active', 'registration_closed']);

const initialCreateForm = {
  name: '',
  description: '',
  category: '',
  academic_year: '',
  membership_type: 'approval_required',
  max_members: '',
  coordinator_user_id: '',
  status: 'draft'
};

const initialEventForm = {
  title: '',
  description: '',
  event_type: 'workshop',
  visibility: 'public',
  registration_start: '',
  registration_end: '',
  event_date: '',
  capacity: 100,
  registration_enabled: true,
  payment_required: false,
  payment_qr_image_url: '',
  payment_amount: ''
};

function createInitialRegistrationForm(user = null) {
  return {
    enrollment_number: '',
    full_name: user?.full_name || '',
    email: user?.email || '',
    year: '',
    course_branch: '',
    class_name: '',
    phone_number: '',
    whatsapp_number: '',
    payment_qr_code: ''
  };
}

export default function ClubsPage() {
  const { user } = useAuth();
  const { pushToast } = useToast();

  const isAdmin = user?.role === 'admin';
  const isTeacher = user?.role === 'teacher';
  const isStudent = user?.role === 'student';
  const teacherExtensions = user?.extended_roles || [];

  const [activeTab, setActiveTab] = useState('overview');
  const [clubs, setClubs] = useState([]);
  const [selectedClubId, setSelectedClubId] = useState('');
  const [statusFilter, setStatusFilter] = useState('active');
  const [search, setSearch] = useState('');
  const [loadingClubs, setLoadingClubs] = useState(false);

  const [teachers, setTeachers] = useState([]);
  const [students, setStudents] = useState([]);

  const [members, setMembers] = useState([]);
  const [applications, setApplications] = useState([]);
  const [events, setEvents] = useState([]);
  const [eventRegistrations, setEventRegistrations] = useState([]);
  const [analytics, setAnalytics] = useState(null);

  const [createForm, setCreateForm] = useState(initialCreateForm);
  const [createLoading, setCreateLoading] = useState(false);

  const [eventForm, setEventForm] = useState(initialEventForm);
  const [eventLoading, setEventLoading] = useState(false);
  const [registrationModalOpen, setRegistrationModalOpen] = useState(false);
  const [registrationEvent, setRegistrationEvent] = useState(null);
  const [registrationForm, setRegistrationForm] = useState(createInitialRegistrationForm(user));
  const [paymentReceiptFile, setPaymentReceiptFile] = useState(null);
  const [registrationSubmitting, setRegistrationSubmitting] = useState(false);
  const [expandedDescriptions, setExpandedDescriptions] = useState({});
  const [clubsLoadError, setClubsLoadError] = useState('');
  const [clubDataLoadError, setClubDataLoadError] = useState('');
  const loadErrorRef = useRef('');

  const selectedClub = useMemo(
    () => (selectedClubId === ALL_CLUBS_VALUE ? null : clubs.find((club) => club.id === selectedClubId) || null),
    [clubs, selectedClubId]
  );

  function canManageClub(club) {
    if (!club || !user) return false;
    if (isAdmin) return true;
    if (isTeacher) {
      return club.coordinator_user_id === user.id || teacherExtensions.includes('club_coordinator');
    }
    return false;
  }

  function isClubPresident(club) {
    if (!club || !user) return false;
    return club.president_user_id === user.id;
  }

  const filteredClubs = useMemo(() => {
    const text = search.trim().toLowerCase();
    return clubs.filter((club) => {
      const statusPass = statusFilter ? club.status === statusFilter : true;
      const textPass = text
        ? [club.name, club.category, club.description]
            .filter(Boolean)
            .some((value) => String(value).toLowerCase().includes(text))
        : true;
      return statusPass && textPass;
    });
  }, [clubs, search, statusFilter]);

  function notifyLoadErrorOnce(message) {
    if (!message) return;
    if (loadErrorRef.current === message) return;
    loadErrorRef.current = message;
    pushToast({
      title: 'Failed to load clubs',
      description: message,
      variant: 'error'
    });
  }

  useEffect(() => {
    async function loadClubs() {
      setLoadingClubs(true);
      setClubsLoadError('');
      try {
        const response = await apiClient.get('/clubs/', { params: { skip: 0, limit: 100 } });
        const items = response.data || [];
        setClubs(items);
        loadErrorRef.current = '';
        if (!selectedClubId && items.length > 0) {
          setSelectedClubId(items[0].id);
        }
      } catch (err) {
        const message = formatApiError(err, 'Could not load clubs');
        setClubsLoadError(message);
        notifyLoadErrorOnce(message);
      } finally {
        setLoadingClubs(false);
      }
    }

    loadClubs();
  }, []);

  useEffect(() => {
    async function loadUsers() {
      if (!isAdmin) return;
      try {
        const response = await apiClient.get('/users/', { params: { skip: 0, limit: 500 } });
        const all = response.data || [];
        setTeachers(all.filter((item) => item.role === 'teacher'));
        setStudents(all.filter((item) => item.role === 'student'));
      } catch {
        setTeachers([]);
        setStudents([]);
      }
    }

    loadUsers();
  }, [isAdmin]);

  useEffect(() => {
    setRegistrationForm((prev) => ({
      ...prev,
      full_name: prev.full_name || user?.full_name || '',
      email: prev.email || user?.email || ''
    }));
  }, [user]);

  useEffect(() => {
    async function loadSelectedClubData() {
      if (!selectedClubId) {
        setMembers([]);
        setApplications([]);
        setEvents([]);
        setEventRegistrations([]);
        setAnalytics(null);
        return;
      }

      setClubDataLoadError('');
      try {
        const eventsParams = selectedClubId === ALL_CLUBS_VALUE
          ? { skip: 0, limit: 100 }
          : { club_id: selectedClubId, skip: 0, limit: 100 };
        const eventsRes = await apiClient.get('/club-events/', { params: eventsParams });
        const eventItems = eventsRes.data || [];

        if (selectedClubId === ALL_CLUBS_VALUE) {
          setMembers([]);
          setApplications([]);
        } else {
          const [membersRes, applicationsRes] = await Promise.all([
            apiClient.get(`/clubs/${selectedClubId}/members`),
            apiClient.get(`/clubs/${selectedClubId}/applications`)
          ]);
          setMembers(membersRes.data || []);
          setApplications(applicationsRes.data || []);
        }

        setEvents(eventItems);
        if (isStudent) {
          const regsRes = await apiClient.get('/event-registrations/', { params: { skip: 0, limit: 100 } });
          setEventRegistrations(regsRes.data || []);
        } else {
          setEventRegistrations([]);
        }
      } catch (err) {
        setMembers([]);
        setApplications([]);
        setEvents([]);
        setEventRegistrations([]);
        const status = err?.response?.status;
        const message =
          status === 404
            ? 'Advanced club endpoints are unavailable on backend. Restart backend to load members/applications/events.'
            : formatApiError(err, 'Failed to load selected club data');
        setClubDataLoadError(message);
      }

      try {
        const analyticsRes = await apiClient.get(`/clubs/${selectedClubId}/analytics`);
        setAnalytics(analyticsRes.data || null);
      } catch {
        setAnalytics(null);
      }
    }

    loadSelectedClubData();
  }, [selectedClubId, isStudent]);

  async function refreshClubs() {
    try {
      setClubsLoadError('');
      const response = await apiClient.get('/clubs/', { params: { skip: 0, limit: 100 } });
      const items = response.data || [];
      setClubs(items);
      loadErrorRef.current = '';
      if (selectedClubId && !items.some((club) => club.id === selectedClubId)) {
        setSelectedClubId(items[0]?.id || '');
      }
    } catch (err) {
      const message = formatApiError(err, 'Could not refresh clubs');
      setClubsLoadError(message);
      pushToast({ title: 'Refresh failed', description: message, variant: 'error' });
    }
  }

  async function submitCreateClub(event) {
    event.preventDefault();
    setCreateLoading(true);
    try {
      const payload = {
        ...createForm,
        max_members: createForm.max_members ? Number(createForm.max_members) : null,
        coordinator_user_id: createForm.coordinator_user_id || null
      };
      await apiClient.post('/clubs/', payload);
      setCreateForm(initialCreateForm);
      pushToast({ title: 'Club created', description: 'New club created successfully.', variant: 'success' });
      await refreshClubs();
    } catch (err) {
      pushToast({ title: 'Create failed', description: formatApiError(err, 'Failed to create club'), variant: 'error' });
    } finally {
      setCreateLoading(false);
    }
  }

  async function joinClub(clubId) {
    try {
      const response = await apiClient.post(`/clubs/${clubId}/join`);
      pushToast({
        title: response.data?.status === 'approved' ? 'Joined club' : 'Application submitted',
        description: response.data?.message || 'Request processed',
        variant: 'success'
      });
      const [membersRes, applicationsRes] = await Promise.all([
        apiClient.get(`/clubs/${clubId}/members`),
        apiClient.get(`/clubs/${clubId}/applications`)
      ]);
      setMembers(membersRes.data || []);
      setApplications(applicationsRes.data || []);
      await refreshClubs();
    } catch (err) {
      pushToast({ title: 'Join failed', description: formatApiError(err, 'Could not process club join'), variant: 'error' });
    }
  }

  async function updateClubStatus(club, nextStatus) {
    try {
      await apiClient.patch(`/clubs/${club.id}`, { status: nextStatus });
      pushToast({ title: 'Club updated', description: `Status changed to ${nextStatus}.`, variant: 'success' });
      await refreshClubs();
    } catch (err) {
      pushToast({ title: 'Update failed', description: formatApiError(err, 'Failed to update status'), variant: 'error' });
    }
  }

  async function toggleRegistration(club) {
    try {
      await apiClient.patch(`/clubs/${club.id}`, { registration_open: !club.registration_open });
      pushToast({
        title: club.registration_open ? 'Registration closed' : 'Registration opened',
        description: `Club registration is now ${club.registration_open ? 'closed' : 'open'}.`,
        variant: 'success'
      });
      await refreshClubs();
    } catch (err) {
      pushToast({ title: 'Update failed', description: formatApiError(err, 'Failed to toggle registration'), variant: 'error' });
    }
  }

  async function reviewApplication(applicationId, status) {
    if (!selectedClubId) return;
    try {
      await apiClient.patch(`/clubs/${selectedClubId}/applications/${applicationId}`, { status });
      pushToast({ title: 'Application updated', description: `Application ${status}.`, variant: 'success' });
      const [membersRes, applicationsRes, clubsRes] = await Promise.all([
        apiClient.get(`/clubs/${selectedClubId}/members`),
        apiClient.get(`/clubs/${selectedClubId}/applications`),
        apiClient.get('/clubs/', { params: { skip: 0, limit: 100 } })
      ]);
      setMembers(membersRes.data || []);
      setApplications(applicationsRes.data || []);
      setClubs(clubsRes.data || []);
    } catch (err) {
      pushToast({ title: 'Review failed', description: formatApiError(err, 'Could not review application'), variant: 'error' });
    }
  }

  async function submitCreateEvent(event) {
    event.preventDefault();
    if (!selectedClubId || selectedClubId === ALL_CLUBS_VALUE) {
      pushToast({ title: 'Select a club', description: 'Choose a specific club to create event.', variant: 'error' });
      return;
    }
    setEventLoading(true);
    try {
      await apiClient.post('/club-events/', {
        club_id: selectedClubId,
        title: eventForm.title,
        description: eventForm.description || null,
        event_type: eventForm.event_type,
        visibility: eventForm.visibility,
        registration_start: eventForm.registration_start || null,
        registration_end: eventForm.registration_end || null,
        event_date: eventForm.event_date || null,
        capacity: Number(eventForm.capacity) || 100,
        registration_enabled: Boolean(eventForm.registration_enabled),
        payment_required: Boolean(eventForm.registration_enabled && eventForm.payment_required),
        payment_qr_image_url:
          eventForm.registration_enabled && eventForm.payment_required
            ? (eventForm.payment_qr_image_url || null)
            : null,
        payment_amount:
          eventForm.registration_enabled && eventForm.payment_required && eventForm.payment_amount !== ''
            ? Number(eventForm.payment_amount)
            : null
      });
      setEventForm(initialEventForm);
      pushToast({ title: 'Event created', description: 'Club event created successfully.', variant: 'success' });
      const response = await apiClient.get('/club-events/', { params: { club_id: selectedClubId, skip: 0, limit: 100 } });
      setEvents(response.data || []);
    } catch (err) {
      pushToast({ title: 'Create failed', description: formatApiError(err, 'Failed to create event'), variant: 'error' });
    } finally {
      setEventLoading(false);
    }
  }

  function openRegistrationModal(eventRow) {
    setRegistrationEvent(eventRow);
    setRegistrationForm(createInitialRegistrationForm(user));
    setPaymentReceiptFile(null);
    setRegistrationModalOpen(true);
  }

  async function submitEventRegistrationForm(event) {
    event.preventDefault();
    if (!registrationEvent) return;

    if (registrationEvent.payment_required && !registrationForm.payment_qr_code) {
      pushToast({ title: 'Payment required', description: 'Enter transaction reference.', variant: 'error' });
      return;
    }
    if (registrationEvent.payment_required && !paymentReceiptFile) {
      pushToast({ title: 'Payment screenshot required', description: 'Upload payment screenshot.', variant: 'error' });
      return;
    }

    setRegistrationSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('event_id', registrationEvent.id);
      formData.append('enrollment_number', registrationForm.enrollment_number);
      formData.append('full_name', registrationForm.full_name);
      formData.append('email', registrationForm.email);
      formData.append('year', registrationForm.year);
      formData.append('course_branch', registrationForm.course_branch);
      formData.append('class_name', registrationForm.class_name);
      formData.append('phone_number', registrationForm.phone_number);
      formData.append('whatsapp_number', registrationForm.whatsapp_number);
      formData.append('payment_qr_code', registrationForm.payment_qr_code || '');
      if (paymentReceiptFile) {
        formData.append('payment_receipt', paymentReceiptFile);
      }

      await apiClient.post('/event-registrations/submit', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      pushToast({ title: 'Registered', description: 'Event registration submitted.', variant: 'success' });
      const [eventsRes, regsRes] = await Promise.all([
        apiClient.get('/club-events/', {
          params: selectedClubId === ALL_CLUBS_VALUE
            ? { skip: 0, limit: 100 }
            : { club_id: selectedClubId, skip: 0, limit: 100 }
        }),
        apiClient.get('/event-registrations/', { params: { skip: 0, limit: 100 } })
      ]);
      setEvents(eventsRes.data || []);
      setEventRegistrations(regsRes.data || []);
      setRegistrationModalOpen(false);
      setRegistrationEvent(null);
      setPaymentReceiptFile(null);
      setRegistrationForm(createInitialRegistrationForm(user));
    } catch (err) {
      pushToast({ title: 'Registration failed', description: formatApiError(err, 'Could not register for event'), variant: 'error' });
    } finally {
      setRegistrationSubmitting(false);
    }
  }

  const eventRegistrationByEventId = useMemo(() => {
    const map = new Map();
    for (const reg of eventRegistrations) {
      map.set(reg.event_id, reg);
    }
    return map;
  }, [eventRegistrations]);

  function toggleDescription(clubId) {
    setExpandedDescriptions((prev) => ({
      ...prev,
      [clubId]: !prev[clubId]
    }));
  }

  function openClub(clubId) {
    setSelectedClubId(clubId);
    setActiveTab('members');
  }

  const memberColumns = [
    { key: 'student_name', label: 'Student', render: (row) => row.student_name || row.student_email || row.student_user_id },
    { key: 'role', label: 'Role' },
    { key: 'status', label: 'Status' },
    { key: 'joined_at', label: 'Joined', render: (row) => (row.joined_at ? new Date(row.joined_at).toLocaleString() : '-') }
  ];

  const applicationColumns = [
    { key: 'student_name', label: 'Student', render: (row) => row.student_name || row.student_email || row.student_user_id },
    { key: 'status', label: 'Status' },
    { key: 'applied_at', label: 'Applied', render: (row) => (row.applied_at ? new Date(row.applied_at).toLocaleString() : '-') }
  ];

  const eventColumns = [
    { key: 'title', label: 'Title' },
    { key: 'event_type', label: 'Type' },
    { key: 'status', label: 'Status' },
    {
      key: 'registration_enabled',
      label: 'Registration',
      render: (row) => (row.registration_enabled ? 'Enabled' : 'Disabled')
    },
    {
      key: 'payment',
      label: 'Payment',
      render: (row) => (
        row.payment_required ? (
          <div className="space-y-1">
            <div>{`Paid${row.payment_amount ? ` (INR ${row.payment_amount})` : ''}`}</div>
            {row.payment_qr_image_url ? (
              <a
                className="text-xs text-brand-600 underline hover:text-brand-700"
                href={row.payment_qr_image_url}
                target="_blank"
                rel="noreferrer"
              >
                View QR
              </a>
            ) : null}
          </div>
        ) : 'Free'
      )
    },
    {
      key: 'registration_start',
      label: 'Registration Start',
      render: (row) => (row.registration_start ? new Date(row.registration_start).toLocaleString() : '-')
    },
    {
      key: 'registration_end',
      label: 'Registration End',
      render: (row) => (row.registration_end ? new Date(row.registration_end).toLocaleString() : '-')
    },
    { key: 'capacity', label: 'Capacity' },
    { key: 'event_date', label: 'Date', render: (row) => (row.event_date ? new Date(row.event_date).toLocaleString() : '-') },
    ...(isStudent
      ? [{
          key: 'action',
          label: 'Action',
          render: (row) => {
            const registration = eventRegistrationByEventId.get(row.id);
            if (registration) {
              return <span className="text-xs font-medium text-emerald-600">{registration.status}</span>;
            }
            const now = Date.now();
            const isOpenStatus = row.status === 'open';
            const startsAt = row.registration_start ? new Date(row.registration_start).getTime() : null;
            const endsAt = row.registration_end ? new Date(row.registration_end).getTime() : null;
            const notStarted = startsAt && now < startsAt;
            const expired = endsAt && now > endsAt;
            const disabled = !isOpenStatus || !row.registration_enabled || notStarted || expired;
            const label = !isOpenStatus
              ? (row.status === 'draft' ? 'Not Open' : 'Closed')
              : (notStarted ? 'Not Started' : expired ? 'Closed' : 'Register');
            const title = !isOpenStatus
              ? `Event status is ${row.status}`
              : notStarted
              ? `Registration opens at ${new Date(row.registration_start).toLocaleString()}`
              : expired
                ? 'Registration deadline passed'
                : '';
            return (
              <button
                className="btn-primary !px-3 !py-1 text-xs"
                type="button"
                disabled={disabled}
                title={title}
                onClick={() => openRegistrationModal(row)}
              >
                {label}
              </button>
            );
          }
        }]
      : [])
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-4 page-fade">
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold">Clubs Hub</h1>
            <p className="text-sm text-slate-500">Governance, members, events, announcements and analytics.</p>
          </div>
          <button className="btn-secondary" onClick={refreshClubs}>Refresh</button>
        </div>

        <div className="flex flex-wrap gap-2 rounded-2xl border border-slate-200 p-2 dark:border-slate-700">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              className={`rounded-xl px-4 py-2 text-sm font-medium ${activeTab === tab.key ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </Card>

      <Card className="space-y-3">
        <div className="grid gap-3 md:grid-cols-3">
          <FormInput as="select" label="Status" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All</option>
            {clubStatusOptions.map((status) => (
              <option key={status} value={status}>{status}</option>
            ))}
          </FormInput>
          <FormInput label="Search clubs" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Name, category, description" />
          <FormInput as="select" label="Selected Club" value={selectedClubId} onChange={(e) => setSelectedClubId(e.target.value)}>
            <option value="">Select club</option>
            <option value={ALL_CLUBS_VALUE}>All Clubs</option>
            {filteredClubs.map((club) => (
              <option key={club.id} value={club.id}>{club.name}</option>
            ))}
          </FormInput>
        </div>

        {loadingClubs ? <p className="text-sm text-slate-500">Loading clubs...</p> : null}
        {clubsLoadError ? (
          <div className="rounded-xl border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-200">
            {clubsLoadError}
          </div>
        ) : null}
        {clubDataLoadError ? (
          <div className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-700 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
            {clubDataLoadError}
          </div>
        ) : null}
      </Card>

      {activeTab === 'overview' ? (
        <div className="space-y-4">
          <Card className="space-y-3">
            <h2 className="text-lg font-semibold">Club Directory</h2>
            <div className="grid gap-3 md:grid-cols-2">
              {filteredClubs.map((club) => (
                <article
                  key={club.id}
                  className={`cursor-pointer rounded-2xl border p-4 transition ${selectedClubId === club.id ? 'border-brand-400 ring-1 ring-brand-300 dark:border-brand-500 dark:ring-brand-700' : 'border-slate-200 hover:border-slate-300 dark:border-slate-700 dark:hover:border-slate-500'}`}
                  onClick={() => openClub(club.id)}
                >
                  <div className="mb-2 flex items-start justify-between gap-2">
                    <div>
                      <h3 className="text-lg font-semibold">{club.name}</h3>
                      <p className="text-sm text-slate-500">{club.category || 'General'}</p>
                    </div>
                    <span className="rounded-full border border-slate-300 px-2 py-0.5 text-xs uppercase">{club.status}</span>
                  </div>
                  <p className="mb-1 text-sm text-slate-600 dark:text-slate-300">
                    {club.description
                      ? (expandedDescriptions[club.id] || club.description.length <= 180
                        ? club.description
                        : `${club.description.slice(0, 180)}...`)
                      : 'No description'}
                  </p>
                  {club.description && club.description.length > 180 ? (
                    <button
                      className="mb-3 text-xs font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300"
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        toggleDescription(club.id);
                      }}
                    >
                      {expandedDescriptions[club.id] ? 'Show less' : 'Read more'}
                    </button>
                  ) : (
                    <div className="mb-3" />
                  )}
                  <div className="mb-3 grid grid-cols-2 gap-2 text-xs text-slate-500">
                    <span>Coordinator: {club.coordinator_name || '-'}</span>
                    <span>President: {club.president_name || '-'}</span>
                    <span>Members: {club.member_count ?? 0}</span>
                    <span>Registration: {club.registration_open ? 'Open' : 'Closed'}</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {isStudent ? (
                      <button
                        className="btn-primary !px-3 !py-1.5 text-xs"
                        onClick={(event) => {
                          event.stopPropagation();
                          joinClub(club.id);
                        }}
                        disabled={!activeClubStatuses.has(club.status) || !club.registration_open}
                      >
                        Join Club
                      </button>
                    ) : null}

                    {canManageClub(club) ? (
                      <>
                        {activeClubStatuses.has(club.status) ? (
                          <button className="btn-secondary !px-3 !py-1.5 text-xs" onClick={(event) => { event.stopPropagation(); toggleRegistration(club); }}>
                            {club.registration_open ? 'Close Registration' : 'Open Registration'}
                          </button>
                        ) : null}
                        {club.status !== 'active' ? (
                          <button className="btn-secondary !px-3 !py-1.5 text-xs" onClick={(event) => { event.stopPropagation(); updateClubStatus(club, 'active'); }}>
                            Activate
                          </button>
                        ) : null}
                        {club.status === 'active' ? (
                          <button className="btn-secondary !px-3 !py-1.5 text-xs" onClick={(event) => { event.stopPropagation(); updateClubStatus(club, 'registration_closed'); }}>
                            Registration Closed
                          </button>
                        ) : null}
                        {club.status === 'registration_closed' ? (
                          <button className="btn-secondary !px-3 !py-1.5 text-xs" onClick={(event) => { event.stopPropagation(); updateClubStatus(club, 'active'); }}>
                            Reopen
                          </button>
                        ) : null}
                        {(club.status === 'active' || club.status === 'registration_closed') ? (
                          <button className="btn-secondary !px-3 !py-1.5 text-xs" onClick={(event) => { event.stopPropagation(); updateClubStatus(club, 'closed'); }}>
                            Close
                          </button>
                        ) : null}
                        {(club.status === 'active' || club.status === 'registration_closed' || club.status === 'closed') ? (
                          <button className="btn-secondary !px-3 !py-1.5 text-xs" onClick={(event) => { event.stopPropagation(); updateClubStatus(club, 'dormant'); }}>
                            Mark Dormant
                          </button>
                        ) : null}
                        {isAdmin ? (
                          <>
                            {club.status !== 'suspended' ? (
                              <button className="btn-secondary !px-3 !py-1.5 text-xs" onClick={(event) => { event.stopPropagation(); updateClubStatus(club, 'suspended'); }}>
                                Suspend
                              </button>
                            ) : null}
                            {club.status !== 'archived' ? (
                              <button className="btn-secondary !px-3 !py-1.5 text-xs" onClick={(event) => { event.stopPropagation(); updateClubStatus(club, 'archived'); }}>
                                Archive
                              </button>
                            ) : null}
                          </>
                        ) : null}
                      </>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          </Card>

          {isAdmin ? (
            <Card className="space-y-3">
              <h2 className="text-lg font-semibold">Create Club</h2>
              <form className="grid gap-3 md:grid-cols-2" onSubmit={submitCreateClub}>
                <FormInput label="Name" required value={createForm.name} onChange={(e) => setCreateForm((prev) => ({ ...prev, name: e.target.value }))} />
                <FormInput label="Category" value={createForm.category} onChange={(e) => setCreateForm((prev) => ({ ...prev, category: e.target.value }))} />
                <FormInput label="Academic Year" value={createForm.academic_year} onChange={(e) => setCreateForm((prev) => ({ ...prev, academic_year: e.target.value }))} />
                <FormInput as="select" label="Membership Type" value={createForm.membership_type} onChange={(e) => setCreateForm((prev) => ({ ...prev, membership_type: e.target.value }))}>
                  <option value="approval_required">Approval Required</option>
                  <option value="open">Open</option>
                </FormInput>
                <FormInput label="Max Members" type="number" min={1} value={createForm.max_members} onChange={(e) => setCreateForm((prev) => ({ ...prev, max_members: e.target.value }))} />
                <FormInput as="select" label="Coordinator" value={createForm.coordinator_user_id} onChange={(e) => setCreateForm((prev) => ({ ...prev, coordinator_user_id: e.target.value }))}>
                  <option value="">Select coordinator</option>
                  {teachers.map((teacher) => (
                    <option key={teacher.id} value={teacher.id}>{teacher.full_name} ({teacher.email})</option>
                  ))}
                </FormInput>
                <FormInput as="select" label="President (Optional)" value={createForm.president_user_id || ''} onChange={(e) => setCreateForm((prev) => ({ ...prev, president_user_id: e.target.value }))}>
                  <option value="">Select president</option>
                  {students.map((student) => (
                    <option key={student.id} value={student.id}>{student.full_name} ({student.email})</option>
                  ))}
                </FormInput>
                <FormInput as="select" label="Status" value={createForm.status} onChange={(e) => setCreateForm((prev) => ({ ...prev, status: e.target.value }))}>
                  {clubStatusOptions.map((status) => (
                    <option key={status} value={status}>{status}</option>
                  ))}
                </FormInput>
                <div className="md:col-span-2">
                  <FormInput label="Description" value={createForm.description} onChange={(e) => setCreateForm((prev) => ({ ...prev, description: e.target.value }))} />
                </div>
                <button className="btn-primary md:col-span-2" type="submit" disabled={createLoading}>{createLoading ? 'Creating...' : 'Create Club'}</button>
              </form>
            </Card>
          ) : null}
        </div>
      ) : null}

      {activeTab === 'members' ? (
        <div className="space-y-4">
          <Card className="space-y-3">
            <h2 className="text-lg font-semibold">Members</h2>
            <Table columns={memberColumns} data={members} />
          </Card>

          {selectedClub && canManageClub(selectedClub) ? (
            <Card className="space-y-3">
              <h2 className="text-lg font-semibold">Membership Applications</h2>
              <Table
                columns={applicationColumns}
                data={applications}
                rowActions={[
                  { key: 'approve', label: 'Approve', onClick: (row) => reviewApplication(row.id, 'approved') },
                  { key: 'reject', label: 'Reject', onClick: (row) => reviewApplication(row.id, 'rejected') }
                ]}
              />
            </Card>
          ) : null}
        </div>
      ) : null}

      {activeTab === 'events' ? (
        <div className="space-y-4">
          {(selectedClub && (canManageClub(selectedClub) || isClubPresident(selectedClub))) ? (
            <Card className="space-y-3">
              <h2 className="text-lg font-semibold">Create Event</h2>
              <form className="grid gap-3 md:grid-cols-2" onSubmit={submitCreateEvent}>
                <FormInput label="Title" required value={eventForm.title} onChange={(e) => setEventForm((prev) => ({ ...prev, title: e.target.value }))} />
                <FormInput as="select" label="Type" value={eventForm.event_type} onChange={(e) => setEventForm((prev) => ({ ...prev, event_type: e.target.value }))}>
                  <option value="workshop">Workshop</option>
                  <option value="competition">Competition</option>
                  <option value="seminar">Seminar</option>
                  <option value="cultural">Cultural</option>
                  <option value="internal">Internal</option>
                </FormInput>
                <FormInput as="select" label="Visibility" value={eventForm.visibility} onChange={(e) => setEventForm((prev) => ({ ...prev, visibility: e.target.value }))}>
                  <option value="public">Public</option>
                  <option value="members_only">Members Only</option>
                </FormInput>
                <FormInput as="select" label="Registration Enabled" value={eventForm.registration_enabled ? 'yes' : 'no'} onChange={(e) => {
                  const enabled = e.target.value === 'yes';
                  setEventForm((prev) => ({
                    ...prev,
                    registration_enabled: enabled,
                    registration_start: enabled ? prev.registration_start : '',
                    registration_end: enabled ? prev.registration_end : '',
                    payment_required: enabled ? prev.payment_required : false,
                    payment_qr_image_url: enabled ? prev.payment_qr_image_url : '',
                    payment_amount: enabled ? prev.payment_amount : ''
                  }));
                }}>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </FormInput>
                {eventForm.registration_enabled ? (
                  <>
                    <FormInput
                      type="datetime-local"
                      label="Registration Start"
                      value={eventForm.registration_start}
                      onChange={(e) => setEventForm((prev) => ({ ...prev, registration_start: e.target.value }))}
                    />
                    <FormInput
                      type="datetime-local"
                      label="Registration End"
                      value={eventForm.registration_end}
                      onChange={(e) => setEventForm((prev) => ({ ...prev, registration_end: e.target.value }))}
                    />
                  </>
                ) : null}
                {eventForm.registration_enabled ? (
                  <FormInput as="select" label="Payment Required" value={eventForm.payment_required ? 'yes' : 'no'} onChange={(e) => {
                    const required = e.target.value === 'yes';
                    setEventForm((prev) => ({
                      ...prev,
                      payment_required: required,
                      payment_qr_image_url: required ? prev.payment_qr_image_url : '',
                      payment_amount: required ? prev.payment_amount : ''
                    }));
                  }}>
                    <option value="no">No</option>
                    <option value="yes">Yes</option>
                  </FormInput>
                ) : null}
                <FormInput type="datetime-local" label="Event Date" value={eventForm.event_date} onChange={(e) => setEventForm((prev) => ({ ...prev, event_date: e.target.value }))} />
                <FormInput type="number" min={1} max={5000} label="Capacity" value={eventForm.capacity} onChange={(e) => setEventForm((prev) => ({ ...prev, capacity: e.target.value }))} />
                {eventForm.registration_enabled && eventForm.payment_required ? (
                  <>
                    <FormInput
                      label="Payment QR Image URL"
                      placeholder="https://..."
                      value={eventForm.payment_qr_image_url}
                      onChange={(e) => setEventForm((prev) => ({ ...prev, payment_qr_image_url: e.target.value }))}
                    />
                    <FormInput
                      type="number"
                      min={0}
                      step="0.01"
                      label="Amount (INR)"
                      value={eventForm.payment_amount}
                      onChange={(e) => setEventForm((prev) => ({ ...prev, payment_amount: e.target.value }))}
                    />
                  </>
                ) : null}
                <div className="md:col-span-2">
                  <FormInput label="Description" value={eventForm.description} onChange={(e) => setEventForm((prev) => ({ ...prev, description: e.target.value }))} />
                </div>
                <button className="btn-primary md:col-span-2" type="submit" disabled={eventLoading}>{eventLoading ? 'Creating...' : 'Create Event'}</button>
              </form>
            </Card>
          ) : null}

          <Card className="space-y-3">
            <h2 className="text-lg font-semibold">Events</h2>
            <Table columns={eventColumns} data={events} />
          </Card>
        </div>
      ) : null}

      {activeTab === 'announcements' ? (
        <Card className="space-y-3">
          <h2 className="text-lg font-semibold">Club Announcements</h2>
          <p className="text-sm text-slate-500">
            Announcements are managed in Communication Hub. Use the audience selector to publish club-scoped updates.
          </p>
          <div className="flex flex-wrap gap-2">
            <Link className="btn-primary" to="/communication/announcements">Open Announcements</Link>
            <Link className="btn-secondary" to="/communication/feed">Open Feed</Link>
          </div>
        </Card>
      ) : null}

      {activeTab === 'analytics' ? (
        <Card className="space-y-3">
          <h2 className="text-lg font-semibold">Club Analytics</h2>
          {!analytics ? (
            <p className="text-sm text-slate-500">Analytics not available for this role or club.</p>
          ) : (
            <div className="grid gap-3 md:grid-cols-3">
              <Stat label="Total Members" value={analytics.total_members} />
              <Stat label="Active Members" value={analytics.active_members} />
              <Stat label="Inactive Members" value={analytics.inactive_members} />
              <Stat label="Membership Growth (30d)" value={analytics.membership_growth_30d} />
              <Stat label="Total Events" value={analytics.total_events} />
              <Stat label="Upcoming Events" value={analytics.upcoming_events} />
              <Stat label="Completed Events" value={analytics.completed_events} />
              <Stat label="Avg Attendance %" value={analytics.average_attendance_pct} />
              <Stat label="Pending Applications" value={analytics.pending_applications} />
            </div>
          )}
        </Card>
      ) : null}

      <Modal
        open={registrationModalOpen}
        title={registrationEvent ? `Register: ${registrationEvent.title}` : 'Event Registration'}
        onClose={() => {
          setRegistrationModalOpen(false);
          setRegistrationEvent(null);
          setPaymentReceiptFile(null);
        }}
      >
        <form className="grid gap-3 md:grid-cols-2" onSubmit={submitEventRegistrationForm}>
          <FormInput required label="Enrollment Number" value={registrationForm.enrollment_number} onChange={(e) => setRegistrationForm((prev) => ({ ...prev, enrollment_number: e.target.value }))} />
          <FormInput required label="Full Name" value={registrationForm.full_name} onChange={(e) => setRegistrationForm((prev) => ({ ...prev, full_name: e.target.value }))} />
          <FormInput required label="Email" type="email" value={registrationForm.email} onChange={(e) => setRegistrationForm((prev) => ({ ...prev, email: e.target.value }))} />
          <FormInput required label="Year" value={registrationForm.year} onChange={(e) => setRegistrationForm((prev) => ({ ...prev, year: e.target.value }))} />
          <FormInput required label="Course / Branch" value={registrationForm.course_branch} onChange={(e) => setRegistrationForm((prev) => ({ ...prev, course_branch: e.target.value }))} />
          <FormInput required label="Class" value={registrationForm.class_name} onChange={(e) => setRegistrationForm((prev) => ({ ...prev, class_name: e.target.value }))} />
          <FormInput required label="Phone Number" value={registrationForm.phone_number} onChange={(e) => setRegistrationForm((prev) => ({ ...prev, phone_number: e.target.value }))} />
          <FormInput required label="WhatsApp Number" value={registrationForm.whatsapp_number} onChange={(e) => setRegistrationForm((prev) => ({ ...prev, whatsapp_number: e.target.value }))} />

          {registrationEvent?.payment_required ? (
            <>
              <div className="md:col-span-2 rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                Payment required
                {registrationEvent.payment_amount ? `: INR ${registrationEvent.payment_amount}` : ''}.
                {registrationEvent.payment_qr_image_url ? (
                  <> <a className="underline" href={registrationEvent.payment_qr_image_url} target="_blank" rel="noreferrer">View QR</a></>
                ) : null}
              </div>
              <FormInput required label="Transaction Reference" value={registrationForm.payment_qr_code} onChange={(e) => setRegistrationForm((prev) => ({ ...prev, payment_qr_code: e.target.value }))} />
              <label className="block space-y-1">
                <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Payment Screenshot</span>
                <input
                  className="input"
                  type="file"
                  accept=".png,.jpg,.jpeg,.pdf"
                  required
                  onChange={(e) => setPaymentReceiptFile(e.target.files?.[0] || null)}
                />
              </label>
            </>
          ) : null}

          <div className="md:col-span-2 flex justify-end gap-2 pt-2">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setRegistrationModalOpen(false);
                setRegistrationEvent(null);
                setPaymentReceiptFile(null);
              }}
            >
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={registrationSubmitting}>
              {registrationSubmitting ? 'Submitting...' : 'Submit Registration'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold">{value ?? 0}</p>
    </div>
  );
}
