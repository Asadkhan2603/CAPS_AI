import { useEffect, useMemo, useRef, useState } from 'react';
import { apiClient } from '../../services/apiClient';
import { formatApiError } from '../../utils/apiError';
import { ALL_CLUBS_VALUE } from './constants';

export function useClubDirectory({ user, pushToast }) {
  const isAdmin = user?.role === 'admin';
  const isTeacher = user?.role === 'teacher';
  const isStudent = user?.role === 'student';
  const teacherExtensions = user?.extended_roles || [];

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
    const response = await apiClient.get('/clubs/', { params: { skip: 0, limit: 100 } });
    const items = response.data || [];
    setClubs(items);
    loadErrorRef.current = '';

    if (!nextSelectedClubId && items.length > 0) {
      setSelectedClubId(items[0].id);
    } else if (nextSelectedClubId && !items.some((club) => club.id === nextSelectedClubId)) {
      setSelectedClubId(items[0]?.id || '');
    }

    return items;
  }

  async function loadSelectedClubData(clubId = selectedClubId, studentMode = isStudent) {
    if (!clubId) {
      setMembers([]);
      setApplications([]);
      setEvents([]);
      setEventRegistrations([]);
      setAnalytics(null);
      return;
    }

    setClubDataLoadError('');
    try {
      const eventsParams =
        clubId === ALL_CLUBS_VALUE
          ? { skip: 0, limit: 100 }
          : { club_id: clubId, skip: 0, limit: 100 };
      const eventsRes = await apiClient.get('/club-events/', { params: eventsParams });
      const eventItems = eventsRes.data || [];

      if (clubId === ALL_CLUBS_VALUE) {
        setMembers([]);
        setApplications([]);
      } else {
        const [membersRes, applicationsRes] = await Promise.all([
          apiClient.get(`/clubs/${clubId}/members`),
          apiClient.get(`/clubs/${clubId}/applications`)
        ]);
        setMembers(membersRes.data || []);
        setApplications(applicationsRes.data || []);
      }

      setEvents(eventItems);
      if (studentMode) {
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
      const analyticsRes = await apiClient.get(`/clubs/${clubId}/analytics`);
      setAnalytics(analyticsRes.data || null);
    } catch {
      setAnalytics(null);
    }
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
      pushToast({ title: 'Refresh failed', description: message, variant: 'error' });
    }
  }

  async function createClub(payload) {
    await apiClient.post('/clubs/', payload);
    await refreshClubs();
  }

  async function joinClub(clubId) {
    try {
      const response = await apiClient.post(`/clubs/${clubId}/join`);
      pushToast({
        title: response.data?.status === 'approved' ? 'Joined club' : 'Application submitted',
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
      await Promise.all([loadSelectedClubData(selectedClubId, isStudent), refreshClubs()]);
    } catch (err) {
      pushToast({ title: 'Review failed', description: formatApiError(err, 'Could not review application'), variant: 'error' });
    }
  }

  async function createEvent(payload) {
    await apiClient.post('/club-events/', payload);
    pushToast({ title: 'Event created', description: 'Club event created successfully.', variant: 'success' });
    await loadSelectedClubData(selectedClubId, isStudent);
  }

  async function registerForEvent({ registrationEvent, registrationForm, paymentReceiptFile }) {
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
    await loadSelectedClubData(selectedClubId, true);
  }

  return {
    analytics,
    applications,
    canManageClub,
    clubDataLoadError,
    clubs,
    clubsLoadError,
    createClub,
    createEvent,
    eventRegistrations,
    events,
    isAdmin,
    isClubPresident,
    isStudent,
    joinClub,
    loadingClubs,
    members,
    refreshClubs,
    registerForEvent,
    reviewApplication,
    selectedClub,
    selectedClubId,
    setSelectedClubId,
    students,
    teachers,
    updateClubStatus,
    toggleRegistration
  };
}
