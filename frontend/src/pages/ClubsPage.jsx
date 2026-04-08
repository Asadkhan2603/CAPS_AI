import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import Card from '../components/ui/Card';
import EmptyState from '../components/ui/EmptyState';
import FormInput from '../components/ui/FormInput';
import Modal from '../components/ui/Modal';
import Table from '../components/ui/Table';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { apiClient } from '../services/apiClient';
import { formatApiError } from '../utils/apiError';
import { activeClubStatuses, clubStatusOptions, initialCreateForm, initialEventForm, tabs } from './clubs/constants';
import ClubAnnouncementsPanel from './clubs/ClubAnnouncementsPanel';
import EventRegistrationForm from './clubs/EventRegistrationForm';
import { getEventRegistrationAvailability } from './clubs/eventRegistration';
import { buildClubPerformanceMonitor } from './clubs/performanceMonitor';
import { useClubDirectory } from './clubs/useClubDirectory';
import { useClubRegistrationFlow } from './clubs/useClubRegistrationFlow';

function normalizeAchievementHighlights(rawValue) {
  const values = Array.isArray(rawValue)
    ? rawValue
    : String(rawValue || '')
        .split(/\r?\n|,/)
        .map((item) => item.trim());
  return values.filter(Boolean).slice(0, 8);
}

function formatAchievementHighlightsField(rawValue) {
  return normalizeAchievementHighlights(rawValue).join('\n');
}

