import { useEffect, useMemo, useRef, useState } from 'react';
import { apiClient, getRecentApiTraceEntries } from '../../services/apiClient';
import { formatApiError } from '../../utils/apiError';
import { ALL_CLUBS_VALUE } from './constants';
import { submitEventRegistration } from './eventRegistration';

function currentTimeMs() {
  if (typeof globalThis.performance?.now === 'function') {
    return globalThis.performance.now();
  }
  return Date.now();
}

function toRoundedDuration(value) {
  return Math.max(0, Math.round(value));
}

function snapshotClubApiTraces() {
  return getRecentApiTraceEntries()
    .filter((entry) => {
      const url = String(entry?.url || '');
      return (
        url.includes('/clubs') ||
        url.includes('/club-events') ||
        url.includes('/event-registrations')
      );
    })
    .slice(0, 16);
}

export function useClubDirectory({ user, pushToast }) {
  const isAdmin = user?.role === 'admin';
  const isTeacher = user?.role === 'teacher';
  const isStudent = user?.role === 'student';

  const [clubs, setClubs] = useState([]);
  const [selectedClubId, setSelectedClubId] = useState('');
  const [loadingClubs, setLoadingClubs] = useState(false);
  const [teachers, setTeachers] = useState([]);
  const [students, setStudents] = useState([]);
  const [members, setMembers] = useState([]);
  const [applications, setApplications] = useState([]);
  const [events, setEvents] = useState([]);
  const [eventRegistrations, setEventRegistrations] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [clubsLoadError, setClubsLoadError] = useState('');
  const [clubDataLoadError, setClubDataLoadError] = useState('');
  const [workspacePerformance, setWorkspacePerformance] = useState({
    traces: [],
    updatedAt: null,
    directory: null,
    selectedClub: null
  });
  const loadErrorRef = useRef('');

  const selectedClub = useMemo(
    () => (selectedClubId === ALL_CLUBS_VALUE ? null : clubs.find((club) => club.id === selectedClubId) || null),
    [clubs, selectedClubId]
  );

  function canManageClub(club) {
    if (!club || !user) return false;
    if (isAdmin) return true;
    if (isTeacher) {
      return club.coordinator_user_id === user.id;
    }
    return false;
  }

  function isClubPresident(club) {
    if (!club || !user) return false;
    return club.president_user_id === user.id;
  }

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

  async function fetchClubs(nextSelectedClubId = selectedClubId) {
    const startedAt = currentTimeMs();
    const response = await apiClient.get('/clubs/', { params: { skip: 0, limit: 100 } });
    const items = response.data || [];
    setClubs(items);
    loadErrorRef.current = '';

    if (!nextSelectedClubId && items.length > 0) {
      setSelectedClubId(items[0].id);
    } else if (nextSelectedClubId && !items.some((club) => club.id === nextSelectedClubId)) {
      setSelectedClubId(items[0]?.id || '');
    }

    setWorkspacePerformance((prev) => ({
      ...prev,
      updatedAt: new Date().toISOString(),
      traces: snapshotClubApiTraces(),
      directory: {
        status: 'healthy',
        durationMs: toRoundedDuration(currentTimeMs() - startedAt),
        loadedAt: new Date().toISOString(),
        clubsCount: items.length,
        errorMessage: ''
      }
    }));

    return items;
  }

  async function loadSelectedClubData(clubId = selectedClubId, studentMode = isStudent) {
    if (!clubId) {
      setMembers([]);
      setApplications([]);
      setEvents([]);
      setEventRegistrations([]);
      setAnalytics(null);
      setWorkspacePerformance((prev) => ({
        ...prev,
        updatedAt: new Date().toISOString(),
        selectedClub: null
      }));
      return;
    }

    setClubDataLoadError('');
    const startedAt = currentTimeMs();
    let eventsDurationMs = null;
    let memberDataDurationMs = null;
    let registrationDurationMs = null;
    let analyticsDurationMs = null;
    let eventItems = [];
    let memberItems = [];
    let applicationItems = [];
    let registrationItems = [];
    let analyticsPayload = null;
    let loadStatus = 'healthy';
    let loadErrorMessage = '';
    const analyticsStartedAt = currentTimeMs();
    const analyticsPromise = apiClient
      .get(`/clubs/${clubId}/analytics`)
      .then((response) => {
        analyticsDurationMs = toRoundedDuration(currentTimeMs() - analyticsStartedAt);
        analyticsPayload = response.data || null;
        return analyticsPayload;
      });

    try {
      const eventsParams =
        clubId === ALL_CLUBS_VALUE
          ? { skip: 0, limit: 100 }
          : { club_id: clubId, skip: 0, limit: 100 };

      const eventsStartedAt = currentTimeMs();
      const eventsPromise = apiClient.get('/club-events/', { params: eventsParams }).then((response) => {
        eventsDurationMs = toRoundedDuration(currentTimeMs() - eventsStartedAt);
        return response.data || [];
      });

      const memberDataPromise =
        clubId === ALL_CLUBS_VALUE
          ? Promise.resolve({ members: [], applications: [] })
          : (async () => {
              const memberDataStartedAt = currentTimeMs();
              const [membersRes, applicationsRes] = await Promise.all([
                apiClient.get(`/clubs/${clubId}/members`),
                apiClient.get(`/clubs/${clubId}/applications`)
              ]);
              memberDataDurationMs = toRoundedDuration(currentTimeMs() - memberDataStartedAt);
              return {
                members: membersRes.data || [],
                applications: applicationsRes.data || []
              };
            })();

      const registrationsPromise = studentMode
        ? (async () => {
            const registrationsStartedAt = currentTimeMs();
            const regsRes = await apiClient.get('/event-registrations/', { params: { skip: 0, limit: 100 } });
            registrationDurationMs = toRoundedDuration(currentTimeMs() - registrationsStartedAt);
            return regsRes.data || [];
          })()
        : Promise.resolve([]);

      const [loadedEvents, memberData, loadedRegistrations] = await Promise.all([
        eventsPromise,
        memberDataPromise,
        registrationsPromise
      ]);

      eventItems = loadedEvents;
      memberItems = memberData.members;
      applicationItems = memberData.applications;
      registrationItems = loadedRegistrations;

      setMembers(memberItems);
      setApplications(applicationItems);
      setEvents(eventItems);
      setEventRegistrations(studentMode ? registrationItems : []);
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
      loadStatus = 'error';
      loadErrorMessage = message;
    }

    try {
      const loadedAnalytics = await analyticsPromise;
      setAnalytics(loadedAnalytics);
    } catch (err) {
      setAnalytics(null);
      if (loadStatus !== 'error') {
        loadStatus = 'partial';
        loadErrorMessage = formatApiError(err, 'Analytics unavailable for selected club');
      }
    }

    setWorkspacePerformance((prev) => ({
      ...prev,
      updatedAt: new Date().toISOString(),
      traces: snapshotClubApiTraces(),
      selectedClub: {
        clubId,
        status: loadStatus,
        durationMs: toRoundedDuration(currentTimeMs() - startedAt),
        loadedAt: new Date().toISOString(),
        eventsDurationMs,
        memberDataDurationMs,
        registrationDurationMs,
        analyticsDurationMs,
        counts: {
          members: memberItems.length,
          applications: applicationItems.length,
          events: eventItems.length,
          registrations: registrationItems.length
        },
        analyticsAvailable: Boolean(analyticsPayload),
        errorMessage: loadErrorMessage
      }
    }));
  }

  useEffect(() => {
    async function loadClubs() {
      setLoadingClubs(true);
      setClubsLoadError('');
      try {
        await fetchClubs('');
      } catch (err) {
        const message = formatApiError(err, 'Could not load clubs');
        setClubsLoadError(message);
        setWorkspacePerformance((prev) => ({
          ...prev,
          updatedAt: new Date().toISOString(),
          traces: snapshotClubApiTraces(),
          directory: {
            status: 'error',
            durationMs: null,
            loadedAt: new Date().toISOString(),
            clubsCount: 0,
            errorMessage: message
          }
        }));
        notifyLoadErrorOnce(message);
      } finally {
        setLoadingClubs(false);
      }
    }

    loadClubs();
  }, []);

  useEffect(() => {
    async function loadUsers() {
      if (!isAdmin) {
        setTeachers([]);
        setStudents([]);
        return;
      }

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
    loadSelectedClubData();
  }, [selectedClubId, isStudent]);

  async function refreshClubs() {
    try {
      setClubsLoadError('');
      await fetchClubs(selectedClubId);
    } catch (err) {
      const message = formatApiError(err, 'Could not refresh clubs');
      setClubsLoadError(message);
      setWorkspacePerformance((prev) => ({
        ...prev,
        updatedAt: new Date().toISOString(),
        traces: snapshotClubApiTraces(),
        directory: {
          status: 'error',
          durationMs: prev.directory?.durationMs ?? null,
          loadedAt: new Date().toISOString(),
          clubsCount: clubs.length,
          errorMessage: message
        }
      }));
      pushToast({ title: 'Refresh failed', description: message, variant: 'error' });
    }
  }

  async function reloadSelectedClubData() {
    if (!selectedClubId) return;
    setClubDataLoadError('');
    await loadSelectedClubData(selectedClubId, isStudent);
  }

  async function createClub(payload) {
    await apiClient.post('/clubs/', payload);
    await refreshClubs();
  }

  async function joinClub(clubId) {
    try {
      const response = await apiClient.post(`/clubs/${clubId}/join`);
      const clubJoinStatus = response.data?.status;
      pushToast({
        title:
          clubJoinStatus === 'approved'
            ? 'Joined club'
            : clubJoinStatus === 'waitlisted'
              ? 'Added to membership waitlist'
              : 'Application submitted',
        description: response.data?.message || 'Request processed',
        variant: 'success'
      });
      await Promise.all([loadSelectedClubData(clubId, isStudent), refreshClubs()]);
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

  async function updateClubSettings(clubId, payload, successDescription = 'Club settings updated.') {
    if (!clubId) return null;
    try {
      const response = await apiClient.patch(`/clubs/${clubId}`, payload);
      pushToast({ title: 'Club updated', description: successDescription, variant: 'success' });
      await refreshClubs();
      return response.data || null;
    } catch (err) {
      pushToast({ title: 'Update failed', description: formatApiError(err, 'Failed to update club settings'), variant: 'error' });
      throw err;
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

  async function reviewApplication(applicationId, update) {
    if (!selectedClubId) return;
    try {
      const payload = typeof update === 'string' ? { status: update } : { ...(update || {}) };
      if (!Object.keys(payload).length) return;
      await apiClient.patch(`/clubs/${selectedClubId}/applications/${applicationId}`, payload);
      const description = payload.status
        ? `Application ${payload.status}.`
        : 'Application owner and note saved.';
      pushToast({ title: 'Application updated', description, variant: 'success' });
      await Promise.all([loadSelectedClubData(selectedClubId, isStudent), refreshClubs()]);
    } catch (err) {
      pushToast({ title: 'Review failed', description: formatApiError(err, 'Could not review application'), variant: 'error' });
      throw err;
    }
  }

  async function bulkReviewApplications(applicationIds, status) {
    if (!selectedClubId || !applicationIds?.length) return;
    try {
      const response = await apiClient.post(`/clubs/${selectedClubId}/applications/bulk-review`, {
        application_ids: applicationIds,
        status
      });
      const updatedCount = response.data?.updated_count ?? applicationIds.length;
      pushToast({
        title: 'Queue updated',
        description: `${updatedCount} membership application${updatedCount === 1 ? '' : 's'} moved to ${status}.`,
        variant: 'success'
      });
      await Promise.all([loadSelectedClubData(selectedClubId, isStudent), refreshClubs()]);
    } catch (err) {
      pushToast({ title: 'Bulk review failed', description: formatApiError(err, 'Could not update membership queue'), variant: 'error' });
      throw err;
    }
  }

  async function remindApplications({ applicationIds = [], statusFilter = null, message = '' } = {}) {
    if (!selectedClubId) return;
    try {
      const response = await apiClient.post(`/clubs/${selectedClubId}/applications/remind`, {
        application_ids: applicationIds,
        status_filter: statusFilter,
        message: message || null
      });
      const remindedCount = response.data?.reminded_count ?? 0;
      pushToast({
        title: 'Reminder sent',
        description: `${remindedCount} membership reminder${remindedCount === 1 ? '' : 's'} delivered.`,
        variant: 'success'
      });
    } catch (err) {
      pushToast({ title: 'Reminder failed', description: formatApiError(err, 'Could not remind the membership queue'), variant: 'error' });
      throw err;
    }
  }

  async function updateMember(memberId, payload) {
    if (!selectedClubId) return;
    await apiClient.patch(`/clubs/${selectedClubId}/members/${memberId}`, payload);
    const nextRole = payload.role ? `Role updated to ${payload.role}.` : null;
    const nextStatus = payload.status ? `Status updated to ${payload.status}.` : null;
    pushToast({
      title: 'Member updated',
      description: [nextRole, nextStatus].filter(Boolean).join(' ') || 'Member updated successfully.',
      variant: 'success'
    });
    await Promise.all([loadSelectedClubData(selectedClubId, isStudent), refreshClubs()]);
  }

  async function createEvent(payload) {
    await apiClient.post('/club-events/', payload);
    pushToast({ title: 'Event created', description: 'Club event created successfully.', variant: 'success' });
    await loadSelectedClubData(selectedClubId, isStudent);
  }

  async function bulkUpdateEventRegistrations(registrationIds, payload) {
    if (!registrationIds?.length) return;
    try {
      const response = await apiClient.post('/event-registrations/bulk-update', {
        registration_ids: registrationIds,
        ...payload
      });
      const updatedCount = response.data?.updated_count ?? registrationIds.length;
      const nextStatus = payload.status ? ` moved to ${payload.status}` : '';
      pushToast({
        title: 'Registrations updated',
        description: `${updatedCount} event registration${updatedCount === 1 ? '' : 's'}${nextStatus}.`,
        variant: 'success'
      });
      if (selectedClubId) {
        await loadSelectedClubData(selectedClubId, isStudent);
      }
      return response.data;
    } catch (err) {
      pushToast({ title: 'Bulk update failed', description: formatApiError(err, 'Could not update registrations'), variant: 'error' });
      throw err;
    }
  }

  async function remindEventRegistrations({ eventId, registrationIds = [], statusFilter = null, message = '' } = {}) {
    if (!eventId) return;
    try {
      const response = await apiClient.post('/event-registrations/remind', {
        event_id: eventId,
        registration_ids: registrationIds,
        status_filter: statusFilter,
        message: message || null
      });
      const remindedCount = response.data?.reminded_count ?? 0;
      pushToast({
        title: 'Reminder sent',
        description: `${remindedCount} event reminder${remindedCount === 1 ? '' : 's'} delivered.`,
        variant: 'success'
      });
      return response.data;
    } catch (err) {
      pushToast({ title: 'Reminder failed', description: formatApiError(err, 'Could not remind the event queue'), variant: 'error' });
      throw err;
    }
  }

  async function registerForEvent({ registrationEvent, registrationForm, paymentReceiptFile }) {
    const created = await submitEventRegistration({ registrationEvent, registrationForm, paymentReceiptFile });
    const isWaitlisted = created?.status === 'waitlisted';
    pushToast({
      title: isWaitlisted ? 'Added to waitlist' : 'Registered',
      description: isWaitlisted
        ? 'This event is full right now, so your registration has been placed in the waitlist.'
        : 'Event registration submitted.',
      variant: 'success'
    });
    await loadSelectedClubData(selectedClubId, true);
    return created;
  }

  async function downloadClubAnalyticsReport(report = 'event_performance') {
    if (!selectedClubId || selectedClubId === ALL_CLUBS_VALUE) return;
    try {
      const response = await apiClient.get(`/clubs/${selectedClubId}/analytics/export`, {
        params: { report },
        responseType: 'blob'
      });
      const disposition = response.headers?.['content-disposition'] || '';
      const filenameMatch = disposition.match(/filename="?([^"]+)"?/i);
      const filename = filenameMatch?.[1] || `club-${selectedClubId}-${report}.csv`;
      const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      window.URL.revokeObjectURL(url);
      pushToast({
        title: 'Report exported',
        description:
          report === 'attendance_certificate'
            ? 'Attendance and certificate report downloaded.'
            : 'Event performance report downloaded.',
        variant: 'success'
      });
    } catch (err) {
      pushToast({
        title: 'Export failed',
        description: formatApiError(err, 'Could not export club analytics report'),
        variant: 'error'
      });
      throw err;
    }
  }

  return {
    analytics,
    applications,
    bulkReviewApplications,
    bulkUpdateEventRegistrations,
    canManageClub,
    clubDataLoadError,
    clubs,
    clubsLoadError,
    createClub,
    createEvent,
    downloadClubAnalyticsReport,
    eventRegistrations,
    events,
    isAdmin,
    isClubPresident,
    isStudent,
    joinClub,
    loadingClubs,
    members,
    remindApplications,
    remindEventRegistrations,
    reloadSelectedClubData,
    refreshClubs,
    registerForEvent,
    reviewApplication,
    selectedClub,
    selectedClubId,
    setSelectedClubId,
    students,
    teachers,
    updateMember,
    updateClubSettings,
    updateClubStatus,
    workspacePerformance,
    toggleRegistration
  };
}