export default function ClubsPage() {
  const { user } = useAuth();
  const { pushToast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  const [activeTab, setActiveTab] = useState('overview');
  const [statusFilter, setStatusFilter] = useState('active');
  const [search, setSearch] = useState('');
  const [createForm, setCreateForm] = useState(initialCreateForm);
  const [createLoading, setCreateLoading] = useState(false);
  const [eventForm, setEventForm] = useState(initialEventForm);
  const [eventLoading, setEventLoading] = useState(false);
  const [memberEditor, setMemberEditor] = useState(null);
  const [memberEditorForm, setMemberEditorForm] = useState({ role: 'member', status: 'active' });
  const [memberEditorSaving, setMemberEditorSaving] = useState(false);
  const [applicationContextTarget, setApplicationContextTarget] = useState(null);
  const [applicationContextForm, setApplicationContextForm] = useState({ queue_owner_user_id: '', coordinator_note: '' });
  const [applicationContextSaving, setApplicationContextSaving] = useState(false);
  const [applicationSearch, setApplicationSearch] = useState('');
  const [applicationStatusFilter, setApplicationStatusFilter] = useState('all');
  const [applicationPage, setApplicationPage] = useState(1);
  const [applicationPageSize, setApplicationPageSize] = useState(8);
  const [savedApplicationFilters, setSavedApplicationFilters] = useState([]);
  const [applicationSnapshots, setApplicationSnapshots] = useState([]);
  const [selectedApplicationIds, setSelectedApplicationIds] = useState([]);
  const [enrollmentModalEvent, setEnrollmentModalEvent] = useState(null);
  const [enrollments, setEnrollments] = useState([]);
  const [loadingEnrollments, setLoadingEnrollments] = useState(false);
  const [eventHistory, setEventHistory] = useState(null);
  const [enrollmentSearch, setEnrollmentSearch] = useState('');
  const [enrollmentStatusFilter, setEnrollmentStatusFilter] = useState('all');
  const [enrollmentPage, setEnrollmentPage] = useState(1);
  const [enrollmentPageSize, setEnrollmentPageSize] = useState(8);
  const [savedEnrollmentFilters, setSavedEnrollmentFilters] = useState([]);
  const [enrollmentSnapshots, setEnrollmentSnapshots] = useState([]);
  const [selectedEnrollmentIds, setSelectedEnrollmentIds] = useState([]);
  const [enrollmentContextTarget, setEnrollmentContextTarget] = useState(null);
  const [enrollmentContextForm, setEnrollmentContextForm] = useState({ queue_owner_user_id: '', coordinator_note: '' });
  const [enrollmentContextSaving, setEnrollmentContextSaving] = useState(false);
  const [eventSearch, setEventSearch] = useState('');
  const [eventStatusFilter, setEventStatusFilter] = useState('all');
  const [eventPage, setEventPage] = useState(1);
  const [eventPageSize, setEventPageSize] = useState(8);
  const [financialProfileModalOpen, setFinancialProfileModalOpen] = useState(false);
  const [financialProfileForm, setFinancialProfileForm] = useState({
    sponsorship_target_amount: '',
    sponsorship_committed_amount: '',
    sponsorship_notes: ''
  });
  const [financialProfileSaving, setFinancialProfileSaving] = useState(false);
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [profileForm, setProfileForm] = useState({
    tagline: '',
    achievement_highlights: '',
    recruitment_headline: '',
    recruitment_cta_label: '',
    public_contact_url: '',
    logo_url: '',
    banner_url: ''
  });
  const [profileSaving, setProfileSaving] = useState(false);
  const {
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
    toggleRegistration,
    updateClubStatus,
    workspacePerformance
  } = useClubDirectory({ pushToast, user });

  const filteredClubs = useMemo(() => {
    const text = search.trim().toLowerCase();
    return clubs.filter((club) => {
      const statusPass = statusFilter ? club.status === statusFilter : true;
      const textPass = text
        ? [
            club.name,
            club.category,
            club.description,
            club.tagline,
            club.recruitment_headline,
            ...(club.achievement_highlights || []),
          ]
            .filter(Boolean)
            .some((value) => String(value).toLowerCase().includes(text))
        : true;
      return statusPass && textPass;
    });
  }, [clubs, search, statusFilter]);
  const {
    closeRegistrationModal,
    openRegistrationModal,
    paymentReceiptFile,
    registrationEvent,
    registrationForm,
    registrationModalOpen,
    registrationSubmitting,
    setPaymentReceiptFile,
    setRegistrationForm,
    submitEventRegistrationForm
  } = useClubRegistrationFlow({
    onSubmitRegistration: registerForEvent,
    pushToast,
    user
  });
  const requestedTab = searchParams.get('tab') || '';
  const requestedClubId = searchParams.get('club_id') || '';
  const requestedRegistrationEventId = searchParams.get('register_event_id') || '';

  useEffect(() => {
    if (!requestedTab || !tabs.some((tab) => tab.key === requestedTab)) {
      return;
    }
    setActiveTab(requestedTab);
  }, [requestedTab]);

  useEffect(() => {
    if (!requestedClubId || requestedClubId === selectedClubId) {
      return;
    }
    setSelectedClubId(requestedClubId);
  }, [requestedClubId, selectedClubId, setSelectedClubId]);

  useEffect(() => {
    if (!isStudent || !requestedRegistrationEventId || !events.length) {
      return;
    }
    const targetEvent = events.find((item) => item.id === requestedRegistrationEventId);
    if (!targetEvent) {
      return;
    }
    openRegistrationModal(targetEvent);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('tab', 'events');
    nextParams.set('club_id', targetEvent.club_id || requestedClubId || selectedClubId || '');
    nextParams.delete('register_event_id');
    setSearchParams(nextParams, { replace: true });
  }, [events, isStudent, openRegistrationModal, requestedClubId, requestedRegistrationEventId, searchParams, selectedClubId, setSearchParams]);

  useEffect(() => {
    setSelectedApplicationIds([]);
  }, [selectedClubId, applicationSearch, applicationStatusFilter, applications.length]);

  useEffect(() => {
    setSelectedEnrollmentIds([]);
  }, [enrollmentModalEvent?.id, enrollmentSearch, enrollmentStatusFilter, enrollments.length]);

  useEffect(() => {
    setApplicationPage(1);
  }, [selectedClubId, applicationSearch, applicationStatusFilter, applicationPageSize]);

  useEffect(() => {
    setEnrollmentPage(1);
  }, [enrollmentModalEvent?.id, enrollmentSearch, enrollmentStatusFilter, enrollmentPageSize]);

  useEffect(() => {
    setEventPage(1);
  }, [selectedClubId, eventSearch, eventStatusFilter, eventPageSize]);

  function openFinancialProfileEditor() {
    if (!selectedClub) return;
    setFinancialProfileForm({
      sponsorship_target_amount:
        selectedClub.sponsorship_target_amount != null ? String(selectedClub.sponsorship_target_amount) : '',
      sponsorship_committed_amount:
        selectedClub.sponsorship_committed_amount != null ? String(selectedClub.sponsorship_committed_amount) : '',
      sponsorship_notes: selectedClub.sponsorship_notes || ''
    });
    setFinancialProfileModalOpen(true);
  }

  function openClubProfileEditor() {
    if (!selectedClub) return;
    setProfileForm({
      tagline: selectedClub.tagline || '',
      achievement_highlights: formatAchievementHighlightsField(selectedClub.achievement_highlights || []),
      recruitment_headline: selectedClub.recruitment_headline || '',
      recruitment_cta_label: selectedClub.recruitment_cta_label || '',
      public_contact_url: selectedClub.public_contact_url || '',
      logo_url: selectedClub.logo_url || '',
      banner_url: selectedClub.banner_url || ''
    });
    setProfileModalOpen(true);
  }

  function closeClubProfileEditor() {
    if (profileSaving) return;
    setProfileModalOpen(false);
  }

  function closeFinancialProfileEditor() {
    if (financialProfileSaving) return;
    setFinancialProfileModalOpen(false);
  }

  async function submitFinancialProfile(event) {
    event.preventDefault();
    if (!selectedClub) return;
    setFinancialProfileSaving(true);
    try {
      await updateClubSettings(
        selectedClub.id,
        {
          sponsorship_target_amount:
            financialProfileForm.sponsorship_target_amount === ''
              ? null
              : Number(financialProfileForm.sponsorship_target_amount),
          sponsorship_committed_amount:
            financialProfileForm.sponsorship_committed_amount === ''
              ? null
              : Number(financialProfileForm.sponsorship_committed_amount),
          sponsorship_notes: financialProfileForm.sponsorship_notes || null
        },
        'Funding profile updated.'
      );
      await reloadSelectedClubData();
      setFinancialProfileModalOpen(false);
    } finally {
      setFinancialProfileSaving(false);
    }
  }

  async function submitClubProfile(event) {
    event.preventDefault();
    if (!selectedClub) return;
    setProfileSaving(true);
    try {
      await updateClubSettings(
        selectedClub.id,
        {
          tagline: profileForm.tagline || null,
          achievement_highlights: normalizeAchievementHighlights(profileForm.achievement_highlights),
          recruitment_headline: profileForm.recruitment_headline || null,
          recruitment_cta_label: profileForm.recruitment_cta_label || null,
          public_contact_url: profileForm.public_contact_url || null,
          logo_url: profileForm.logo_url || null,
          banner_url: profileForm.banner_url || null
        },
        'Club profile updated.'
      );
      await reloadSelectedClubData();
      setProfileModalOpen(false);
    } finally {
      setProfileSaving(false);
    }
  }

  useEffect(() => {
    if (!selectedClub?.id || !canManageClub(selectedClub)) {
      setSavedApplicationFilters([]);
      setApplicationSnapshots([]);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const [viewsResponse, historyResponse] = await Promise.all([
          apiClient.get(`/clubs/${selectedClub.id}/applications/views`),
          apiClient.get(`/clubs/${selectedClub.id}/applications/history`, { params: { limit: 12 } })
        ]);
        if (cancelled) return;
        setSavedApplicationFilters(viewsResponse.data || []);
        setApplicationSnapshots(historyResponse.data || []);
      } catch {
        if (cancelled) return;
        setSavedApplicationFilters([]);
        setApplicationSnapshots([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [applications, selectedClub?.id, user?.id]);

  useEffect(() => {
    if (!enrollmentModalEvent?.id) {
      setSavedEnrollmentFilters([]);
      setEnrollmentSnapshots([]);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const [viewsResponse, historyResponse] = await Promise.all([
          apiClient.get('/event-registrations/views', { params: { event_id: enrollmentModalEvent.id } }),
          apiClient.get('/event-registrations/history', { params: { event_id: enrollmentModalEvent.id, limit: 12 } })
        ]);
        if (cancelled) return;
        setSavedEnrollmentFilters(viewsResponse.data || []);
        setEnrollmentSnapshots(historyResponse.data || []);
      } catch {
        if (cancelled) return;
        setSavedEnrollmentFilters([]);
        setEnrollmentSnapshots([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [enrollmentModalEvent?.id, enrollments]);

  function closeRegistrationExperience() {
    closeRegistrationModal();
    if (!searchParams.get('register_event_id')) {
      return;
    }
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('register_event_id');
    setSearchParams(nextParams, { replace: true });
  }

  async function submitCreateClub(event) {
    event.preventDefault();
    setCreateLoading(true);
    try {
      const payload = {
        ...createForm,
        max_members: createForm.max_members ? Number(createForm.max_members) : null,
        coordinator_user_id: createForm.coordinator_user_id || null,
        tagline: createForm.tagline || null,
        achievement_highlights: normalizeAchievementHighlights(createForm.achievement_highlights),
        recruitment_headline: createForm.recruitment_headline || null,
        recruitment_cta_label: createForm.recruitment_cta_label || null,
        public_contact_url: createForm.public_contact_url || null
      };
      await createClub(payload);
      setCreateForm(initialCreateForm);
      pushToast({ title: 'Club created', description: 'New club created successfully.', variant: 'success' });
    } catch (err) {
      pushToast({ title: 'Create failed', description: formatApiError(err, 'Failed to create club'), variant: 'error' });
    } finally {
      setCreateLoading(false);
    }
  }

  async function submitCreateEvent(event) {
    event.preventDefault();
    if (!selectedClub) {
      pushToast({ title: 'Select a club', description: 'Choose a club in the workspace rail before creating an event.', variant: 'error' });
      return;
    }
    setEventLoading(true);
    try {
      const payload = {
        club_id: selectedClub.id,
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
      };
      await createEvent(payload);
      setEventForm(initialEventForm);
    } catch (err) {
      pushToast({ title: 'Create failed', description: formatApiError(err, 'Failed to create event'), variant: 'error' });
    } finally {
      setEventLoading(false);
    }
  }

  async function loadEventEnrollments(eventRow) {
    if (!eventRow?.id) return;
    setEnrollmentModalEvent(eventRow);
    setLoadingEnrollments(true);
    try {
      const [enrollmentResponse, historyResponse] = await Promise.all([
        apiClient.get('/event-registrations/', {
          params: { event_id: eventRow.id, skip: 0, limit: 100 }
        }),
        apiClient.get(`/clubs/${eventRow.club_id}/events/${eventRow.id}/history`, {
          params: { limit: 24 }
        })
      ]);
      setEnrollments(enrollmentResponse.data || []);
      setEventHistory(historyResponse.data || null);
    } catch (err) {
      setEnrollments([]);
      setEventHistory(null);
      pushToast({
        title: 'Load failed',
        description: formatApiError(err, 'Failed to load event enrollments'),
        variant: 'error'
      });
    } finally {
      setLoadingEnrollments(false);
    }
  }

  async function updateEnrollment(row, patch, successMessage) {
    if (!row?.id || !enrollmentModalEvent?.id) return;
    setLoadingEnrollments(true);
    try {
      await apiClient.patch(`/event-registrations/${row.id}`, patch);
      pushToast({
        title: 'Enrollment updated',
        description: successMessage,
        variant: 'success'
      });
      await loadEventEnrollments(enrollmentModalEvent);
    } catch (err) {
      pushToast({
        title: 'Update failed',
        description: formatApiError(err, 'Failed to update event enrollment'),
        variant: 'error'
      });
      setLoadingEnrollments(false);
    }
  }

  function toggleSelectedId(setter, rowId) {
    setter((current) => (
      current.includes(rowId)
        ? current.filter((item) => item !== rowId)
        : [...current, rowId]
    ));
  }

  function toggleAllSelectedIds(setter, rows, selectedIds) {
    const rowIds = rows.map((row) => row.id).filter(Boolean);
    const allSelected = rowIds.length > 0 && rowIds.every((rowId) => selectedIds.includes(rowId));
    setter(allSelected ? [] : rowIds);
  }

  async function runBulkApplicationAction(status) {
    if (!selectedApplicationIds.length) return;
    await bulkReviewApplications(selectedApplicationIds, status);
    setSelectedApplicationIds([]);
  }

  async function sendApplicationReminder(mode = 'selected') {
    const hasSelection = selectedApplicationIds.length > 0;
    const payload = mode === 'selected' && hasSelection
      ? { applicationIds: selectedApplicationIds }
      : { statusFilter: applicationStatusFilter === 'all' ? null : applicationStatusFilter };
    await remindApplications(payload);
  }

  async function saveCurrentApplicationFilter() {
    if (!selectedClub?.id) return;
    const presetName = buildSavedFilterName(applicationStatusFilter, applicationSearch);
    try {
      const response = await apiClient.post(`/clubs/${selectedClub.id}/applications/views`, {
        name: presetName,
        filters: {
          search: applicationSearch,
          status: applicationStatusFilter,
          page_size: applicationPageSize
        }
      });
      setSavedApplicationFilters((current) => [response.data, ...current].slice(0, 12));
      pushToast({
        title: 'View saved',
        description: `Saved shared membership view "${presetName}".`,
        variant: 'success'
      });
    } catch (err) {
      pushToast({
        title: 'Save failed',
        description: formatApiError(err, 'Failed to save shared membership view'),
        variant: 'error'
      });
    }
  }

  function applyApplicationFilter(filter) {
    const filters = filter.filters || filter;
    setApplicationSearch(filters.search || '');
    setApplicationStatusFilter(filters.status || 'all');
    setApplicationPageSize(filters.page_size || filters.pageSize || 8);
    setApplicationPage(1);
  }

  async function deleteApplicationFilter(filterId) {
    if (!selectedClub?.id) return;
    try {
      await apiClient.delete(`/clubs/${selectedClub.id}/applications/views/${filterId}`);
      setSavedApplicationFilters((current) => current.filter((item) => item.id !== filterId));
    } catch (err) {
      pushToast({
        title: 'Delete failed',
        description: formatApiError(err, 'Failed to remove shared membership view'),
        variant: 'error'
      });
    }
  }

  async function runBulkEnrollmentAction(payload) {
    if (!selectedEnrollmentIds.length) return;
    setLoadingEnrollments(true);
    try {
      await bulkUpdateEventRegistrations(selectedEnrollmentIds, payload);
      if (enrollmentModalEvent) {
        await loadEventEnrollments(enrollmentModalEvent);
      }
      setSelectedEnrollmentIds([]);
    } finally {
      setLoadingEnrollments(false);
    }
  }

  async function sendEnrollmentReminder(mode = 'selected') {
    if (!enrollmentModalEvent?.id) return;
    const hasSelection = selectedEnrollmentIds.length > 0;
    const payload = mode === 'selected' && hasSelection
      ? { eventId: enrollmentModalEvent.id, registrationIds: selectedEnrollmentIds }
      : { eventId: enrollmentModalEvent.id, statusFilter: enrollmentStatusFilter === 'all' ? null : enrollmentStatusFilter };
    await remindEventRegistrations(payload);
  }

  async function saveCurrentEnrollmentFilter() {
    if (!enrollmentModalEvent?.id) return;
    const presetName = buildSavedFilterName(enrollmentStatusFilter, enrollmentSearch);
    try {
      const response = await apiClient.post(`/event-registrations/views?event_id=${encodeURIComponent(enrollmentModalEvent.id)}`, {
        name: presetName,
        filters: {
          search: enrollmentSearch,
          status: enrollmentStatusFilter,
          page_size: enrollmentPageSize
        }
      });
      setSavedEnrollmentFilters((current) => [response.data, ...current].slice(0, 12));
      pushToast({
        title: 'View saved',
        description: `Saved shared enrollment view "${presetName}".`,
        variant: 'success'
      });
    } catch (err) {
      pushToast({
        title: 'Save failed',
        description: formatApiError(err, 'Failed to save shared enrollment view'),
        variant: 'error'
      });
    }
  }

  function applyEnrollmentFilter(filter) {
    const filters = filter.filters || filter;
    setEnrollmentSearch(filters.search || '');
    setEnrollmentStatusFilter(filters.status || 'all');
    setEnrollmentPageSize(filters.page_size || filters.pageSize || 8);
    setEnrollmentPage(1);
  }

  async function deleteEnrollmentFilter(filterId) {
    if (!enrollmentModalEvent?.id) return;
    try {
      await apiClient.delete(`/event-registrations/views/${filterId}`, {
        params: { event_id: enrollmentModalEvent.id }
      });
      setSavedEnrollmentFilters((current) => current.filter((item) => item.id !== filterId));
    } catch (err) {
      pushToast({
        title: 'Delete failed',
        description: formatApiError(err, 'Failed to remove shared enrollment view'),
        variant: 'error'
      });
    }
  }

  async function updateEventStatus(eventRow, nextStatus, successMessage) {
    if (!eventRow?.id) return;
    try {
      await apiClient.put(`/club-events/${eventRow.id}`, { status: nextStatus });
      pushToast({
        title: 'Event updated',
        description: successMessage,
        variant: 'success'
      });
      await refreshClubs();
    } catch (err) {
      pushToast({
        title: 'Event update failed',
        description: formatApiError(err, 'Failed to update event status'),
        variant: 'error'
      });
    }
  }

  const eventRegistrationByEventId = useMemo(() => {
    const map = new Map();
    for (const reg of eventRegistrations) {
      map.set(reg.event_id, reg);
    }
    return map;
  }, [eventRegistrations]);
  const selectedClubCanManage = Boolean(selectedClub && canManageClub(selectedClub));
  const selectedClubCanLeadEvents = Boolean(selectedClub && (selectedClubCanManage || isClubPresident(selectedClub)));
  const selectedClubAchievements = useMemo(
    () => normalizeAchievementHighlights(selectedClub?.achievement_highlights || []),
    [selectedClub?.achievement_highlights]
  );
  const selectedClubRecruitmentLabel = selectedClub?.recruitment_cta_label || 'Contact Club';
  const queueOwnerOptions = useMemo(
    () => buildQueueOwnerOptions({ currentUser: user, isAdmin, selectedClub, teachers }),
    [isAdmin, selectedClub, teachers, user]
  );

  function openClub(clubId) {
    setSelectedClubId(clubId);
    setActiveTab('overview');
  }

  function openMemberEditor(member) {
    setMemberEditor(member);
    setMemberEditorForm({
      role: member.role || 'member',
      status: member.status || 'active'
    });
  }

  function closeMemberEditor() {
    setMemberEditor(null);
    setMemberEditorSaving(false);
    setMemberEditorForm({ role: 'member', status: 'active' });
  }

  function openApplicationContextEditor(application) {
    setApplicationContextTarget(application);
    setApplicationContextForm({
      queue_owner_user_id: application.queue_owner_user_id || '',
      coordinator_note: application.coordinator_note || ''
    });
  }

  function closeApplicationContextEditor() {
    setApplicationContextTarget(null);
    setApplicationContextSaving(false);
    setApplicationContextForm({ queue_owner_user_id: '', coordinator_note: '' });
  }

  function openEnrollmentContextEditor(enrollment) {
    setEnrollmentContextTarget(enrollment);
    setEnrollmentContextForm({
      queue_owner_user_id: enrollment.queue_owner_user_id || '',
      coordinator_note: enrollment.coordinator_note || ''
    });
  }

  function closeEnrollmentContextEditor() {
    setEnrollmentContextTarget(null);
    setEnrollmentContextSaving(false);
    setEnrollmentContextForm({ queue_owner_user_id: '', coordinator_note: '' });
  }

  const activePresidentMember = useMemo(
    () => members.find((member) => member.role === 'president' && member.status === 'active') || null,
    [members]
  );
  const activeMembersCount = useMemo(
    () => members.filter((member) => member.status === 'active').length,
    [members]
  );
  const pendingApplicationsCount = useMemo(
    () => applications.filter((item) => item.status === 'pending').length,
    [applications]
  );
  const waitlistedApplicationsCount = useMemo(
    () => applications.filter((item) => item.status === 'waitlisted').length,
    [applications]
  );
  const filteredApplications = useMemo(() => {
    const query = applicationSearch.trim().toLowerCase();
    return applications.filter((application) => {
      const statusPass = applicationStatusFilter === 'all' ? true : application.status === applicationStatusFilter;
      const searchPass = query
        ? [application.student_name, application.student_email, application.public_id]
            .filter(Boolean)
            .some((value) => String(value).toLowerCase().includes(query))
        : true;
      return statusPass && searchPass;
    });
  }, [applicationSearch, applicationStatusFilter, applications]);
  const upcomingEvents = useMemo(() => {
    const now = Date.now();
    return [...events]
      .filter((item) => {
        if (item.status === 'archived') return false;
        if (!item.event_date) return true;
        return new Date(item.event_date).getTime() >= now;
      })
      .sort((left, right) => {
        const leftTime = left.event_date ? new Date(left.event_date).getTime() : Number.MAX_SAFE_INTEGER;
        const rightTime = right.event_date ? new Date(right.event_date).getTime() : Number.MAX_SAFE_INTEGER;
        return leftTime - rightTime;
      });
  }, [events]);
  const archivedEventsCount = useMemo(
    () => events.filter((eventItem) => eventItem.status === 'archived').length,
    [events]
  );
  const filteredEvents = useMemo(() => {
    const query = eventSearch.trim().toLowerCase();
    return events.filter((eventItem) => {
      const searchPass = query
        ? [eventItem.title, eventItem.event_type, eventItem.public_id]
            .filter(Boolean)
            .some((value) => String(value).toLowerCase().includes(query))
        : true;
      let statusPass = true;
      if (eventStatusFilter === 'live') {
        statusPass = ['draft', 'open', 'closed'].includes(eventItem.status);
      } else if (eventStatusFilter === 'completed') {
        statusPass = eventItem.status === 'completed';
      } else if (eventStatusFilter === 'archived') {
        statusPass = eventItem.status === 'archived';
      }
      return searchPass && statusPass;
    });
  }, [eventSearch, eventStatusFilter, events]);
  const filteredEnrollments = useMemo(() => {
    const query = enrollmentSearch.trim().toLowerCase();
    return enrollments.filter((enrollment) => {
      const statusPass = enrollmentStatusFilter === 'all' ? true : enrollment.status === enrollmentStatusFilter;
      const searchPass = query
        ? [enrollment.student_name, enrollment.student_email, enrollment.email, enrollment.public_id]
            .filter(Boolean)
            .some((value) => String(value).toLowerCase().includes(query))
        : true;
      return searchPass && statusPass;
    });
  }, [enrollmentSearch, enrollmentStatusFilter, enrollments]);
  const selectedApplications = useMemo(
    () => applications.filter((application) => selectedApplicationIds.includes(application.id)),
    [applications, selectedApplicationIds]
  );
  const selectedEnrollments = useMemo(
    () => enrollments.filter((enrollment) => selectedEnrollmentIds.includes(enrollment.id)),
    [enrollments, selectedEnrollmentIds]
  );
  const pagedApplications = useMemo(() => {
    const start = (applicationPage - 1) * applicationPageSize;
    return filteredApplications.slice(start, start + applicationPageSize);
  }, [applicationPage, applicationPageSize, filteredApplications]);
  const pagedEnrollments = useMemo(() => {
    const start = (enrollmentPage - 1) * enrollmentPageSize;
    return filteredEnrollments.slice(start, start + enrollmentPageSize);
  }, [enrollmentPage, enrollmentPageSize, filteredEnrollments]);
  const pagedEvents = useMemo(() => {
    const start = (eventPage - 1) * eventPageSize;
    return filteredEvents.slice(start, start + eventPageSize);
  }, [eventPage, eventPageSize, filteredEvents]);
  const applicationPriorityCounts = useMemo(() => {
    return filteredApplications.reduce((acc, row) => {
      const meta = getQueueAgeMeta(row.applied_at, row.status);
      if (meta.priorityLabel in acc) {
        acc[meta.priorityLabel] += 1;
      }
      return acc;
    }, { stale: 0, aging: 0, fresh: 0 });
  }, [filteredApplications]);
  const enrollmentPriorityCounts = useMemo(() => {
    return filteredEnrollments.reduce((acc, row) => {
      const meta = getQueueAgeMeta(row.created_at, row.status);
      if (meta.priorityLabel in acc) {
        acc[meta.priorityLabel] += 1;
      }
      return acc;
    }, { stale: 0, aging: 0, fresh: 0 });
  }, [filteredEnrollments]);
  const membershipQueueRows = useMemo(
    () => applications.filter((row) => ['pending', 'waitlisted'].includes(row.status)),
    [applications]
  );
  const enrollmentQueueRows = useMemo(
    () => enrollments.filter((row) => ['pending', 'waitlisted'].includes(row.status)),
    [enrollments]
  );
  const membershipQueueSnapshot = useMemo(() => {
    const counts = membershipQueueRows.reduce((acc, row) => {
      const meta = getQueueAgeMeta(row.applied_at, row.status);
      acc[meta.priorityLabel] += 1;
      return acc;
    }, { fresh: 0, aging: 0, stale: 0 });
    return {
      total: membershipQueueRows.length,
      pending: membershipQueueRows.filter((row) => row.status === 'pending').length,
      waitlisted: membershipQueueRows.filter((row) => row.status === 'waitlisted').length,
      ...counts,
      signature: `m-${membershipQueueRows.length}-${counts.fresh}-${counts.aging}-${counts.stale}`
    };
  }, [membershipQueueRows]);
  const enrollmentQueueSnapshot = useMemo(() => {
    const counts = enrollmentQueueRows.reduce((acc, row) => {
      const meta = getQueueAgeMeta(row.created_at, row.status);
      acc[meta.priorityLabel] += 1;
      return acc;
    }, { fresh: 0, aging: 0, stale: 0 });
    return {
      total: enrollmentQueueRows.length,
      pending: enrollmentQueueRows.filter((row) => row.status === 'pending').length,
      waitlisted: enrollmentQueueRows.filter((row) => row.status === 'waitlisted').length,
      ...counts,
      signature: `e-${enrollmentQueueRows.length}-${counts.fresh}-${counts.aging}-${counts.stale}`
    };
  }, [enrollmentQueueRows]);

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(filteredApplications.length / applicationPageSize));
    if (applicationPage > totalPages) {
      setApplicationPage(totalPages);
    }
  }, [applicationPage, applicationPageSize, filteredApplications.length]);

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(filteredEnrollments.length / enrollmentPageSize));
    if (enrollmentPage > totalPages) {
      setEnrollmentPage(totalPages);
    }
  }, [enrollmentPage, enrollmentPageSize, filteredEnrollments.length]);

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(filteredEvents.length / eventPageSize));
    if (eventPage > totalPages) {
      setEventPage(totalPages);
    }
  }, [eventPage, eventPageSize, filteredEvents.length]);

  const overviewEvents = useMemo(() => upcomingEvents.slice(0, 3), [upcomingEvents]);
  const isDormantClub = selectedClub?.status === 'dormant';
  const isEmptyClub = Boolean(selectedClub) && members.length === 0 && events.length === 0 && applications.length === 0;
  const isLargeClub = members.length >= 120 || events.length >= 40 || applications.length >= 80;
  const clubPerformanceMonitor = useMemo(
    () => buildClubPerformanceMonitor({
      selectedClub,
      workspacePerformance,
      members,
      applications,
      events,
      eventRegistrations
    }),
    [applications, eventRegistrations, events, members, selectedClub, workspacePerformance]
  );
  const edgeCaseNotice = useMemo(() => {
    if (!selectedClub) return null;
    if (isDormantClub) {
      return {
        tone: 'amber',
        title: 'Dormant club workspace',
        description: 'This club is marked dormant, so the workspace should focus on recovery: reopen intake carefully, plan a restart event, and rebuild the active roster before treating current metrics as normal operations.'
      };
    }
    if (isEmptyClub) {
      return {
        tone: 'emerald',
        title: 'New club starting point',
        description: 'This club has no members, applications, or events yet. The next useful move is to assign leadership clearly, open intake if appropriate, and create the first event or announcement from this workspace.'
      };
    }
    if (isLargeClub) {
      return {
        tone: 'brand',
        title: 'High-volume club workspace',
        description: 'This club is operating at larger volume. Use saved views, pagination, exports, history drilldowns, and trend signals to avoid reading the whole workspace as one long list.'
      };
    }
    return null;
  }, [applications.length, events.length, isDormantClub, isEmptyClub, isLargeClub, members.length, selectedClub]);
  const selectedClubOverviewStats = useMemo(() => {
    if (!selectedClub) return [];
    return [
      { label: 'Members', value: selectedClub.member_count ?? members.length, detail: `${activeMembersCount} active` },
      {
        label: 'Applications',
        value: pendingApplicationsCount + waitlistedApplicationsCount,
        detail: selectedClubCanManage
          ? `${pendingApplicationsCount} pending • ${waitlistedApplicationsCount} waitlisted`
          : 'membership pipeline'
      },
      { label: 'Events', value: events.length, detail: `${upcomingEvents.length} upcoming` },
      {
        label: isStudent ? 'My Registrations' : 'Club Waitlist',
        value: isStudent
          ? eventRegistrations.filter((item) => events.some((eventItem) => eventItem.id === item.event_id)).length
          : analytics?.waitlisted_applications ?? 0,
        detail: isStudent ? 'for this club' : 'students waiting for intake'
      }
    ];
  }, [activeMembersCount, analytics?.waitlisted_applications, eventRegistrations, events, isStudent, members.length, pendingApplicationsCount, selectedClub, selectedClubCanManage, upcomingEvents.length, waitlistedApplicationsCount]);
  const workspaceActionButtons = useMemo(() => {
    if (!selectedClub) return [];

    const actions = [];

    if (isStudent) {
      actions.push({
        key: 'join',
        label: 'Join Club',
        className: 'btn-primary',
        disabled: !activeClubStatuses.has(selectedClub.status) || !selectedClub.registration_open,
        onClick: () => joinClub(selectedClub.id)
      });
    }

    if (selectedClubCanManage) {
      if (activeClubStatuses.has(selectedClub.status)) {
        actions.push({
          key: 'intake',
          label: selectedClub.registration_open ? 'Pause Intake' : 'Open Intake',
          className: 'btn-secondary',
          onClick: () => toggleRegistration(selectedClub)
        });
      }
      if (selectedClub.status !== 'active') {
        actions.push({
          key: 'activate',
          label: 'Activate Club',
          className: 'btn-secondary',
          onClick: () => updateClubStatus(selectedClub, 'active')
        });
      }
      if (selectedClub.status === 'active') {
        actions.push({
          key: 'finish-intake',
          label: 'Finish Intake',
          className: 'btn-secondary',
          onClick: () => updateClubStatus(selectedClub, 'registration_closed')
        });
      }
    }

    if (selectedClubCanLeadEvents) {
      actions.push({
        key: 'open-events',
        label: 'Open Event Center',
        className: 'btn-secondary',
        onClick: () => setActiveTab('events')
      });
    }

    if (selectedClubCanManage) {
      actions.push({
        key: 'open-members',
        label: 'Open Members',
        className: 'btn-secondary',
        onClick: () => setActiveTab('members')
      });
    }

    return actions;
  }, [isStudent, joinClub, selectedClub, selectedClubCanLeadEvents, selectedClubCanManage, toggleRegistration, updateClubStatus]);

  const memberRowActions = useMemo(() => {
    if (!selectedClubCanManage) {
      return [];
    }
    return [
      {
        key: 'manage-member',
        label: (row) => (row.role === 'president' ? 'Review President' : 'Manage'),
        onClick: (row) => openMemberEditor(row)
      }
    ];
  }, [selectedClubCanManage]);

  const eventRowActions = !selectedClubCanLeadEvents
    ? []
    : [
        {
          key: 'toggle-status',
          label: (row) => (row.status === 'open' ? 'Close Event' : 'Open Event'),
          hidden: (row) => row.status === 'archived',
          onClick: (row) => updateEventStatus(
            row,
            row.status === 'open' ? 'closed' : 'open',
            `Event status changed to ${row.status === 'open' ? 'closed' : 'open'}.`
          )
        },
        {
          key: 'archive-toggle',
          label: (row) => (row.status === 'archived' ? 'Restore Event' : 'Archive Event'),
          className: selectedClubCanManage ? '' : '!text-amber-700 dark:!text-amber-300',
          onClick: (row) => updateEventStatus(
            row,
            row.status === 'archived' ? 'open' : 'archived',
            row.status === 'archived' ? 'Event restored to open status.' : 'Event archived successfully.'
          )
        },
        {
          key: 'view-enrollments',
          label: 'View Enrollments',
          onClick: (row) => loadEventEnrollments(row)
        }
      ];

  const applicationRowActions = selectedClubCanManage
    ? [
        {
          key: 'context',
          label: 'Context',
          onClick: (row) => openApplicationContextEditor(row)
        },
        {
          key: 'promote-review',
          label: 'Move To Pending',
          hidden: (row) => selectedClub?.membership_type === 'open' || row.status !== 'waitlisted',
          onClick: (row) => reviewApplication(row.id, 'pending')
        },
        {
          key: 'approve',
          label: (row) => (row.status === 'waitlisted' ? 'Approve From Waitlist' : 'Approve'),
          hidden: (row) => !['pending', 'waitlisted'].includes(row.status),
          onClick: (row) => reviewApplication(row.id, 'approved')
        },
        {
          key: 'move-waitlist',
          label: 'Move To Waitlist',
          hidden: (row) => row.status !== 'pending',
          onClick: (row) => reviewApplication(row.id, 'waitlisted')
        },
        {
          key: 'reject',
          label: 'Reject',
          hidden: (row) => !['pending', 'waitlisted'].includes(row.status),
          onClick: (row) => reviewApplication(row.id, 'rejected')
        }
      ]
    : [];
  const canBulkApproveApplications = selectedApplications.length > 0 && selectedApplications.every((row) => ['pending', 'waitlisted'].includes(row.status));
  const canBulkWaitlistApplications = selectedApplications.length > 0 && selectedApplications.every((row) => row.status === 'pending');
  const canBulkRejectApplications = selectedApplications.length > 0 && selectedApplications.every((row) => ['pending', 'waitlisted'].includes(row.status));
  const canBulkPendingApplications = selectedApplications.length > 0
    && selectedClub?.membership_type !== 'open'
    && selectedApplications.every((row) => row.status === 'waitlisted');

  async function submitMemberEditor(event) {
    event.preventDefault();
    if (!memberEditor) return;

    if (
      memberEditorForm.role === 'president' &&
      activePresidentMember &&
      activePresidentMember.id !== memberEditor.id
    ) {
      pushToast({
        title: 'President already assigned',
        description: 'Demote the current president before promoting another member.',
        variant: 'error'
      });
      return;
    }

    const payload = {};
    if (memberEditorForm.role !== memberEditor.role) {
      payload.role = memberEditorForm.role;
    }
    if (memberEditorForm.status !== memberEditor.status) {
      payload.status = memberEditorForm.status;
    }

    if (!Object.keys(payload).length) {
      closeMemberEditor();
      return;
    }

    setMemberEditorSaving(true);
    try {
      await updateMember(memberEditor.id, payload);
      closeMemberEditor();
    } catch (err) {
      pushToast({
        title: 'Member update failed',
        description: formatApiError(err, 'Could not update member'),
        variant: 'error'
      });
      setMemberEditorSaving(false);
    }
  }

  async function submitApplicationContext(event) {
    event.preventDefault();
    if (!applicationContextTarget) return;
    setApplicationContextSaving(true);
    try {
      await reviewApplication(applicationContextTarget.id, {
        queue_owner_user_id: applicationContextForm.queue_owner_user_id || '',
        coordinator_note: applicationContextForm.coordinator_note
      });
      closeApplicationContextEditor();
    } catch {
      setApplicationContextSaving(false);
    }
  }

  async function submitEnrollmentContext(event) {
    event.preventDefault();
    if (!enrollmentContextTarget) return;
    setEnrollmentContextSaving(true);
    try {
      await updateEnrollment(
        enrollmentContextTarget,
        {
          queue_owner_user_id: enrollmentContextForm.queue_owner_user_id || '',
          coordinator_note: enrollmentContextForm.coordinator_note
        },
        'Enrollment owner and note saved.'
      );
      closeEnrollmentContextEditor();
    } catch {
      setEnrollmentContextSaving(false);
    }
  }

  const memberColumns = [
    { key: 'public_id', label: 'Short ID', render: (row) => row.public_id || '-' },
    { key: 'student_name', label: 'Student', render: (row) => row.student_name || row.student_email || '-' },
    { key: 'role', label: 'Role' },
    { key: 'status', label: 'Status' },
    { key: 'joined_at', label: 'Joined', render: (row) => (row.joined_at ? new Date(row.joined_at).toLocaleString() : '-') }
  ];

  const applicationColumns = [
    { key: 'public_id', label: 'Short ID', render: (row) => row.public_id || '-' },
    { key: 'student_name', label: 'Student', render: (row) => row.student_name || row.student_email || '-' },
    { key: 'status', label: 'Status' },
    { key: 'queue_owner_label', label: 'Owner', render: (row) => row.queue_owner_label || 'Unassigned' },
    {
      key: 'queue_age',
      label: 'Queue Age',
      render: (row) => getQueueAgeMeta(row.applied_at, row.status).ageLabel
    },
    {
      key: 'priority',
      label: 'Priority',
      render: (row) => {
        const meta = getQueueAgeMeta(row.applied_at, row.status);
        return (
          <span className={`rounded-full border px-2 py-0.5 text-[11px] uppercase tracking-wide ${toneToBadgeClass(meta.priorityTone)}`}>
            {meta.priorityLabel}
          </span>
        );
      }
    },
    {
      key: 'last_touched_at',
      label: 'Last Touched',
      render: (row) => formatQueueTouch(row.last_touched_at, row.last_touched_by_label)
    },
    {
      key: 'coordinator_note',
      label: 'Note',
      render: (row) => summarizeQueueNote(row.coordinator_note)
    },
    { key: 'applied_at', label: 'Applied', render: (row) => (row.applied_at ? new Date(row.applied_at).toLocaleString() : '-') }
  ];

  const eventColumns = [
    { key: 'title', label: 'Title' },
    { key: 'public_id', label: 'Short ID', render: (row) => row.public_id || '-' },
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
            const availability = getEventRegistrationAvailability(row);
            return (
              <button
                className="btn-primary !px-3 !py-1 text-xs"
                type="button"
                disabled={availability.disabled}
                title={availability.title}
                onClick={() => openRegistrationModal(row)}
              >
                {availability.label}
              </button>
            );
          }
        }]
      : [])
  ];

  const enrollmentColumns = [
    { key: 'student_name', label: 'Student', render: (row) => row.student_name || row.student_user_id || '-' },
    { key: 'student_email', label: 'Email', render: (row) => row.student_email || row.email || '-' },
    { key: 'status', label: 'Status' },
    { key: 'queue_owner_label', label: 'Owner', render: (row) => row.queue_owner_label || 'Unassigned' },
    {
      key: 'queue_age',
      label: 'Queue Age',
      render: (row) => getQueueAgeMeta(row.created_at, row.status).ageLabel
    },
    {
      key: 'priority',
      label: 'Priority',
      render: (row) => {
        const meta = getQueueAgeMeta(row.created_at, row.status);
        return (
          <span className={`rounded-full border px-2 py-0.5 text-[11px] uppercase tracking-wide ${toneToBadgeClass(meta.priorityTone)}`}>
            {meta.priorityLabel}
          </span>
        );
      }
    },
    {
      key: 'last_touched_at',
      label: 'Last Touched',
      render: (row) => formatQueueTouch(row.last_touched_at, row.last_touched_by_label)
    },
    { key: 'attendance_status', label: 'Attendance', render: (row) => row.attendance_status || '-' },
    { key: 'certificate_issued', label: 'Certificate', render: (row) => (row.certificate_issued ? 'Issued' : 'Not issued') },
    { key: 'coordinator_note', label: 'Note', render: (row) => summarizeQueueNote(row.coordinator_note) },
    { key: 'created_at', label: 'Registered At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
  ];

  const enrollmentRowActions = !selectedClubCanLeadEvents
    ? []
    : [
        {
          key: 'context',
          label: 'Context',
          onClick: (row) => openEnrollmentContextEditor(row)
        },
        {
          key: 'promote-waitlist',
          label: () => (enrollmentModalEvent?.approval_required ? 'Move To Pending' : 'Confirm Seat'),
          hidden: (row) => row.status !== 'waitlisted',
          onClick: (row) => updateEnrollment(
            row,
            { status: enrollmentModalEvent?.approval_required ? 'pending' : 'registered' },
            enrollmentModalEvent?.approval_required
              ? 'Waitlisted registration moved into the approval queue.'
              : 'Waitlisted registration promoted into a confirmed seat.'
          )
        },
        {
          key: 'approve',
          label: 'Approve',
          hidden: (row) => row.status !== 'pending',
          onClick: (row) => updateEnrollment(row, { status: 'approved' }, 'Registration approved.')
        },
        {
          key: 'reject',
          label: 'Reject',
          className: '!text-rose-600 dark:!text-rose-300',
          hidden: (row) => row.status !== 'pending',
          onClick: (row) => updateEnrollment(row, { status: 'rejected' }, 'Registration rejected.')
        },
        {
          key: 'move-waitlist',
          label: 'Move To Waitlist',
          hidden: (row) => row.status !== 'pending',
          onClick: (row) => updateEnrollment(row, { status: 'waitlisted' }, 'Registration moved to waitlist.')
        },
        {
          key: 'mark-present',
          label: 'Present',
          hidden: (row) => !['approved', 'registered'].includes(row.status) || row.attendance_status === 'present',
          onClick: (row) => updateEnrollment(row, { attendance_status: 'present' }, 'Attendance marked present.')
        },
        {
          key: 'mark-absent',
          label: 'Absent',
          hidden: (row) => !['approved', 'registered'].includes(row.status) || row.attendance_status === 'absent',
          onClick: (row) => updateEnrollment(row, { attendance_status: 'absent' }, 'Attendance marked absent.')
        },
        {
          key: 'issue-certificate',
          label: 'Issue Certificate',
          hidden: (row) => row.attendance_status !== 'present' || row.certificate_issued,
          onClick: (row) => updateEnrollment(row, { certificate_issued: true }, 'Certificate issued.')
        }
      ];
  const canPromoteEnrollments = selectedEnrollments.length > 0
    && selectedEnrollments.every((row) => row.status === 'waitlisted');
  const canApproveEnrollments = selectedEnrollments.length > 0
    && selectedEnrollments.every((row) => row.status === 'pending');
  const canWaitlistEnrollments = selectedEnrollments.length > 0
    && selectedEnrollments.every((row) => row.status === 'pending');
  const canRejectEnrollments = selectedEnrollments.length > 0
    && selectedEnrollments.every((row) => row.status === 'pending');
  const mobileAnalyticsCards = analytics ? [
    {
      key: 'membership',
      title: 'Membership Health',
      subtitle: 'Roster and growth snapshot',
      badges: ['members'],
      details: [
        { label: 'Total Members', value: analytics.total_members ?? 0 },
        { label: 'Active Members', value: analytics.active_members ?? 0 },
        { label: 'Inactive Members', value: analytics.inactive_members ?? 0 },
        { label: 'Growth (30d)', value: analytics.membership_growth_30d ?? 0 }
      ]
    },
    {
      key: 'engagement',
      title: 'Engagement Intelligence',
      subtitle: 'Retention, churn, and member participation signals',
      badges: ['engagement'],
      details: [
        { label: 'Retention (90d)', value: `${analytics.member_retention_pct_90d ?? 0}%` },
        { label: 'Churn (90d)', value: `${analytics.member_churn_rate_pct_90d ?? 0}%` },
        { label: 'Join To Event %', value: `${analytics.member_event_conversion_pct ?? 0}%` },
        { label: 'Join To Attend %', value: `${analytics.member_attendance_conversion_pct ?? 0}%` },
        { label: 'At-Risk Active Members', value: analytics.at_risk_active_members_90d ?? 0 }
      ]
    },
    {
      key: 'events',
      title: 'Event Activity',
      subtitle: 'Current event delivery status',
      badges: ['events'],
      details: [
        { label: 'Total Events', value: analytics.total_events ?? 0 },
        { label: 'Upcoming', value: analytics.upcoming_events ?? 0 },
        { label: 'Completed', value: analytics.completed_events ?? 0 },
        { label: 'Event Fill %', value: analytics.average_attendance_pct ?? 0 },
        { label: 'Events At Capacity', value: analytics.events_at_capacity ?? 0 }
      ]
    },
    {
      key: 'pipeline',
      title: 'Operations Pipeline',
      subtitle: 'What still needs attention',
      badges: ['pipeline'],
      details: [
        { label: 'Pending Applications', value: analytics.pending_applications ?? 0 },
        { label: 'Waitlisted Applications', value: analytics.waitlisted_applications ?? 0 },
        { label: 'Pending Event Reviews', value: analytics.pending_event_registrations ?? 0 },
        { label: 'Waitlisted Registrations', value: analytics.waitlisted_event_registrations ?? 0 },
        { label: 'Confirmed Seats', value: analytics.confirmed_event_registrations ?? 0 }
      ]
    },
    {
      key: 'delivery',
      title: 'Delivery Quality',
      subtitle: 'Attendance and certificate follow-through',
      badges: ['delivery'],
      details: [
        { label: 'Attendance Marked %', value: `${analytics.attendance_marked_pct ?? 0}%` },
        { label: 'No-Show Rate', value: `${analytics.no_show_rate_pct ?? 0}%` },
        { label: 'Certificates Issued', value: analytics.certificates_issued ?? 0 },
        { label: 'Certificate Coverage', value: `${analytics.certificate_issuance_pct ?? 0}%` },
        { label: 'Events With Waitlist', value: analytics.waitlist_pressure_events ?? 0 }
      ]
    },
    {
      key: 'trends',
      title: 'Trend Signals',
      subtitle: 'Repeated event patterns across recent activity',
      badges: ['trends'],
      details: [
        { label: 'Demand Trend', value: formatTrendSummaryValue(analytics.trend_summaries?.find((item) => item.key === 'demand')) },
        { label: 'No-Show Trend', value: formatTrendSummaryValue(analytics.trend_summaries?.find((item) => item.key === 'attendance')) },
        { label: 'Certificate Trend', value: formatTrendSummaryValue(analytics.trend_summaries?.find((item) => item.key === 'certificate')) },
        { label: 'Repeat Attention Events', value: analytics.repeat_attention_events ?? 0 }
      ]
    },
    {
      key: 'archive',
      title: 'Archive Insights',
      subtitle: 'Long-range performance from archived cycles',
      badges: ['archive'],
      details: [
        { label: 'Archived Events', value: analytics.archived_events ?? 0 },
        { label: 'Archived Seats', value: analytics.archived_confirmed_registrations ?? 0 },
        { label: 'Archived Attendance %', value: `${analytics.archived_attendance_marked_pct ?? 0}%` },
        { label: 'Archived No-Show', value: `${analytics.archived_no_show_rate_pct ?? 0}%` },
        { label: 'Archived Certificate Coverage', value: `${analytics.archived_certificate_issuance_pct ?? 0}%` }
      ]
    },
    {
      key: 'finance',
      title: 'Financial Signals',
      subtitle: 'Paid-event and sponsorship snapshot',
      badges: ['finance'],
      details: [
        { label: 'Paid Events', value: analytics.paid_events_count ?? 0 },
        { label: 'Listed Paid Revenue', value: formatCurrencyLabel(analytics.listed_paid_revenue_inr) },
        { label: 'Payment Proof Coverage', value: `${analytics.payment_proof_coverage_pct ?? 0}%` },
        { label: 'Sponsorship Progress', value: `${analytics.sponsorship_progress_pct ?? 0}%` },
        { label: 'Funding Gap', value: formatCurrencyLabel(analytics.sponsorship_gap_amount) }
      ]
    }
  ] : [];

  const directoryPanel = (
    <>
      <div>
        <h2 className="text-lg font-semibold">Club Directory</h2>
        <p className="text-sm text-slate-500">Filter the list, then open a club to switch the workspace context.</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
        <FormInput as="select" label="Status" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All</option>
          {clubStatusOptions.map((status) => (
            <option key={status} value={status}>{status}</option>
          ))}
        </FormInput>
        <FormInput label="Search clubs" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Name, category, description" />
      </div>

      {loadingClubs ? <p className="text-sm text-slate-500">Loading clubs...</p> : null}

      <div className="space-y-3">
        {filteredClubs.length ? filteredClubs.map((club) => (
          <button
            key={club.id}
            type="button"
            className={`w-full overflow-hidden rounded-2xl border text-left transition ${selectedClubId === club.id ? 'border-brand-400 bg-brand-50 ring-1 ring-brand-200 dark:border-brand-500 dark:bg-brand-950/20 dark:ring-brand-700' : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:hover:border-slate-500 dark:hover:bg-slate-900/60'}`}
            onClick={() => openClub(club.id)}
          >
            <div
              className="h-20 bg-gradient-to-br from-slate-900 via-slate-800 to-brand-900"
              style={club.banner_url ? { backgroundImage: `linear-gradient(rgba(15,23,42,0.5), rgba(15,23,42,0.72)), url(${club.banner_url})`, backgroundSize: 'cover', backgroundPosition: 'center' } : undefined}
            />
            <div className="space-y-3 p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  {club.logo_url ? (
                    <img src={club.logo_url} alt={`${club.name} logo`} className="-mt-9 h-14 w-14 rounded-2xl border border-white/60 bg-white object-cover shadow-lg" />
                  ) : (
                    <div className="-mt-9 grid h-14 w-14 place-items-center rounded-2xl border border-white/60 bg-white text-lg font-semibold text-slate-900 shadow-lg">
                      {club.name?.slice(0, 1) || 'C'}
                    </div>
                  )}
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{club.name}</p>
                    <p className="mt-1 text-xs text-slate-500">{club.category || 'General'}</p>
                  </div>
                </div>
                <span className="rounded-full border border-slate-300 px-2 py-0.5 text-[11px] uppercase tracking-wide text-slate-600 dark:border-slate-600 dark:text-slate-300">
                  {club.status}
                </span>
              </div>
              <div className="space-y-2">
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  {club.tagline || club.recruitment_headline || club.description || 'No public-facing club profile text yet.'}
                </p>
                {(club.achievement_highlights || []).length ? (
                  <div className="flex flex-wrap gap-2">
                    {club.achievement_highlights.slice(0, 2).map((highlight) => (
                      <span
                        key={`${club.id}-${highlight}`}
                        className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                      >
                        {highlight}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs text-slate-500 dark:text-slate-400">
                <span>Members: {club.member_count ?? 0}</span>
                <span>President: {club.president_name || '-'}</span>
                <span>Coordinator: {club.coordinator_name || '-'}</span>
                <span>Intake: {club.registration_open ? 'Open' : 'Closed'}</span>
              </div>
            </div>
          </button>
        )) : <EmptyState title="No clubs match" description="Adjust the filters to see more clubs." />}
      </div>
    </>
  );

  return (
    <div className="mx-auto max-w-7xl space-y-4 page-fade">
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold">Clubs Workspace</h1>
            <p className="text-sm text-slate-500">Select a club from the rail, then work inside that club’s focused workspace.</p>
          </div>
          <button className="btn-secondary" onClick={refreshClubs}>Refresh</button>
        </div>
        {clubsLoadError ? (
          <WorkspaceRecoveryPanel
            title="Club directory load failed"
            description={clubsLoadError}
            actions={[
              { key: 'retry-directory', label: 'Retry Directory', onClick: refreshClubs }
            ]}
            tone="rose"
          />
        ) : null}
        {clubDataLoadError ? (
          <WorkspaceRecoveryPanel
            title="Selected club workspace is partially unavailable"
            description={clubDataLoadError}
            actions={[
              { key: 'retry-selected', label: 'Retry Selected Club', onClick: reloadSelectedClubData },
              { key: 'refresh-directory', label: 'Refresh Directory', onClick: refreshClubs }
            ]}
            tone="amber"
          />
        ) : null}
      </Card>

      <div className="space-y-4 xl:hidden">
        <Card className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">Club Switcher</h2>
              <p className="text-sm text-slate-500">Keep the workspace focused on one club, then expand the directory only when you need to switch context.</p>
            </div>
            {selectedClub ? (
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300">
                Selected: {selectedClub.name}
              </div>
            ) : null}
          </div>
          <details className="group">
            <summary className="flex cursor-pointer list-none items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-800 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-100">
              Browse Clubs
              <span className="text-xs font-medium text-slate-500 group-open:hidden dark:text-slate-400">Expand</span>
              <span className="hidden text-xs font-medium text-slate-500 group-open:inline dark:text-slate-400">Collapse</span>
            </summary>
            <div className="mt-4 space-y-4">
              {directoryPanel}
            </div>
          </details>
        </Card>

        {isAdmin ? (
          <Card className="space-y-3">
            <details className="group">
              <summary className="flex cursor-pointer list-none items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-800 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-100">
                Create New Club
                <span className="text-xs font-medium text-slate-500 group-open:hidden dark:text-slate-400">Expand</span>
                <span className="hidden text-xs font-medium text-slate-500 group-open:inline dark:text-slate-400">Collapse</span>
              </summary>
              <form className="mt-4 space-y-3" onSubmit={submitCreateClub}>
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
                <FormInput label="Description" value={createForm.description} onChange={(e) => setCreateForm((prev) => ({ ...prev, description: e.target.value }))} />
                <FormInput label="Tagline" value={createForm.tagline} onChange={(e) => setCreateForm((prev) => ({ ...prev, tagline: e.target.value }))} placeholder="Short public-facing club hook" />
                <FormInput as="textarea" rows={3} label="Achievement Highlights" value={createForm.achievement_highlights} onChange={(e) => setCreateForm((prev) => ({ ...prev, achievement_highlights: e.target.value }))} placeholder="One highlight per line" />
                <FormInput label="Recruitment Headline" value={createForm.recruitment_headline} onChange={(e) => setCreateForm((prev) => ({ ...prev, recruitment_headline: e.target.value }))} placeholder="Why students should care right now" />
                <FormInput label="Recruitment CTA Label" value={createForm.recruitment_cta_label} onChange={(e) => setCreateForm((prev) => ({ ...prev, recruitment_cta_label: e.target.value }))} placeholder="Join the next open meeting" />
                <FormInput label="Public Contact URL" value={createForm.public_contact_url} onChange={(e) => setCreateForm((prev) => ({ ...prev, public_contact_url: e.target.value }))} placeholder="https://..." />
                <button className="btn-primary w-full" type="submit" disabled={createLoading}>{createLoading ? 'Creating...' : 'Create Club'}</button>
              </form>
            </details>
          </Card>
        ) : null}
      </div>

      <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="hidden space-y-4 xl:sticky xl:top-4 xl:block xl:self-start">
          <Card className="space-y-4">
            {directoryPanel}
          </Card>

          {isAdmin ? (
            <Card className="space-y-3">
              <details className="group">
                <summary className="flex cursor-pointer list-none items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-800 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-100">
                  Create New Club
                  <span className="text-xs font-medium text-slate-500 group-open:hidden dark:text-slate-400">Expand</span>
                  <span className="hidden text-xs font-medium text-slate-500 group-open:inline dark:text-slate-400">Collapse</span>
                </summary>
                <form className="mt-4 space-y-3" onSubmit={submitCreateClub}>
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
                  <FormInput label="Description" value={createForm.description} onChange={(e) => setCreateForm((prev) => ({ ...prev, description: e.target.value }))} />
                  <FormInput label="Tagline" value={createForm.tagline} onChange={(e) => setCreateForm((prev) => ({ ...prev, tagline: e.target.value }))} placeholder="Short public-facing club hook" />
                  <FormInput as="textarea" rows={3} label="Achievement Highlights" value={createForm.achievement_highlights} onChange={(e) => setCreateForm((prev) => ({ ...prev, achievement_highlights: e.target.value }))} placeholder="One highlight per line" />
                  <FormInput label="Recruitment Headline" value={createForm.recruitment_headline} onChange={(e) => setCreateForm((prev) => ({ ...prev, recruitment_headline: e.target.value }))} placeholder="Why students should care right now" />
                  <FormInput label="Recruitment CTA Label" value={createForm.recruitment_cta_label} onChange={(e) => setCreateForm((prev) => ({ ...prev, recruitment_cta_label: e.target.value }))} placeholder="Join the next open meeting" />
                  <FormInput label="Public Contact URL" value={createForm.public_contact_url} onChange={(e) => setCreateForm((prev) => ({ ...prev, public_contact_url: e.target.value }))} placeholder="https://..." />
                  <button className="btn-primary w-full" type="submit" disabled={createLoading}>{createLoading ? 'Creating...' : 'Create Club'}</button>
                </form>
              </details>
            </Card>
          ) : null}
        </aside>

        <div className="space-y-4">

      {selectedClub ? (
        <>
          <Card className="space-y-5 overflow-hidden">
            <div
              className="rounded-[1.75rem] bg-gradient-to-br from-slate-900 via-slate-800 to-brand-900 p-5 text-white shadow-[0_28px_70px_-42px_rgba(15,23,42,0.72)] sm:p-6"
              style={
                selectedClub.banner_url
                  ? {
                      backgroundImage: `linear-gradient(rgba(15,23,42,0.72), rgba(15,23,42,0.85)), url(${selectedClub.banner_url})`,
                      backgroundSize: 'cover',
                      backgroundPosition: 'center',
                    }
                  : undefined
              }
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.18em] text-slate-200/80">
                    <span>{selectedClub.category || 'General Club'}</span>
                    <span className="h-1 w-1 rounded-full bg-slate-200/60" />
                    <span>{selectedClub.status}</span>
                    <span className="h-1 w-1 rounded-full bg-slate-200/60" />
                    <span>{selectedClub.registration_open ? 'Recruitment Open' : 'Recruitment Closed'}</span>
                  </div>
                  <div className="flex flex-wrap items-start gap-4">
                    {selectedClub.logo_url ? (
                      <img src={selectedClub.logo_url} alt={`${selectedClub.name} logo`} className="h-20 w-20 rounded-3xl border border-white/20 bg-white/10 object-cover shadow-lg" />
                    ) : (
                      <div className="grid h-20 w-20 place-items-center rounded-3xl border border-white/20 bg-white/10 text-3xl font-semibold shadow-lg">
                        {selectedClub.name?.slice(0, 1) || 'C'}
                      </div>
                    )}
                    <div>
                      <h2 className="text-3xl font-semibold tracking-tight">{selectedClub.name}</h2>
                      {selectedClub.tagline ? (
                        <p className="mt-2 text-base font-medium text-brand-100">{selectedClub.tagline}</p>
                      ) : null}
                      <p className="mt-2 max-w-3xl text-sm text-slate-200/85">
                        {selectedClub.description || 'No club description is available yet. Use the workspace tabs to build the club experience around members, events, announcements, and analytics.'}
                      </p>
                    </div>
                  </div>
                  {selectedClubAchievements.length ? (
                    <div className="flex flex-wrap gap-2">
                      {selectedClubAchievements.map((highlight) => (
                        <span
                          key={`${selectedClub.id}-${highlight}`}
                          className="rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium text-slate-100 backdrop-blur-sm"
                        >
                          {highlight}
                        </span>
                      ))}
                    </div>
                  ) : null}
                  <div className="grid gap-2 text-sm text-slate-200/80 sm:flex sm:flex-wrap sm:gap-4">
                    <span>Coordinator: {selectedClub.coordinator_name || '-'}</span>
                    <span>President: {activePresidentMember?.student_name || selectedClub.president_name || '-'}</span>
                    <span>Membership: {selectedClub.membership_type || 'approval_required'}</span>
                    <span>Academic Year: {selectedClub.academic_year || '-'}</span>
                  </div>
                  {selectedClub.recruitment_headline || selectedClub.public_contact_url ? (
                    <div className="rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-sm text-slate-100 backdrop-blur-sm">
                      <p className="font-semibold text-white">
                        {selectedClub.recruitment_headline || 'Ready to bring in the next wave of members?'}
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-white/15 px-3 py-1 text-xs uppercase tracking-[0.16em] text-slate-100">
                          {selectedClub.registration_open ? 'Recruitment Live' : 'Recruitment Closed'}
                        </span>
                        {selectedClub.public_contact_url ? (
                          <a
                            className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-900 transition hover:bg-slate-100"
                            href={selectedClub.public_contact_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {selectedClubRecruitmentLabel}
                          </a>
                        ) : null}
                      </div>
                    </div>
                  ) : null}
                </div>

                <div className="grid w-full gap-2 sm:grid-cols-2 xl:flex xl:w-auto xl:flex-wrap">
                  {workspaceActionButtons.map((action) => (
                    <button
                      key={action.key}
                      type="button"
                      className={`${action.className} w-full justify-center ${action.className === 'btn-primary' ? '' : '!border-white/30 !bg-white/10 !text-white hover:!bg-white/15'} xl:w-auto`}
                      onClick={action.onClick}
                      disabled={action.disabled}
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              </div>

              {edgeCaseNotice ? (
                <div className="mt-5">
                  <WorkspaceNotice
                    title={edgeCaseNotice.title}
                    description={edgeCaseNotice.description}
                    tone={edgeCaseNotice.tone}
                    inverse
                  />
                </div>
              ) : null}

              <div className="mt-6 grid grid-cols-2 gap-3 xl:grid-cols-4">
                {selectedClubOverviewStats.map((item) => (
                  <div key={item.label} className="rounded-2xl border border-white/15 bg-white/8 px-4 py-3 backdrop-blur-sm">
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-200/70">{item.label}</p>
                    <p className="mt-2 text-2xl font-semibold text-white">{item.value}</p>
                    <p className="mt-1 text-xs text-slate-200/70">{item.detail}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-2 dark:border-slate-700 dark:bg-slate-900/60">
              <div className="flex min-w-max gap-2 overflow-x-auto">
                {tabs.map((tab) => (
                  <button
                    key={tab.key}
                    className={`whitespace-nowrap rounded-xl px-4 py-2 text-sm font-medium ${activeTab === tab.key ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900' : 'text-slate-600 hover:bg-white dark:text-slate-300 dark:hover:bg-slate-800'}`}
                    onClick={() => setActiveTab(tab.key)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>
          </Card>

          {activeTab === 'overview' ? (
            <div className="grid gap-4 2xl:grid-cols-[1.08fr_0.92fr]">
              <div className="space-y-4">
                {isEmptyClub ? (
                  <WorkspaceNotice
                    title="This club is still empty"
                    description="Use the selected-club actions to assign leadership, open recruitment, create the first event, and publish the first announcement so the workspace starts accumulating meaningful signals."
                    tone="emerald"
                  />
                ) : null}
                <Card className="space-y-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="text-lg font-semibold">Club Summary</h3>
                      <p className="text-sm text-slate-500">The selected-club workspace keeps the strongest facts and actions in one place.</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {selectedClubCanManage ? (
                        <button type="button" className="btn-secondary" onClick={openClubProfileEditor}>
                          Edit Club Profile
                        </button>
                      ) : null}
                      {!isStudent ? (
                        <Link className="btn-secondary" to={`/club-events?club_id=${selectedClub.id}`}>Open Event Inventory</Link>
                      ) : null}
                    </div>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <InfoPanel label="Coordinator" value={selectedClub.coordinator_name || 'Not assigned'} />
                    <InfoPanel label="President" value={activePresidentMember?.student_name || selectedClub.president_name || 'Not assigned'} />
                    <InfoPanel label="Membership Type" value={selectedClub.membership_type || 'approval_required'} />
                    <InfoPanel label="Recruitment" value={selectedClub.registration_open ? 'Open' : 'Closed'} />
                    <InfoPanel label="Academic Year" value={selectedClub.academic_year || '-'} />
                    <InfoPanel label="Club Status" value={selectedClub.status} />
                    <InfoPanel label="Tagline" value={selectedClub.tagline || 'Not set'} />
                    <InfoPanel label="Public Contact" value={selectedClub.public_contact_url || 'Not set'} />
                  </div>
                  {selectedClubAchievements.length ? (
                    <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-950/40">
                      <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Achievement Highlights</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {selectedClubAchievements.map((highlight) => (
                          <span
                            key={`${selectedClub.id}-summary-${highlight}`}
                            className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700 dark:bg-brand-950/30 dark:text-brand-300"
                          >
                            {highlight}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </Card>

                <Card className="space-y-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="text-lg font-semibold">Upcoming Events</h3>
                      <p className="text-sm text-slate-500">Stay inside the selected-club context while reviewing what is next.</p>
                    </div>
                    <button type="button" className="btn-secondary" onClick={() => setActiveTab('events')}>Open Event Center</button>
                  </div>
                  {overviewEvents.length ? (
                    <div className="space-y-3">
                      {overviewEvents.map((eventItem) => {
                        const availability = getEventRegistrationAvailability(eventItem);
                        const registration = eventRegistrationByEventId.get(eventItem.id);
                        return (
                          <div key={eventItem.id} className="rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div>
                                <p className="text-base font-semibold text-slate-900 dark:text-slate-100">{eventItem.title}</p>
                                <p className="mt-1 text-sm text-slate-500">{eventItem.event_type || 'event'} • {eventItem.event_date ? new Date(eventItem.event_date).toLocaleString() : 'Date TBD'}</p>
                              </div>
                              <span className="rounded-full border border-slate-300 px-2 py-1 text-xs uppercase tracking-wide text-slate-600 dark:border-slate-600 dark:text-slate-300">{eventItem.status}</span>
                            </div>
                            <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                              <span>{eventItem.visibility === 'members_only' ? 'Members only' : 'Public event'}</span>
                              <span>{eventItem.payment_required ? `Paid${eventItem.payment_amount ? ` (INR ${eventItem.payment_amount})` : ''}` : 'Free'}</span>
                              <span>{eventItem.registration_enabled ? 'Registration enabled' : 'Registration off'}</span>
                            </div>
                            <div className="mt-4 flex flex-wrap gap-2">
                              {registration ? (
                                <span className="rounded-full border border-emerald-300 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-300">
                                  Registration: {registration.status}
                                </span>
                              ) : null}
                              {isStudent ? (
                                <button
                                  type="button"
                                  className="btn-primary !px-3 !py-1.5 text-xs"
                                  disabled={availability.disabled}
                                  title={availability.title}
                                  onClick={() => openRegistrationModal(eventItem)}
                                >
                                  {availability.label}
                                </button>
                              ) : null}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <EmptyState
                      title={isDormantClub ? 'No active events while club is dormant' : 'No upcoming events'}
                      description={
                        isDormantClub
                          ? 'Re-activate the club and create a restart event when the club is ready to resume activity.'
                          : 'Use the Event Center to create the first event or reopen activity.'
                      }
                    />
                  )}
                </Card>
              </div>

              <div className="space-y-4">
                <Card className="space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold">Workspace Signals</h3>
                    <p className="text-sm text-slate-500">Quick health checks for the selected club.</p>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <SignalCard title="Pending Applications" value={pendingApplicationsCount} detail={selectedClubCanManage ? 'Review from Members tab' : 'Visible to club leads'} />
                    <SignalCard title="Waitlisted Members" value={waitlistedApplicationsCount} detail="Students queued for intake" />
                    <SignalCard title="Active Members" value={activeMembersCount} detail="Current active roster" />
                    <SignalCard title="Upcoming Events" value={upcomingEvents.length} detail="Scheduled or planned ahead" />
                  </div>
                </Card>

                <Card className="space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold">Next Best Actions</h3>
                    <p className="text-sm text-slate-500">The workspace keeps the next operational moves close to the selected club.</p>
                  </div>
                  <div className="space-y-3">
                    {selectedClubCanManage ? (
                      <ActionCallout
                        title={pendingApplicationsCount || waitlistedApplicationsCount ? 'Review membership pipeline' : 'Membership pipeline is clear'}
                        description={
                          pendingApplicationsCount || waitlistedApplicationsCount
                            ? `${pendingApplicationsCount} pending and ${waitlistedApplicationsCount} waitlisted application${pendingApplicationsCount + waitlistedApplicationsCount === 1 ? '' : 's'} are in the queue.`
                            : 'No pending or waitlisted membership requests right now.'
                        }
                        actionLabel="Open Members"
                        onAction={() => setActiveTab('members')}
                      />
                    ) : null}
                    <ActionCallout
                      title={upcomingEvents.length ? 'Stay on top of the event timeline' : 'Plan the next club event'}
                      description={upcomingEvents.length ? `${upcomingEvents[0].title} is the next highlighted event in this club.` : 'No future event is visible in the selected club yet.'}
                      actionLabel="Open Event Center"
                      onAction={() => setActiveTab('events')}
                    />
                    <ActionCallout
                      title="Keep club communication active"
                      description="Announcements, reminders, and scoped updates now live inside this workspace."
                      actionLabel="Open Announcements"
                      onAction={() => setActiveTab('announcements')}
                    />
                  </div>
                </Card>
              </div>
            </div>
          ) : null}

      {selectedClub && activeTab === 'members' ? (
        <div className="space-y-4">
          {isDormantClub || isLargeClub ? (
            <WorkspaceNotice
              title={isDormantClub ? 'Dormant member operations' : 'High-volume roster operations'}
              description={
                isDormantClub
                  ? 'Treat the current roster as recovery context. Review inactive or removed members carefully before reopening intake, and use announcements to restart the club deliberately.'
                  : 'Use filters, saved queue views, pagination, and bulk actions to manage the intake pipeline without reading the whole roster and queue at once.'
              }
              tone={isDormantClub ? 'amber' : 'brand'}
            />
          ) : null}
          <Card className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Members</h2>
                <p className="text-sm text-slate-500">
                  {selectedClubCanManage
                    ? 'Manage roles and membership state for this club.'
                    : 'View active member roster and membership history.'}
                </p>
              </div>
              {selectedClubCanManage ? (
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300">
                  Current president: {activePresidentMember?.student_name || selectedClub.president_name || 'Not assigned'}
                </div>
              ) : null}
            </div>
            <div className="md:hidden">
              <MobileCollectionState
                items={members}
                emptyTitle="No members yet"
                emptyDescription="Member cards will appear here once the selected club has an active roster."
                renderItem={(member) => (
                  <MobileInfoCard
                    key={member.id}
                    title={member.student_name || member.student_email || 'Club member'}
                    subtitle={member.student_email || member.public_id || 'Member record'}
                    badges={[member.role || 'member', member.status || 'active']}
                    details={[
                      { label: 'Short ID', value: member.public_id || '-' },
                      { label: 'Joined', value: member.joined_at ? new Date(member.joined_at).toLocaleString() : '-' }
                    ]}
                    actions={memberRowActions}
                    row={member}
                  />
                )}
              />
            </div>
            <div className="hidden md:block">
              <Table columns={memberColumns} data={members} rowActions={memberRowActions} />
            </div>
          </Card>

          {selectedClubCanManage ? (
            <Card className="space-y-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">Membership Applications</h2>
                  <p className="text-sm text-slate-500">
                    Search the intake queue, review applications in bulk, and nudge applicants when the queue is waiting on them.
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300">
                  {selectedApplicationIds.length
                    ? `${selectedApplicationIds.length} application${selectedApplicationIds.length === 1 ? '' : 's'} selected`
                    : `${filteredApplications.length} visible in queue`}
                </div>
              </div>
              <div className="grid gap-3 md:grid-cols-[minmax(0,1fr),220px]">
                <FormInput
                  label="Search queue"
                  value={applicationSearch}
                  onChange={(e) => setApplicationSearch(e.target.value)}
                  placeholder="Student name, email, short ID"
                />
                <FormInput
                  as="select"
                  label="Queue status"
                  value={applicationStatusFilter}
                  onChange={(e) => setApplicationStatusFilter(e.target.value)}
                >
                  <option value="all">All queue states</option>
                  <option value="pending">Pending</option>
                  <option value="waitlisted">Waitlisted</option>
                </FormInput>
              </div>
              <SavedFilterBar
                filters={savedApplicationFilters}
                onApply={applyApplicationFilter}
                onDelete={deleteApplicationFilter}
                onSaveCurrent={saveCurrentApplicationFilter}
                emptyLabel="No saved membership queue views yet."
              />
              <div className="flex flex-wrap gap-2">
                <QueuePriorityPills
                  stale={applicationPriorityCounts.stale}
                  aging={applicationPriorityCounts.aging}
                  fresh={applicationPriorityCounts.fresh}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!canBulkApproveApplications}
                  onClick={() => runBulkApplicationAction('approved')}
                >
                  Bulk Approve
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!canBulkPendingApplications}
                  onClick={() => runBulkApplicationAction('pending')}
                >
                  Move To Pending
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!canBulkWaitlistApplications}
                  onClick={() => runBulkApplicationAction('waitlisted')}
                >
                  Move To Waitlist
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!canBulkRejectApplications}
                  onClick={() => runBulkApplicationAction('rejected')}
                >
                  Bulk Reject
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!selectedApplicationIds.length}
                  onClick={() => sendApplicationReminder('selected')}
                >
                  Remind Selected
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!filteredApplications.length}
                  onClick={() => sendApplicationReminder('filtered')}
                >
                  Remind Visible Queue
                </button>
              </div>
              <div className="md:hidden">
                <MobileCollectionState
                  items={pagedApplications}
                  emptyTitle="No membership applications"
                  emptyDescription="Application and waitlist cards will appear here when students request membership."
                  renderItem={(application) => (
                    <MobileInfoCard
                      key={application.id}
                      title={application.student_name || application.student_email || 'Applicant'}
                      subtitle={application.student_email || application.public_id || 'Application record'}
                      badges={[application.status || 'pending', getQueueAgeMeta(application.applied_at, application.status).priorityLabel]}
                      details={[
                        { label: 'Short ID', value: application.public_id || '-' },
                        { label: 'Owner', value: application.queue_owner_label || 'Unassigned' },
                        { label: 'Queue Age', value: getQueueAgeMeta(application.applied_at, application.status).ageLabel },
                        { label: 'Last Touched', value: formatQueueTouch(application.last_touched_at, application.last_touched_by_label) },
                        { label: 'Note', value: summarizeQueueNote(application.coordinator_note) },
                        { label: 'Applied', value: application.applied_at ? new Date(application.applied_at).toLocaleString() : '-' }
                      ]}
                      actions={applicationRowActions}
                      selectable
                      selected={selectedApplicationIds.includes(application.id)}
                      onToggleSelected={() => toggleSelectedId(setSelectedApplicationIds, application.id)}
                      row={application}
                    />
                  )}
                />
                <QueuePagination
                  page={applicationPage}
                  pageSize={applicationPageSize}
                  totalItems={filteredApplications.length}
                  onPageChange={setApplicationPage}
                  onPageSizeChange={setApplicationPageSize}
                />
              </div>
              <div className="hidden md:block">
                <Table
                  columns={applicationColumns}
                  data={pagedApplications}
                  rowActions={applicationRowActions}
                  selectable
                  selectedRowIds={selectedApplicationIds}
                  onToggleRow={(row) => toggleSelectedId(setSelectedApplicationIds, row.id)}
                  onToggleAllRows={(rows) => toggleAllSelectedIds(setSelectedApplicationIds, rows, selectedApplicationIds)}
                  selectionLabel={(row) => `Select application ${row.student_name || row.student_email || row.id}`}
                />
                <div className="mt-3">
                  <QueuePagination
                    page={applicationPage}
                    pageSize={applicationPageSize}
                    totalItems={filteredApplications.length}
                    onPageChange={setApplicationPage}
                    onPageSizeChange={setApplicationPageSize}
                  />
                </div>
              </div>
              <QueueSnapshotHistory
                title="Membership Queue Snapshot History"
                snapshots={applicationSnapshots}
                emptyLabel="Queue snapshots will appear here after this club's queue changes."
              />
            </Card>
          ) : null}
        </div>
      ) : null}

      {selectedClub && activeTab === 'events' ? (
        <div className="space-y-4">
          {isDormantClub || isLargeClub ? (
            <WorkspaceNotice
              title={isDormantClub ? 'Dormant event operations' : 'High-volume event operations'}
              description={
                isDormantClub
                  ? 'Event health and queue pressure may no longer reflect current club reality. Use this area to plan the restart event first, then rebuild activity and trend lines from there.'
                  : 'This club has enough event volume to rely on trends, exports, and per-event history drilldowns. Open enrollment history from the event table when you need full lifecycle detail.'
              }
              tone={isDormantClub ? 'amber' : 'brand'}
            />
          ) : null}
          <Card className="space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Event Center</h2>
                <p className="text-sm text-slate-500">
                  Manage scheduling, registration windows, and enrollment decisions without leaving the selected-club workspace.
                </p>
              </div>
              {!isStudent ? (
                <Link className="btn-secondary" to={`/club-events?club_id=${selectedClub.id}`}>Open Event Inventory</Link>
              ) : null}
            </div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <SignalCard title="Total Events" value={events.length} detail="Visible for this club" />
              <SignalCard title="Upcoming Events" value={upcomingEvents.length} detail="Open or planned ahead" />
              <SignalCard title="Pending Registrations" value={enrollments.filter((row) => row.status === 'pending').length} detail={enrollmentModalEvent ? `Inside ${enrollmentModalEvent.title}` : 'Open an event to review'} />
              <SignalCard title="Waitlisted" value={enrollments.filter((row) => row.status === 'waitlisted').length} detail={enrollmentModalEvent ? `Queue for ${enrollmentModalEvent.title}` : 'Open an event to review'} />
              <SignalCard title="Archived Events" value={archivedEventsCount} detail="Older club history ready for lookup" />
            </div>
          </Card>

          {selectedClubCanLeadEvents ? (
            <Card className="space-y-3">
              <h2 className="text-lg font-semibold">Create Event</h2>
              <form className="grid gap-3 lg:grid-cols-2" onSubmit={submitCreateEvent}>
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
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Events</h2>
                <p className="text-sm text-slate-500">
                  {selectedClubCanLeadEvents
                    ? 'Open, close, archive, and inspect enrollments directly from this table.'
                    : 'Review upcoming and historical events for the selected club.'}
                </p>
              </div>
              {selectedClubCanLeadEvents ? (
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300">
                  Enrollment review stays attached to each event.
                </div>
              ) : null}
            </div>
            <div className="grid gap-3 md:grid-cols-[minmax(0,1fr),220px,140px]">
              <FormInput
                label="Search events"
                value={eventSearch}
                onChange={(e) => setEventSearch(e.target.value)}
                placeholder="Title, type, short ID"
              />
              <FormInput
                as="select"
                label="Archive View"
                value={eventStatusFilter}
                onChange={(e) => setEventStatusFilter(e.target.value)}
              >
                <option value="all">All events</option>
                <option value="live">Live pipeline</option>
                <option value="completed">Completed only</option>
                <option value="archived">Archived only</option>
              </FormInput>
              <FormInput
                as="select"
                label="Page Size"
                value={eventPageSize}
                onChange={(e) => setEventPageSize(Number(e.target.value))}
              >
                {[6, 8, 12, 20].map((size) => (
                  <option key={size} value={size}>{size}/page</option>
                ))}
              </FormInput>
            </div>
            {eventStatusFilter === 'archived' ? (
              <WorkspaceNotice
                title="Archive navigation is active"
                description={`Showing ${filteredEvents.length} archived event${filteredEvents.length === 1 ? '' : 's'} out of ${archivedEventsCount}. Use search to jump by title, type, or short ID, then page through older records without mixing them into the live pipeline.`}
                tone="brand"
              />
            ) : isLargeClub && archivedEventsCount ? (
              <WorkspaceNotice
                title="Large-club archive shortcut"
                description={`This club already has ${archivedEventsCount} archived event${archivedEventsCount === 1 ? '' : 's'}. Switch Archive View to "Archived only" when you need older event history instead of scanning the active pipeline.`}
                tone="brand"
              />
            ) : null}
            <div className="md:hidden">
              <MobileCollectionState
                items={pagedEvents}
                emptyTitle={eventStatusFilter === 'archived' ? 'No archived events' : 'No events yet'}
                emptyDescription={
                  eventStatusFilter === 'archived'
                    ? 'Archived event cards will appear here when this club starts closing out older activity.'
                    : 'Event cards will appear here once this club starts scheduling activity.'
                }
                renderItem={(eventItem) => {
                  const registration = eventRegistrationByEventId.get(eventItem.id);
                  const availability = getEventRegistrationAvailability(eventItem);
                  const mobileEventActions = [
                    ...(isStudent && !registration
                      ? [{
                          key: `register-${eventItem.id}`,
                          label: availability.label,
                          disabled: availability.disabled,
                          title: availability.title,
                          onClick: () => openRegistrationModal(eventItem)
                        }]
                      : []),
                    ...eventRowActions
                  ];

                  return (
                    <MobileInfoCard
                      key={eventItem.id}
                      title={eventItem.title || 'Club event'}
                      subtitle={eventItem.event_type || 'event'}
                      badges={[
                        eventItem.status || 'open',
                        eventItem.visibility === 'members_only' ? 'members only' : 'public',
                        registration ? `registration: ${registration.status}` : (eventItem.registration_enabled ? 'registration on' : 'registration off')
                      ]}
                      details={[
                        { label: 'Short ID', value: eventItem.public_id || '-' },
                        { label: 'Date', value: eventItem.event_date ? new Date(eventItem.event_date).toLocaleString() : 'Date TBD' },
                        { label: 'Registration Window', value: eventItem.registration_end ? `Ends ${new Date(eventItem.registration_end).toLocaleString()}` : 'No deadline' },
                        { label: 'Capacity', value: eventItem.capacity ?? '-' },
                        { label: 'Payment', value: eventItem.payment_required ? `INR ${eventItem.payment_amount ?? 0}` : 'Free' },
                        { label: 'Result', value: eventItem.result_summary || '-' }
                      ]}
                      actions={mobileEventActions}
                      row={eventItem}
                    />
                  );
                }}
              />
              <QueuePagination
                page={eventPage}
                pageSize={eventPageSize}
                totalItems={filteredEvents.length}
                onPageChange={setEventPage}
                onPageSizeChange={setEventPageSize}
              />
            </div>
            <div className="hidden md:block">
              <Table columns={eventColumns} data={pagedEvents} rowActions={eventRowActions} />
              <div className="mt-3">
                <QueuePagination
                  page={eventPage}
                  pageSize={eventPageSize}
                  totalItems={filteredEvents.length}
                  onPageChange={setEventPage}
                  onPageSizeChange={setEventPageSize}
                />
              </div>
            </div>
          </Card>
        </div>
      ) : null}

      {selectedClub && activeTab === 'announcements' ? (
        <div className="space-y-4">
          <ClubAnnouncementsPanel
            selectedClub={selectedClub}
            canPublish={Boolean(selectedClubCanLeadEvents)}
          />
          <Card className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold">Communication Hub</h3>
                <p className="text-sm text-slate-500">
                  Cross-module announcements and the broader communication feed still live in the shared communication workspace.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Link className="btn-secondary" to="/communication/announcements">Open All Announcements</Link>
                <Link className="btn-secondary" to="/communication/feed">Open Feed</Link>
              </div>
            </div>
          </Card>
        </div>
      ) : null}

      {selectedClub && activeTab === 'analytics' ? (
        <Card className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">Club Analytics</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Download coordinator-ready reporting for event health, attendance follow-through, and certificate issuance.
              </p>
            </div>
            {analytics ? (
              <div className="flex flex-wrap gap-2">
                {selectedClubCanManage ? (
                  <button type="button" className="btn-secondary" onClick={openFinancialProfileEditor}>
                    Manage Funding Profile
                  </button>
                ) : null}
                <button type="button" className="btn-secondary" onClick={() => downloadClubAnalyticsReport('event_performance')}>
                  Export Event Performance CSV
                </button>
                <button type="button" className="btn-secondary" onClick={() => downloadClubAnalyticsReport('attendance_certificate')}>
                  Export Attendance CSV
                </button>
              </div>
            ) : null}
          </div>
          {!analytics ? (
            <p className="text-sm text-slate-500">Analytics not available for this role or club.</p>
          ) : (
            <>
              {isEmptyClub || isDormantClub || isLargeClub ? (
                <WorkspaceNotice
                  title={
                    isEmptyClub
                      ? 'Analytics are still warming up'
                      : isDormantClub
                        ? 'Read dormant-club analytics carefully'
                        : 'Large-club analytics guidance'
                  }
                  description={
                    isEmptyClub
                      ? 'This club does not have enough operational history yet for trend lines or delivery metrics to mean much. Use the workspace to build the first roster and event cycle.'
                      : isDormantClub
                        ? 'Dormant clubs often carry stale historical signals. Use trends and drilldowns as context, but pair them with a deliberate restart plan before reading them as current momentum.'
                        : 'For high-volume clubs, start with trend summaries and exports, then move into per-event drilldowns only for the events that still need intervention.'
                  }
                  tone={isEmptyClub ? 'emerald' : isDormantClub ? 'amber' : 'brand'}
                />
              ) : null}
              {clubPerformanceMonitor && (isLargeClub || clubPerformanceMonitor.status !== 'healthy') ? (
                <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-950/40">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Workspace Performance Monitor</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        Session-level load timings and recent club API traces for high-volume club operations.
                      </p>
                    </div>
                    <span className={`rounded-full border px-3 py-1 text-xs uppercase tracking-wide ${performanceStatusBadgeClass(clubPerformanceMonitor.status)}`}>
                      {clubPerformanceMonitor.statusLabel}
                    </span>
                  </div>
                  <div className="mt-4 grid gap-3 lg:grid-cols-3">
                    <SignalCard
                      title="Selected Club Load"
                      value={formatDurationLabel(clubPerformanceMonitor.selectedClubLoad?.durationMs)}
                      detail={`Members ${members.length} • Events ${events.length} • Updated ${formatRelativeTimestamp(clubPerformanceMonitor.selectedClubLoad?.loadedAt)}`}
                    />
                    <SignalCard
                      title="Club API P95"
                      value={formatDurationLabel(clubPerformanceMonitor.p95DurationMs)}
                      detail={`${clubPerformanceMonitor.slowTraceCount} slow trace${clubPerformanceMonitor.slowTraceCount === 1 ? '' : 's'} • ${clubPerformanceMonitor.errorTraceCount} trace error${clubPerformanceMonitor.errorTraceCount === 1 ? '' : 's'}`}
                    />
                    <SignalCard
                      title="Dataset Weight"
                      value={clubPerformanceMonitor.datasetWeight}
                      detail={`${clubPerformanceMonitor.archivedEvents} archived events • Avg API ${formatDurationLabel(clubPerformanceMonitor.averageDurationMs)}`}
                    />
                  </div>
                  {clubPerformanceMonitor.slowestTrace ? (
                    <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-200">
                      <p className="font-semibold">Slowest recent club request</p>
                      <p className="mt-1">
                        {clubPerformanceMonitor.slowestTrace.endpointLabel} took {formatDurationLabel(clubPerformanceMonitor.slowestTrace.durationMs)} with status {clubPerformanceMonitor.slowestTrace.status || '-'}.
                      </p>
                    </div>
                  ) : null}
                  <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr),320px]">
                    <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-700">
                      <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
                        <thead className="bg-slate-50 dark:bg-slate-900/40">
                          <tr>
                            {['Endpoint', 'Status', 'Duration', 'Time'].map((label) => (
                              <th key={label} className="px-4 py-3 text-left font-medium text-slate-500 dark:text-slate-300">{label}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                          {clubPerformanceMonitor.recentTraces.length ? (
                            clubPerformanceMonitor.recentTraces.map((trace) => (
                              <tr key={`${trace.requestId || trace.traceId || trace.at}-${trace.url}`}>
                                <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">{trace.endpointLabel}</td>
                                <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{trace.status || '-'}</td>
                                <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{formatDurationLabel(trace.durationMs)}</td>
                                <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{formatRelativeTimestamp(trace.at)}</td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td colSpan={4} className="px-4 py-4 text-sm text-slate-500 dark:text-slate-400">
                                Club API traces will appear here after the workspace loads club data.
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/60">
                      <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Large-club recommendations</p>
                      <div className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                        {clubPerformanceMonitor.recommendations.map((recommendation) => (
                          <p key={recommendation} className="rounded-xl border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950/40">
                            {recommendation}
                          </p>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}
              <div className="md:hidden">
                <MobileCollectionState
                  items={mobileAnalyticsCards}
                  emptyTitle="Analytics unavailable"
                  emptyDescription="Analytics cards will appear here when metrics are available for the selected club."
                  renderItem={(item) => (
                    <MobileInfoCard
                      key={item.key}
                      title={item.title}
                      subtitle={item.subtitle}
                      badges={item.badges}
                      details={item.details}
                      row={item}
                    />
                  )}
                />
              </div>
              <div className="hidden md:grid gap-3 md:grid-cols-3">
                <Stat label="Total Members" value={analytics.total_members} />
                <Stat label="Active Members" value={analytics.active_members} />
                <Stat label="Inactive Members" value={analytics.inactive_members} />
                <Stat label="Membership Growth (30d)" value={analytics.membership_growth_30d} />
                <Stat label="Retention (90d)" value={`${analytics.member_retention_pct_90d ?? 0}%`} />
                <Stat label="Churn (90d)" value={`${analytics.member_churn_rate_pct_90d ?? 0}%`} />
                <Stat label="Join To Event %" value={`${analytics.member_event_conversion_pct ?? 0}%`} />
                <Stat label="Join To Attend %" value={`${analytics.member_attendance_conversion_pct ?? 0}%`} />
                <Stat label="Recently Engaged (90d)" value={analytics.recently_engaged_active_members_90d} />
                <Stat label="At-Risk Active Members" value={analytics.at_risk_active_members_90d} />
                <Stat label="Total Events" value={analytics.total_events} />
                <Stat label="Upcoming Events" value={analytics.upcoming_events} />
                <Stat label="Completed Events" value={analytics.completed_events} />
                <Stat label="Event Fill %" value={analytics.average_attendance_pct} />
                <Stat label="Pending Applications" value={analytics.pending_applications} />
                <Stat label="Waitlisted Applications" value={analytics.waitlisted_applications} />
                <Stat label="Pending Event Reviews" value={analytics.pending_event_registrations} />
                <Stat label="Waitlisted Registrations" value={analytics.waitlisted_event_registrations} />
                <Stat label="Events At Capacity" value={analytics.events_at_capacity} />
                <Stat label="Attendance Marked %" value={`${analytics.attendance_marked_pct ?? 0}%`} />
                <Stat label="No-Show Rate" value={`${analytics.no_show_rate_pct ?? 0}%`} />
                <Stat label="Certificates Issued" value={analytics.certificates_issued} />
                <Stat label="Certificate Coverage" value={`${analytics.certificate_issuance_pct ?? 0}%`} />
                <Stat label="Events With Waitlist" value={analytics.waitlist_pressure_events} />
                <Stat label="Certificate Events" value={analytics.certificate_enabled_events} />
                <Stat label="Repeat Attention Events" value={analytics.repeat_attention_events} />
                <Stat label="Archived Events" value={analytics.archived_events} />
                <Stat label="Archived Seats" value={analytics.archived_confirmed_registrations} />
                <Stat label="Archived Attendance %" value={`${analytics.archived_attendance_marked_pct ?? 0}%`} />
                <Stat label="Archived Certificate Coverage" value={`${analytics.archived_certificate_issuance_pct ?? 0}%`} />
                <Stat label="Paid Events" value={analytics.paid_events_count} />
                <Stat label="Listed Paid Revenue" value={formatCurrencyLabel(analytics.listed_paid_revenue_inr)} />
                <Stat label="Payment Proof Coverage" value={`${analytics.payment_proof_coverage_pct ?? 0}%`} />
                <Stat label="Sponsorship Progress" value={`${analytics.sponsorship_progress_pct ?? 0}%`} />
              </div>
              <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/40">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Engagement Intelligence</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      Track whether members stay, convert into real participation, and start falling quiet before the roster looks healthy on paper but empty in practice.
                    </p>
                  </div>
                </div>
                <div className="mt-4 grid gap-3 xl:grid-cols-5">
                  <SignalCard
                    title="Retention (90d)"
                    value={`${analytics.member_retention_pct_90d ?? 0}%`}
                    detail={`${analytics.retained_members_90d ?? 0} retained members against ${analytics.departed_members_90d ?? 0} recent departures`}
                  />
                  <SignalCard
                    title="Churn (90d)"
                    value={`${analytics.member_churn_rate_pct_90d ?? 0}%`}
                    detail={`${analytics.departed_members_90d ?? 0} members left or went inactive in the last 90 days`}
                  />
                  <SignalCard
                    title="Join To Event Conversion"
                    value={`${analytics.member_event_conversion_pct ?? 0}%`}
                    detail={`${analytics.members_with_event_participation ?? 0} members have at least one confirmed club event registration`}
                  />
                  <SignalCard
                    title="Join To Attendance Conversion"
                    value={`${analytics.member_attendance_conversion_pct ?? 0}%`}
                    detail={`${analytics.members_with_present_attendance ?? 0} members have a present attendance record in club history`}
                  />
                  <SignalCard
                    title="At-Risk Active Members"
                    value={analytics.at_risk_active_members_90d ?? 0}
                    detail={`${analytics.recently_engaged_active_members_90d ?? 0} active members showed recent event activity in the last 90 days`}
                  />
                </div>
                <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr),320px]">
                  <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-950/40">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Why this matters</p>
                    <div className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                      <p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-900/60">
                        `Retention (90d)` compares longer-standing active members with recent departures so you can see whether the roster is holding or leaking.
                      </p>
                      <p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-900/60">
                        `Join To Event Conversion` answers whether members ever make it from joining the club into a real event seat.
                      </p>
                      <p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-900/60">
                        `At-Risk Active Members` flags mature active members with no recent club-event engagement so outreach can start before they disappear into churn.
                      </p>
                    </div>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-950/40">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Engagement Readout</p>
                    <div className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                      <p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-900/60">
                        Recently engaged active members: {analytics.recently_engaged_active_members_90d ?? 0}
                      </p>
                      <p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-900/60">
                        Members with event participation history: {analytics.members_with_event_participation ?? 0}
                      </p>
                      <p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-900/60">
                        Members with present attendance history: {analytics.members_with_present_attendance ?? 0}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/40">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Financial & Sponsorship Insight</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      Read paid-event revenue signals honestly from listed event pricing and payment-proof coverage, then compare them with the club sponsorship target.
                    </p>
                  </div>
                </div>
                <div className="mt-4 grid gap-3 xl:grid-cols-4">
                  <SignalCard
                    title="Paid Event Revenue"
                    value={formatCurrencyLabel(analytics.listed_paid_revenue_inr)}
                    detail={`${analytics.paid_confirmed_registrations ?? 0} confirmed paid registration${analytics.paid_confirmed_registrations === 1 ? '' : 's'}`}
                  />
                  <SignalCard
                    title="Payment Proof Coverage"
                    value={`${analytics.payment_proof_coverage_pct ?? 0}%`}
                    detail={`${analytics.payment_proof_submitted_count ?? 0} proof submission${analytics.payment_proof_submitted_count === 1 ? '' : 's'} across paid seats`}
                  />
                  <SignalCard
                    title="Sponsorship Progress"
                    value={`${analytics.sponsorship_progress_pct ?? 0}%`}
                    detail={`${formatCurrencyLabel(analytics.sponsorship_committed_amount)} committed of ${formatCurrencyLabel(analytics.sponsorship_target_amount)} target`}
                  />
                  <SignalCard
                    title="Funding Gap"
                    value={formatCurrencyLabel(analytics.sponsorship_gap_amount)}
                    detail={`${analytics.free_events_count ?? 0} free event${analytics.free_events_count === 1 ? '' : 's'} and ${analytics.paid_events_count ?? 0} paid event${analytics.paid_events_count === 1 ? '' : 's'} in club history`}
                  />
                </div>
                <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr),320px]">
                  <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-950/40">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Funding Notes</p>
                    <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                      {selectedClub?.sponsorship_notes
                        ? selectedClub.sponsorship_notes
                        : 'No sponsorship notes yet. Use the funding profile to record the current target, committed amount, and sponsor context.'}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-950/40">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Finance Reality Check</p>
                    <div className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                      <p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-900/60">
                        `Listed Paid Revenue` is estimated from confirmed paid registrations multiplied by each event&apos;s listed amount. It is not bank-verified cash received.
                      </p>
                      <p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-900/60">
                        `Payment Proof Coverage` shows how many confirmed paid seats already include a transaction reference or uploaded receipt.
                      </p>
                      <p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-900/60">
                        `Sponsorship Progress` compares club-managed committed sponsorship against the club target stored in the funding profile.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/40">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Cross-Event Trends</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      Compare recent club events to spot repeated demand, attendance, and certificate follow-through patterns.
                    </p>
                  </div>
                </div>
                <div className="mt-4 grid gap-3 xl:grid-cols-3">
                  {(analytics.trend_summaries || []).map((trend) => (
                    <div key={trend.key} className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-950/40">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{trend.label}</p>
                        <span className={`rounded-full border px-2 py-0.5 text-[11px] uppercase tracking-wide ${trendDirectionBadgeClass(trend.direction)}`}>
                          {trend.direction}
                        </span>
                      </div>
                      <p className="mt-2 text-xl font-semibold text-slate-900 dark:text-slate-100">
                        {trend.current_value ?? 0}%
                      </p>
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{trend.detail}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-4 rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-950/40">
                  <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-700">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Recent Event Trend Line</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      Latest six events with fill, no-show, waitlist pressure, and certificate follow-through.
                    </p>
                  </div>
                  {analytics.recent_event_trends?.length ? (
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
                        <thead className="bg-slate-50 dark:bg-slate-900/40">
                          <tr>
                            {['Event', 'Date', 'Fill', 'No-Show', 'Waitlist', 'Certificates', 'Health'].map((label) => (
                              <th key={label} className="px-4 py-3 text-left font-medium text-slate-500 dark:text-slate-300">{label}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                          {analytics.recent_event_trends.map((point) => (
                            <tr key={point.event_id}>
                              <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">{point.title}</td>
                              <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                                {point.event_date ? new Date(point.event_date).toLocaleString() : '-'}
                              </td>
                              <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{point.fill_pct}%</td>
                              <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{point.no_show_rate_pct}%</td>
                              <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{point.waitlisted_registrations}</td>
                              <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{point.certificate_issuance_pct}%</td>
                              <td className="px-4 py-3">
                                <span className={`rounded-full border px-2 py-1 text-xs uppercase tracking-wide ${eventHealthBadgeClass(point.health_summary)}`}>
                                  {point.health_summary}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="px-4 py-4 text-sm text-slate-500 dark:text-slate-400">
                      Trend lines will appear here as the club accumulates multiple events.
                    </div>
                  )}
                </div>
              </div>
              <div className="mt-4 rounded-2xl border border-slate-200 dark:border-slate-700">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3 dark:border-slate-700">
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Top Event Performance</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      Queue pressure, attendance quality, and certificate follow-through for the club events that need the most coordinator attention.
                    </p>
                  </div>
                </div>
                {analytics.event_performance?.length ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
                      <thead className="bg-slate-50 dark:bg-slate-900/40">
                        <tr>
                          {['Event', 'Health', 'Fill', 'Queue', 'Attendance', 'Certificates'].map((label) => (
                            <th key={label} className="px-4 py-3 text-left font-medium text-slate-500 dark:text-slate-300">{label}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                        {analytics.event_performance.map((eventInsight) => (
                          <tr key={eventInsight.event_id}>
                            <td className="px-4 py-3">
                              <div className="font-medium text-slate-900 dark:text-slate-100">{eventInsight.title}</div>
                              <div className="text-xs text-slate-500 dark:text-slate-400">
                                {eventInsight.status} • {eventInsight.capacity} seats
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <span className={`rounded-full border px-2 py-1 text-xs uppercase tracking-wide ${eventHealthBadgeClass(eventInsight.health_summary)}`}>
                                {eventInsight.health_summary}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                              {eventInsight.fill_pct}% ({eventInsight.confirmed_registrations}/{eventInsight.capacity})
                            </td>
                            <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                              {eventInsight.pending_registrations} pending • {eventInsight.waitlisted_registrations} waitlisted
                            </td>
                            <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                              {eventInsight.attendance_marked_pct}% marked • {eventInsight.no_show_rate_pct}% no-show
                            </td>
                            <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                              {eventInsight.certificate_enabled
                                ? `${eventInsight.certificate_issuance_pct}% (${eventInsight.certificate_issued_count}/${eventInsight.certificate_eligible_count})`
                                : 'No certificates'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="px-4 py-4 text-sm text-slate-500 dark:text-slate-400">
                    Event performance insights will appear here as registrations, attendance, and certificates accumulate.
                  </div>
                )}
              </div>
              <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/40">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Archival Analytics</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      Read completed club history across archived seasons, older event cohorts, and long-range attendance follow-through.
                    </p>
                  </div>
                </div>
                <div className="mt-4 grid gap-3 xl:grid-cols-4">
                  <SignalCard
                    title="Archived Events"
                    value={analytics.archived_events ?? 0}
                    detail="Closed-out events available for long-range comparison"
                  />
                  <SignalCard
                    title="Archived Seats"
                    value={analytics.archived_confirmed_registrations ?? 0}
                    detail="Confirmed registrations across archived club history"
                  />
                  <SignalCard
                    title="Archived Attendance"
                    value={`${analytics.archived_attendance_marked_pct ?? 0}%`}
                    detail={`${analytics.archived_no_show_rate_pct ?? 0}% no-show across archived attendance marks`}
                  />
                  <SignalCard
                    title="Archived Certificates"
                    value={analytics.archived_certificates_issued ?? 0}
                    detail={`${analytics.archived_certificate_issuance_pct ?? 0}% issuance across archived eligible attendees`}
                  />
                </div>
                <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1.15fr),minmax(0,0.85fr)]">
                  <div className="rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-950/40">
                    <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-700">
                      <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Season-over-Season Archive Summary</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        Quarterly archive performance to compare older club cycles without reopening each event one by one.
                      </p>
                    </div>
                    {analytics.archive_season_summaries?.length ? (
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
                          <thead className="bg-slate-50 dark:bg-slate-900/40">
                            <tr>
                              {['Season', 'Archived Events', 'Seats', 'Attendance', 'No-Show', 'Certificates'].map((label) => (
                                <th key={label} className="px-4 py-3 text-left font-medium text-slate-500 dark:text-slate-300">{label}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                            {analytics.archive_season_summaries.map((season) => (
                              <tr key={season.season_label}>
                                <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">{season.season_label}</td>
                                <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{season.archived_events}</td>
                                <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{season.confirmed_registrations}</td>
                                <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{season.attendance_marked_pct}%</td>
                                <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{season.no_show_rate_pct}%</td>
                                <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                                  {season.certificate_issuance_pct}% ({season.certificates_issued})
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="px-4 py-4 text-sm text-slate-500 dark:text-slate-400">
                        Archived seasonal comparisons will appear here after the club starts cycling older events into archive status.
                      </div>
                    )}
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-950/40">
                    <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-700">
                      <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Archived Event Cohorts</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        Split older events by age so coordinators can separate recent archive cleanup from legacy club history.
                      </p>
                    </div>
                    {analytics.archive_event_cohorts?.length ? (
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
                          <thead className="bg-slate-50 dark:bg-slate-900/40">
                            <tr>
                              {['Cohort', 'Events', 'Seats', 'Attendance', 'No-Show', 'Latest Event'].map((label) => (
                                <th key={label} className="px-4 py-3 text-left font-medium text-slate-500 dark:text-slate-300">{label}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                            {analytics.archive_event_cohorts.map((cohort) => (
                              <tr key={cohort.cohort_key}>
                                <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">{cohort.cohort_label}</td>
                                <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{cohort.archived_events}</td>
                                <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{cohort.confirmed_registrations}</td>
                                <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{cohort.attendance_marked_pct}%</td>
                                <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{cohort.no_show_rate_pct}%</td>
                                <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                                  {cohort.latest_event_date ? new Date(cohort.latest_event_date).toLocaleDateString() : '-'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="px-4 py-4 text-sm text-slate-500 dark:text-slate-400">
                        Archive cohorts will appear here as the club builds enough older history to compare.
                      </div>
                    )}
                  </div>
                </div>
                <div className="mt-4 rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-950/40">
                  <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-700">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Long-Range Archive History</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      Monthly archive checkpoints for attendance and certificate follow-through across older club operations.
                    </p>
                  </div>
                  {analytics.archival_history_points?.length ? (
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
                        <thead className="bg-slate-50 dark:bg-slate-900/40">
                          <tr>
                            {['Period', 'Archived Events', 'Seats', 'Attendance', 'No-Show', 'Certificates'].map((label) => (
                              <th key={label} className="px-4 py-3 text-left font-medium text-slate-500 dark:text-slate-300">{label}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                          {analytics.archival_history_points.map((point) => (
                            <tr key={`${point.period_label}-${point.period_start || 'undated'}`}>
                              <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">{point.period_label}</td>
                              <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{point.archived_events}</td>
                              <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{point.confirmed_registrations}</td>
                              <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{point.attendance_marked_pct}%</td>
                              <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{point.no_show_rate_pct}%</td>
                              <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{point.certificate_issuance_pct}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="px-4 py-4 text-sm text-slate-500 dark:text-slate-400">
                      Monthly archive history will appear here once the club has older archived event cycles to compare.
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </Card>
      ) : null}
        </>
        ) : (
          <EmptyState title="Select a club" description="Choose a club from the directory to open its focused workspace." />
        )}

        </div>
      </div>

      <Modal
        open={profileModalOpen}
        title={selectedClub ? `Club Profile: ${selectedClub.name}` : 'Club Profile'}
        onClose={closeClubProfileEditor}
      >
        <form className="space-y-4" onSubmit={submitClubProfile}>
          <FormInput
            label="Tagline"
            value={profileForm.tagline}
            onChange={(e) => setProfileForm((prev) => ({ ...prev, tagline: e.target.value }))}
            placeholder="A short one-line reason this club matters"
          />
          <FormInput
            as="textarea"
            rows={4}
            label="Achievement Highlights"
            value={profileForm.achievement_highlights}
            onChange={(e) => setProfileForm((prev) => ({ ...prev, achievement_highlights: e.target.value }))}
            placeholder="One highlight per line. Example: Built a campus robotics showcase"
          />
          <div className="grid gap-3 md:grid-cols-2">
            <FormInput
              label="Recruitment Headline"
              value={profileForm.recruitment_headline}
              onChange={(e) => setProfileForm((prev) => ({ ...prev, recruitment_headline: e.target.value }))}
              placeholder="Why students should join now"
            />
            <FormInput
              label="Recruitment CTA Label"
              value={profileForm.recruitment_cta_label}
              onChange={(e) => setProfileForm((prev) => ({ ...prev, recruitment_cta_label: e.target.value }))}
              placeholder="Join our next orientation"
            />
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <FormInput
              label="Public Contact URL"
              value={profileForm.public_contact_url}
              onChange={(e) => setProfileForm((prev) => ({ ...prev, public_contact_url: e.target.value }))}
              placeholder="https://..."
            />
            <FormInput
              label="Logo URL"
              value={profileForm.logo_url}
              onChange={(e) => setProfileForm((prev) => ({ ...prev, logo_url: e.target.value }))}
              placeholder="https://..."
            />
          </div>
          <FormInput
            label="Banner URL"
            value={profileForm.banner_url}
            onChange={(e) => setProfileForm((prev) => ({ ...prev, banner_url: e.target.value }))}
            placeholder="https://..."
          />
          <div className="flex justify-end gap-2">
            <button type="button" className="btn-secondary" onClick={closeClubProfileEditor} disabled={profileSaving}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={profileSaving}>
              {profileSaving ? 'Saving...' : 'Save Club Profile'}
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        open={financialProfileModalOpen}
        title={selectedClub ? `Funding Profile: ${selectedClub.name}` : 'Funding Profile'}
        onClose={closeFinancialProfileEditor}
      >
        <form className="space-y-4" onSubmit={submitFinancialProfile}>
          <div className="grid gap-3 md:grid-cols-2">
            <FormInput
              label="Sponsorship Target (INR)"
              type="number"
              min={0}
              step="0.01"
              value={financialProfileForm.sponsorship_target_amount}
              onChange={(e) => setFinancialProfileForm((prev) => ({ ...prev, sponsorship_target_amount: e.target.value }))}
              placeholder="50000"
            />
            <FormInput
              label="Committed Sponsorship (INR)"
              type="number"
              min={0}
              step="0.01"
              value={financialProfileForm.sponsorship_committed_amount}
              onChange={(e) => setFinancialProfileForm((prev) => ({ ...prev, sponsorship_committed_amount: e.target.value }))}
              placeholder="15000"
            />
          </div>
          <FormInput
            as="textarea"
            label="Funding Notes"
            rows={4}
            value={financialProfileForm.sponsorship_notes}
            onChange={(e) => setFinancialProfileForm((prev) => ({ ...prev, sponsorship_notes: e.target.value }))}
            placeholder="Sponsors in conversation, promised support, budget context, or funding constraints."
          />
          <div className="flex justify-end gap-2">
            <button type="button" className="btn-secondary" onClick={closeFinancialProfileEditor} disabled={financialProfileSaving}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={financialProfileSaving}>
              {financialProfileSaving ? 'Saving...' : 'Save Funding Profile'}
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        open={registrationModalOpen}
        title={registrationEvent ? `Register: ${registrationEvent.title}` : 'Event Registration'}
        onClose={closeRegistrationExperience}
      >
        <EventRegistrationForm
          showEventSelector={false}
          selectedEvent={registrationEvent}
          form={registrationForm}
          onFormChange={setRegistrationForm}
          paymentReceiptFile={paymentReceiptFile}
          onPaymentReceiptFileChange={setPaymentReceiptFile}
          onSubmit={submitEventRegistrationForm}
          onCancel={closeRegistrationExperience}
          submitting={registrationSubmitting}
          submitLabel="Submitting..."
          submitIdleLabel="Submit Registration"
        />
      </Modal>

      <Modal
        open={Boolean(memberEditor)}
        title={memberEditor ? `Manage Member: ${memberEditor.student_name || memberEditor.student_email}` : 'Manage Member'}
        onClose={closeMemberEditor}
      >
        {memberEditor ? (
          <form className="space-y-4" onSubmit={submitMemberEditor}>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-200">
              <p className="font-medium">{memberEditor.student_name || memberEditor.student_email}</p>
              <p className="mt-1">Current role: {memberEditor.role}</p>
              <p className="mt-1">Current status: {memberEditor.status}</p>
              {activePresidentMember && activePresidentMember.id !== memberEditor.id ? (
                <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">
                  Promote to president only after demoting {activePresidentMember.student_name || activePresidentMember.student_email}.
                </p>
              ) : null}
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <FormInput
                as="select"
                label="Member Role"
                value={memberEditorForm.role}
                onChange={(e) => setMemberEditorForm((prev) => ({ ...prev, role: e.target.value }))}
              >
                <option value="member">Member</option>
                <option value="core_member">Core Member</option>
                <option value="vice_president">Vice President</option>
                <option value="president" disabled={Boolean(activePresidentMember && activePresidentMember.id !== memberEditor.id)}>
                  President
                </option>
              </FormInput>
              <FormInput
                as="select"
                label="Membership Status"
                value={memberEditorForm.status}
                onChange={(e) => setMemberEditorForm((prev) => ({ ...prev, status: e.target.value }))}
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="removed">Removed</option>
              </FormInput>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="btn-secondary" onClick={closeMemberEditor}>
                Cancel
              </button>
              <button type="submit" className="btn-primary" disabled={memberEditorSaving}>
                {memberEditorSaving ? 'Saving...' : 'Save Member Changes'}
              </button>
            </div>
          </form>
        ) : null}
      </Modal>

      <Modal
        open={Boolean(applicationContextTarget)}
        title={applicationContextTarget ? `Application Context: ${applicationContextTarget.student_name || applicationContextTarget.student_email}` : 'Application Context'}
        onClose={closeApplicationContextEditor}
      >
        {applicationContextTarget ? (
          <form className="space-y-4" onSubmit={submitApplicationContext}>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-200">
              <p className="font-medium">{applicationContextTarget.student_name || applicationContextTarget.student_email || 'Application'}</p>
              <p className="mt-1">Current status: {applicationContextTarget.status}</p>
              <p className="mt-1">Last touched: {formatQueueTouch(applicationContextTarget.last_touched_at, applicationContextTarget.last_touched_by_label)}</p>
            </div>

            <FormInput
              as="select"
              label="Queue Owner"
              value={applicationContextForm.queue_owner_user_id}
              onChange={(e) => setApplicationContextForm((prev) => ({ ...prev, queue_owner_user_id: e.target.value }))}
            >
              {queueOwnerOptions.map((option) => (
                <option key={option.value || 'unassigned'} value={option.value}>{option.label}</option>
              ))}
            </FormInput>

            <FormInput
              as="textarea"
              label="Coordinator Note"
              rows={5}
              value={applicationContextForm.coordinator_note}
              onChange={(e) => setApplicationContextForm((prev) => ({ ...prev, coordinator_note: e.target.value }))}
              placeholder="Capture handoff context, blockers, or the next follow-up needed."
            />

            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="btn-secondary" onClick={closeApplicationContextEditor}>
                Cancel
              </button>
              <button type="submit" className="btn-primary" disabled={applicationContextSaving}>
                {applicationContextSaving ? 'Saving...' : 'Save Context'}
              </button>
            </div>
          </form>
        ) : null}
      </Modal>

      <Modal
        open={Boolean(enrollmentContextTarget)}
        title={enrollmentContextTarget ? `Enrollment Context: ${enrollmentContextTarget.student_name || enrollmentContextTarget.student_email}` : 'Enrollment Context'}
        onClose={closeEnrollmentContextEditor}
      >
        {enrollmentContextTarget ? (
          <form className="space-y-4" onSubmit={submitEnrollmentContext}>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-200">
              <p className="font-medium">{enrollmentContextTarget.student_name || enrollmentContextTarget.student_email || 'Enrollment'}</p>
              <p className="mt-1">Current status: {enrollmentContextTarget.status}</p>
              <p className="mt-1">Last touched: {formatQueueTouch(enrollmentContextTarget.last_touched_at, enrollmentContextTarget.last_touched_by_label)}</p>
            </div>

            <FormInput
              as="select"
              label="Queue Owner"
              value={enrollmentContextForm.queue_owner_user_id}
              onChange={(e) => setEnrollmentContextForm((prev) => ({ ...prev, queue_owner_user_id: e.target.value }))}
            >
              {queueOwnerOptions.map((option) => (
                <option key={option.value || 'unassigned'} value={option.value}>{option.label}</option>
              ))}
            </FormInput>

            <FormInput
              as="textarea"
              label="Coordinator Note"
              rows={5}
              value={enrollmentContextForm.coordinator_note}
              onChange={(e) => setEnrollmentContextForm((prev) => ({ ...prev, coordinator_note: e.target.value }))}
              placeholder="Capture attendance follow-up, certificate blockers, or owner handoff context."
            />

            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="btn-secondary" onClick={closeEnrollmentContextEditor}>
                Cancel
              </button>
              <button type="submit" className="btn-primary" disabled={enrollmentContextSaving}>
                {enrollmentContextSaving ? 'Saving...' : 'Save Context'}
              </button>
            </div>
          </form>
        ) : null}
      </Modal>

      <Modal
        open={Boolean(enrollmentModalEvent)}
        title={enrollmentModalEvent ? `Event Enrollments: ${enrollmentModalEvent.title}` : 'Event Enrollments'}
        onClose={() => {
          setEnrollmentModalEvent(null);
          setEnrollments([]);
          setEventHistory(null);
          setLoadingEnrollments(false);
        }}
      >
        <div className="space-y-3">
          {loadingEnrollments ? <p className="text-sm text-slate-500">Loading enrollments...</p> : null}
          {enrollmentModalEvent ? (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-200">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold">{enrollmentModalEvent.title}</p>
                  <p className="mt-1 text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    {enrollmentModalEvent.event_type || 'event'} • {enrollmentModalEvent.status}
                  </p>
                </div>
                <span className="rounded-full border border-slate-300 px-2 py-1 text-xs uppercase tracking-wide text-slate-600 dark:border-slate-600 dark:text-slate-300">
                  {enrollments.length} registration{enrollments.length === 1 ? '' : 's'}
                </span>
              </div>
            </div>
          ) : null}
          {eventHistory ? (
            <EventHistoryTimeline history={eventHistory} />
          ) : null}
          {enrollmentModalEvent ? (
            <>
              <div className="grid gap-3 md:grid-cols-[minmax(0,1fr),220px]">
                <FormInput
                  label="Search registrations"
                  value={enrollmentSearch}
                  onChange={(e) => setEnrollmentSearch(e.target.value)}
                  placeholder="Student name, email, short ID"
                />
                <FormInput
                  as="select"
                  label="Queue status"
                  value={enrollmentStatusFilter}
                  onChange={(e) => setEnrollmentStatusFilter(e.target.value)}
                >
                  <option value="all">All queue states</option>
                  <option value="pending">Pending</option>
                  <option value="waitlisted">Waitlisted</option>
                  <option value="approved">Approved</option>
                  <option value="registered">Registered</option>
                </FormInput>
              </div>
              <SavedFilterBar
                filters={savedEnrollmentFilters}
                onApply={applyEnrollmentFilter}
                onDelete={deleteEnrollmentFilter}
                onSaveCurrent={saveCurrentEnrollmentFilter}
                emptyLabel="No saved enrollment queue views yet."
              />
              <div className="flex flex-wrap gap-2">
                <QueuePriorityPills
                  stale={enrollmentPriorityCounts.stale}
                  aging={enrollmentPriorityCounts.aging}
                  fresh={enrollmentPriorityCounts.fresh}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!canPromoteEnrollments}
                  onClick={() => runBulkEnrollmentAction({ status: enrollmentModalEvent.approval_required ? 'pending' : 'registered' })}
                >
                  Promote Selected
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!canApproveEnrollments}
                  onClick={() => runBulkEnrollmentAction({ status: 'approved' })}
                >
                  Bulk Approve
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!canWaitlistEnrollments}
                  onClick={() => runBulkEnrollmentAction({ status: 'waitlisted' })}
                >
                  Move To Waitlist
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!canRejectEnrollments}
                  onClick={() => runBulkEnrollmentAction({ status: 'rejected' })}
                >
                  Bulk Reject
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!selectedEnrollmentIds.length}
                  onClick={() => sendEnrollmentReminder('selected')}
                >
                  Remind Selected
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!filteredEnrollments.length}
                  onClick={() => sendEnrollmentReminder('filtered')}
                >
                  Remind Visible Queue
                </button>
              </div>
            </>
          ) : null}
          <div className="md:hidden">
            <MobileCollectionState
              items={pagedEnrollments}
              emptyTitle="No event enrollments"
              emptyDescription="Enrollment cards will appear here after students register for this event."
              renderItem={(enrollment) => (
                <MobileInfoCard
                  key={enrollment.id}
                  title={enrollment.student_name || enrollment.student_user_id || 'Registrant'}
                  subtitle={enrollment.student_email || enrollment.email || 'Enrollment record'}
                  badges={[
                    enrollment.status || 'pending',
                    getQueueAgeMeta(enrollment.created_at, enrollment.status).priorityLabel,
                    enrollment.attendance_status || 'attendance pending'
                  ]}
                  details={[
                    { label: 'Queue Age', value: getQueueAgeMeta(enrollment.created_at, enrollment.status).ageLabel },
                    { label: 'Owner', value: enrollment.queue_owner_label || 'Unassigned' },
                    { label: 'Last Touched', value: formatQueueTouch(enrollment.last_touched_at, enrollment.last_touched_by_label) },
                    { label: 'Certificate', value: enrollment.certificate_issued ? 'Issued' : 'Not issued' },
                    { label: 'Note', value: summarizeQueueNote(enrollment.coordinator_note) },
                    { label: 'Registered', value: enrollment.created_at ? new Date(enrollment.created_at).toLocaleString() : '-' }
                  ]}
                  actions={enrollmentRowActions}
                  selectable
                  selected={selectedEnrollmentIds.includes(enrollment.id)}
                  onToggleSelected={() => toggleSelectedId(setSelectedEnrollmentIds, enrollment.id)}
                  row={enrollment}
                />
              )}
            />
            <QueuePagination
              page={enrollmentPage}
              pageSize={enrollmentPageSize}
              totalItems={filteredEnrollments.length}
              onPageChange={setEnrollmentPage}
              onPageSizeChange={setEnrollmentPageSize}
            />
          </div>
          <div className="hidden md:block">
            <Table
              columns={enrollmentColumns}
              data={pagedEnrollments}
              rowActions={enrollmentRowActions}
              selectable
              selectedRowIds={selectedEnrollmentIds}
              onToggleRow={(row) => toggleSelectedId(setSelectedEnrollmentIds, row.id)}
              onToggleAllRows={(rows) => toggleAllSelectedIds(setSelectedEnrollmentIds, rows, selectedEnrollmentIds)}
              selectionLabel={(row) => `Select registration ${row.student_name || row.student_email || row.id}`}
            />
            <div className="mt-3">
              <QueuePagination
                page={enrollmentPage}
                pageSize={enrollmentPageSize}
                totalItems={filteredEnrollments.length}
                onPageChange={setEnrollmentPage}
                onPageSizeChange={setEnrollmentPageSize}
              />
            </div>
            <QueueSnapshotHistory
              title="Enrollment Queue Snapshot History"
              snapshots={enrollmentSnapshots}
              emptyLabel="Queue snapshots will appear here after this event queue changes."
            />
          </div>
        </div>
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

function InfoPanel({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-slate-100">{value}</p>
    </div>
  );
}

function SignalCard({ title, value, detail }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/60">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-100">{value}</p>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{detail}</p>
    </div>
  );
}

function WorkspaceNotice({ title, description, tone = 'slate', inverse = false }) {
  const toneClass = inverse
    ? (
      tone === 'amber'
        ? 'border-amber-200/30 bg-amber-400/10 text-amber-50'
        : tone === 'emerald'
          ? 'border-emerald-200/30 bg-emerald-400/10 text-emerald-50'
          : tone === 'brand'
            ? 'border-sky-200/30 bg-sky-400/10 text-sky-50'
            : 'border-white/20 bg-white/10 text-white'
    )
    : (
      tone === 'amber'
        ? 'border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100'
        : tone === 'emerald'
          ? 'border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-100'
          : tone === 'brand'
            ? 'border-sky-200 bg-sky-50 text-sky-900 dark:border-sky-800 dark:bg-sky-950/30 dark:text-sky-100'
            : 'border-slate-200 bg-slate-50 text-slate-900 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-100'
    );

  return (
    <div className={`rounded-2xl border px-4 py-3 ${toneClass}`}>
      <p className="text-sm font-semibold">{title}</p>
      <p className={`mt-1 text-sm ${inverse ? 'opacity-90' : 'opacity-80'}`}>{description}</p>
    </div>
  );
}

function WorkspaceRecoveryPanel({ title, description, actions = [], tone = 'slate' }) {
  const toneClass = (
    tone === 'rose'
      ? 'border-rose-200 bg-rose-50 text-rose-950 dark:border-rose-800 dark:bg-rose-950/30 dark:text-rose-100'
      : tone === 'amber'
        ? 'border-amber-200 bg-amber-50 text-amber-950 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100'
        : 'border-slate-200 bg-slate-50 text-slate-950 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-100'
  );

  return (
    <div className={`rounded-2xl border p-4 ${toneClass}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-3xl">
          <p className="text-sm font-semibold">{title}</p>
          <p className="mt-1 text-sm opacity-80">{description}</p>
        </div>
        {actions.length ? (
          <div className="flex flex-wrap gap-2">
            {actions.map((action, index) => (
              <button
                key={action.key || action.label}
                type="button"
                className={index === 0 ? 'btn-primary' : 'btn-secondary'}
                onClick={action.onClick}
              >
                {action.label}
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function formatTrendSummaryValue(trend) {
  if (!trend) return 'No trend yet';
  return `${trend.direction} (${trend.current_value ?? 0}%)`;
}

function ActionCallout({ title, description, actionLabel, onAction }) {
  return (
    <div className="rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</p>
          <p className="mt-1 text-sm text-slate-500">{description}</p>
        </div>
        <button type="button" className="btn-secondary" onClick={onAction}>{actionLabel}</button>
      </div>
    </div>
  );
}

function MobileCollectionState({ items, emptyTitle, emptyDescription, renderItem }) {
  if (!items.length) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <div className="space-y-3">
      {items.map((item) => renderItem(item))}
    </div>
  );
}

function getQueueAgeMeta(value, status) {
  if (!value || !['pending', 'waitlisted'].includes(status)) {
    return {
      ageLabel: 'Resolved',
      priorityLabel: 'normal',
      priorityTone: 'slate'
    };
  }

  const createdAt = new Date(value);
  const ageMs = Date.now() - createdAt.getTime();
  const days = Math.max(0, Math.floor(ageMs / (1000 * 60 * 60 * 24)));

  if (days >= 7) {
    return {
      ageLabel: `${days}d old`,
      priorityLabel: 'stale',
      priorityTone: 'rose'
    };
  }
  if (days >= 3) {
    return {
      ageLabel: `${days}d old`,
      priorityLabel: 'aging',
      priorityTone: 'amber'
    };
  }
  return {
    ageLabel: days === 0 ? 'today' : `${days}d old`,
    priorityLabel: 'fresh',
    priorityTone: 'emerald'
  };
}

function buildSavedFilterName(status, search) {
  const statusLabel = status === 'all' ? 'All queue' : `${status} queue`;
  if (!search) return statusLabel;
  const compact = search.trim().slice(0, 18);
  return `${statusLabel} • ${compact}`;
}

function summarizeQueueNote(note) {
  const cleaned = (note || '').trim();
  if (!cleaned) return 'No note';
  return cleaned.length > 72 ? `${cleaned.slice(0, 69)}...` : cleaned;
}

function formatQueueTouch(timestamp, label) {
  if (!timestamp) {
    return label ? `By ${label}` : 'Not touched yet';
  }
  const dateLabel = new Date(timestamp).toLocaleString();
  return label ? `${dateLabel} by ${label}` : dateLabel;
}

function formatRelativeTimestamp(value) {
  if (!value) return 'Not recorded';
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return 'Not recorded';
  const diffMs = Date.now() - timestamp;
  const diffMinutes = Math.max(0, Math.round(diffMs / (1000 * 60)));
  if (diffMinutes < 1) return 'just now';
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.round(diffHours / 24);
  return `${diffDays}d ago`;
}

function formatDurationLabel(value) {
  if (value == null || value === '') return '-';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '-';
  if (numeric >= 1000) {
    return `${(numeric / 1000).toFixed(1)}s`;
  }
  return `${Math.round(numeric)}ms`;
}

function formatCurrencyLabel(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric === 0) return 'INR 0';
  return `INR ${numeric.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
}

function buildQueueOwnerOptions({ currentUser, isAdmin, selectedClub, teachers = [] }) {
  const options = [];
  const seen = new Set();

  function addOption(value, label) {
    const key = value || '__unassigned__';
    if (seen.has(key)) return;
    seen.add(key);
    options.push({ value: value || '', label });
  }

  addOption('', 'Unassigned');
  if (currentUser?.id) {
    addOption(currentUser.id, 'Me');
  }
  if (selectedClub?.coordinator_user_id) {
    addOption(
      selectedClub.coordinator_user_id,
      selectedClub.coordinator_name ? `${selectedClub.coordinator_name} (Coordinator)` : 'Club Coordinator'
    );
  }
  if (selectedClub?.president_user_id) {
    addOption(
      selectedClub.president_user_id,
      selectedClub.president_name ? `${selectedClub.president_name} (President)` : 'Club President'
    );
  }
  if (isAdmin) {
    teachers.forEach((teacher) => {
      addOption(teacher.id, teacher.full_name ? `${teacher.full_name} (Teacher)` : teacher.email || teacher.id);
    });
  }
  return options;
}

function toneToBadgeClass(tone) {
  if (tone === 'rose') {
    return 'border-rose-300 text-rose-700 dark:border-rose-700 dark:text-rose-300';
  }
  if (tone === 'amber') {
    return 'border-amber-300 text-amber-700 dark:border-amber-700 dark:text-amber-300';
  }
  if (tone === 'emerald') {
    return 'border-emerald-300 text-emerald-700 dark:border-emerald-700 dark:text-emerald-300';
  }
  return 'border-slate-300 text-slate-600 dark:border-slate-600 dark:text-slate-300';
}

function performanceStatusBadgeClass(status) {
  if (status === 'critical') {
    return 'border-rose-300 bg-rose-50 text-rose-700 dark:border-rose-700 dark:bg-rose-950/30 dark:text-rose-300';
  }
  if (status === 'watch') {
    return 'border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-300';
  }
  return 'border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300';
}

function trendDirectionBadgeClass(direction) {
  if (direction === 'improving') {
    return 'border-emerald-300 text-emerald-700 dark:border-emerald-700 dark:text-emerald-300';
  }
  if (direction === 'declining') {
    return 'border-rose-300 text-rose-700 dark:border-rose-700 dark:text-rose-300';
  }
  return toneToBadgeClass('slate');
}

function eventHealthBadgeClass(summary) {
  if (summary === 'waitlist pressure') {
    return toneToBadgeClass('rose');
  }
  if (summary === 'attendance risk') {
    return toneToBadgeClass('amber');
  }
  if (summary === 'certificate follow-up') {
    return 'border-blue-300 text-blue-700 dark:border-blue-700 dark:text-blue-300';
  }
  if (summary === 'high demand') {
    return toneToBadgeClass('emerald');
  }
  return toneToBadgeClass('slate');
}

function formatSnapshotDelta(current, previous) {
  if (!previous) {
    return 'first snapshot';
  }
  const delta = current.total - previous.total;
  if (delta === 0) {
    return 'no queue change';
  }
  return `${delta > 0 ? '+' : ''}${delta} vs previous`;
}

function QueuePriorityPills({ stale, aging, fresh }) {
  return (
    <>
      <span className={`rounded-full border px-2 py-1 text-xs uppercase tracking-wide ${toneToBadgeClass('rose')}`}>
        {stale} stale
      </span>
      <span className={`rounded-full border px-2 py-1 text-xs uppercase tracking-wide ${toneToBadgeClass('amber')}`}>
        {aging} aging
      </span>
      <span className={`rounded-full border px-2 py-1 text-xs uppercase tracking-wide ${toneToBadgeClass('emerald')}`}>
        {fresh} fresh
      </span>
    </>
  );
}

function QueuePagination({ page, pageSize, totalItems, onPageChange, onPageSizeChange }) {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900/60">
      <div className="text-slate-600 dark:text-slate-300">
        Showing {totalItems === 0 ? 0 : (page - 1) * pageSize + 1}-{Math.min(page * pageSize, totalItems)} of {totalItems}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <select
          className="input h-9 w-20"
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
        >
          {[6, 8, 12, 20].map((size) => (
            <option key={size} value={size}>{size}/page</option>
          ))}
        </select>
        <button
          type="button"
          className="btn-secondary"
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page <= 1}
        >
          Previous
        </button>
        <span className="px-2 text-slate-500 dark:text-slate-400">{page} / {totalPages}</span>
        <button
          type="button"
          className="btn-secondary"
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={page >= totalPages}
        >
          Next
        </button>
      </div>
    </div>
  );
}

function SavedFilterBar({
  filters,
  onApply,
  onDelete,
  onSaveCurrent,
  emptyLabel,
  label = 'Shared Views',
  helper = 'Shared with staff managing this queue.'
}) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">{helper}</p>
        </div>
        <button type="button" className="btn-secondary" onClick={onSaveCurrent}>Save Current View</button>
      </div>
      {filters.length ? (
        <div className="flex flex-wrap gap-2">
          {filters.map((filter) => (
            <div key={filter.id} className="flex items-center gap-1 rounded-full border border-slate-300 bg-white px-2 py-1 text-xs dark:border-slate-600 dark:bg-slate-950/40">
              <button type="button" className="text-slate-700 dark:text-slate-200" onClick={() => onApply(filter)}>
                {filter.name}
              </button>
              <button
                type="button"
                className="text-slate-400 hover:text-rose-600 dark:hover:text-rose-300"
                onClick={() => onDelete(filter.id)}
                aria-label={`Delete saved filter ${filter.name}`}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate-500">{emptyLabel}</p>
      )}
    </div>
  );
}

function EventHistoryTimeline({ history }) {
  const entries = Array.isArray(history?.timeline) ? history.timeline.slice(0, 10) : [];
  const summaryCards = [
    { label: 'Confirmed', value: history?.confirmed_registrations ?? 0 },
    { label: 'Pending', value: history?.pending_registrations ?? 0 },
    { label: 'Waitlisted', value: history?.waitlisted_registrations ?? 0 },
    { label: 'Attendance Marked', value: history?.attendance_marked_count ?? 0 },
    { label: 'Present', value: history?.present_count ?? 0 },
    { label: 'Certificates', value: history?.certificates_issued ?? 0 }
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-950/40">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Event History Drilldown</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Lifecycle view for registration movement, attendance updates, certificates, and queue pressure.
          </p>
        </div>
        <div className="text-right text-xs text-slate-500 dark:text-slate-400">
          <p>{history?.event_type || 'event'} • {history?.status || 'draft'}</p>
          <p>{history?.event_date ? new Date(history.event_date).toLocaleString() : 'No event date set'}</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        {summaryCards.map((item) => (
          <div key={item.label} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-900/60">
            <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">{item.label}</p>
            <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">{item.value}</p>
          </div>
        ))}
      </div>

      {entries.length ? (
        <div className="mt-4 space-y-3">
          {entries.map((entry) => (
            <div key={entry.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-900/60">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{entry.title}</p>
                    <span className="rounded-full border border-slate-300 px-2 py-0.5 text-[11px] uppercase tracking-wide text-slate-600 dark:border-slate-600 dark:text-slate-300">
                      {entry.entry_type}
                    </span>
                    {entry.status_label ? (
                      <span className="rounded-full border border-slate-300 px-2 py-0.5 text-[11px] uppercase tracking-wide text-slate-600 dark:border-slate-600 dark:text-slate-300">
                        {entry.status_label}
                      </span>
                    ) : null}
                    {entry.attendance_status ? (
                      <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] uppercase tracking-wide text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">
                        {entry.attendance_status}
                      </span>
                    ) : null}
                    {entry.certificate_issued ? (
                      <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] uppercase tracking-wide text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
                        Certificate issued
                      </span>
                    ) : null}
                  </div>
                  {entry.detail ? (
                    <p className="text-sm text-slate-600 dark:text-slate-300">{entry.detail}</p>
                  ) : null}
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {entry.occurred_at ? new Date(entry.occurred_at).toLocaleString() : 'Unknown time'}
                </p>
              </div>
              <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500 dark:text-slate-400">
                {entry.actor_label ? <span>By {entry.actor_label}</span> : null}
                {entry.subject_label ? <span>For {entry.subject_label}</span> : null}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-4 text-sm text-slate-500">No drilldown entries yet for this event.</p>
      )}
    </div>
  );
}

function QueueSnapshotHistory({ title, snapshots, emptyLabel }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/60">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Shared queue history for staff managing this queue.
          </p>
        </div>
      </div>
      {snapshots.length ? (
        <div className="mt-4 space-y-3">
          {snapshots.slice(0, 4).map((snapshot, index) => (
            <div key={`${snapshot.captured_at || snapshot.capturedAt}-${index}`} className="rounded-xl border border-slate-200 bg-white p-3 text-sm dark:border-slate-700 dark:bg-slate-950/40">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium text-slate-800 dark:text-slate-100">
                  {new Date(snapshot.captured_at || snapshot.capturedAt).toLocaleString()}
                </span>
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  {formatSnapshotDelta(snapshot, snapshots[index + 1])}
                </span>
              </div>
              <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-600 dark:text-slate-300">
                <span>Total: {snapshot.total}</span>
                <span>Pending: {snapshot.pending}</span>
                <span>Waitlisted: {snapshot.waitlisted}</span>
                <span>Fresh: {snapshot.fresh}</span>
                <span>Aging: {snapshot.aging}</span>
                <span>Stale: {snapshot.stale}</span>
              </div>
              {(snapshot.changed_by_label || snapshot.source_action) ? (
                <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                  {snapshot.changed_by_label ? `Updated by ${snapshot.changed_by_label}` : 'Queue changed'}
                  {snapshot.source_action ? ` via ${snapshot.source_action.replaceAll('_', ' ')}` : ''}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm text-slate-500">{emptyLabel}</p>
      )}
    </div>
  );
}

function MobileInfoCard({
  title,
  subtitle,
  badges = [],
  details = [],
  actions = [],
  row,
  selectable = false,
  selected = false,
  onToggleSelected
}) {
  const visibleActions = actions.filter((action) => {
    const hidden = typeof action.hidden === 'function' ? action.hidden(row) : Boolean(action.hidden);
    return !hidden;
  });

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/60">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</p>
          <p className="mt-1 truncate text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
        </div>
        <div className="flex items-start gap-3">
          {badges.length ? (
            <div className="flex flex-wrap justify-end gap-2">
              {badges.map((badge) => (
                <span key={badge} className="rounded-full border border-slate-300 px-2 py-0.5 text-[11px] uppercase tracking-wide text-slate-600 dark:border-slate-600 dark:text-slate-300">
                  {badge}
                </span>
              ))}
            </div>
          ) : null}
          {selectable ? (
            <input
              type="checkbox"
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
              checked={selected}
              onChange={onToggleSelected}
              aria-label={`Select ${title}`}
            />
          ) : null}
        </div>
      </div>

      {details.length ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {details.map((detail) => (
            <div key={detail.label} className="rounded-xl border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950/50">
              <p className="text-[11px] uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">{detail.label}</p>
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">{detail.value}</p>
            </div>
          ))}
        </div>
      ) : null}

      {visibleActions.length ? (
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {visibleActions.map((action) => {
            const disabled = typeof action.disabled === 'function' ? action.disabled(row) : Boolean(action.disabled);
            const titleText = typeof action.title === 'function' ? action.title(row) : action.title || action.label;
            return (
              <button
                key={action.key}
                type="button"
                className={`btn-secondary w-full justify-center ${action.className || ''}`}
                onClick={() => action.onClick(row)}
                title={titleText}
                disabled={disabled}
              >
                {typeof action.label === 'function' ? action.label(row) : action.label}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
