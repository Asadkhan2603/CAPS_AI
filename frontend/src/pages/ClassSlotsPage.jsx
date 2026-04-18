import { useEffect, useMemo, useState } from 'react';
import { BookOpen, CalendarRange, Clock, MapPin, RefreshCw, UserRound } from 'lucide-react';
import EntityManager from '../components/ui/EntityManager';
import Card from '../components/ui/Card';
import EmptyState from '../components/ui/EmptyState';
import InlineErrorState from '../components/ui/InlineErrorState';
import PageLoader from '../components/ui/PageLoader';
import { apiClient } from '../services/apiClient';
import { useAuth } from '../hooks/useAuth';
import { getSectionPage } from '../services/sectionsApi';
import { formatApiError } from '../utils/apiError';

const DAY_OPTIONS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].map((day) => ({
  value: day,
  label: day
}));
const DAY_ORDER = Object.fromEntries(DAY_OPTIONS.map((item, index) => [item.value, index]));

function formatSlotTime(slot) {
  return `${slot.start_time || '-'} - ${slot.end_time || '-'}`;
}

function sortClassSlots(rows) {
  return [...rows].sort((first, second) => {
    const dayDelta = (DAY_ORDER[first.day] ?? 99) - (DAY_ORDER[second.day] ?? 99);
    if (dayDelta !== 0) return dayDelta;
    return String(first.start_time || '').localeCompare(String(second.start_time || ''));
  });
}

function groupSlotsByDay(rows) {
  return sortClassSlots(rows).reduce((groups, slot) => {
    const day = slot.day || 'Unscheduled';
    if (!groups[day]) groups[day] = [];
    groups[day].push(slot);
    return groups;
  }, {});
}

function StudentClassSlotsView() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function loadMyClassSlots() {
    setLoading(true);
    setError('');
    try {
      const response = await apiClient.get('/class-slots/my');
      setRows(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      const message =
        err?.response?.status === 401
          ? 'Your session has expired. Please sign in again to view your classes.'
          : formatApiError(err, 'Failed to load your class slots');
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMyClassSlots();
  }, []);

  const groupedSlots = useMemo(() => groupSlotsByDay(rows), [rows]);
  const dayEntries = useMemo(
    () => Object.entries(groupedSlots).sort(([first], [second]) => (DAY_ORDER[first] ?? 99) - (DAY_ORDER[second] ?? 99)),
    [groupedSlots]
  );
  const todayName = new Date().toLocaleDateString(undefined, { weekday: 'long' });
  const todaySlots = groupedSlots[todayName] || [];

  return (
    <div className="space-y-4 page-fade">
      <Card className="overflow-hidden border-brand-100 bg-gradient-to-br from-white via-brand-50/60 to-slate-50 shadow-sm dark:border-brand-950/40 dark:from-slate-950 dark:via-slate-900 dark:to-brand-950/20">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-600">Student Timetable</p>
            <h1 className="mt-1 text-2xl font-semibold text-slate-950 dark:text-slate-50">My Classes</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-600 dark:text-slate-300">
              Read-only list of your scheduled class slots, grouped by day with subject, teacher, time, and room context.
            </p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold">
              <span className="rounded-full bg-brand-50 px-3 py-1 text-brand-700 dark:bg-brand-950/40 dark:text-brand-200">
                Total slots: {rows.length}
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                Today: {todaySlots.length}
              </span>
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-200">
                Read-only
              </span>
            </div>
          </div>
          <button type="button" className="btn-secondary" onClick={() => void loadMyClassSlots()} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </Card>

      {loading && !rows.length ? <PageLoader compact label="Loading your classes..." /> : null}

      {error ? (
        <InlineErrorState
          title="Could not load class slots"
          description={error}
          onRetry={() => void loadMyClassSlots()}
        />
      ) : null}

      {!loading && !error && !rows.length ? (
        <EmptyState
          title="No class slots found"
          description="Your class schedule has not been published yet, or your student section is not mapped."
        />
      ) : null}

      {!error && rows.length ? (
        <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
          <Card className="space-y-4">
            <div className="flex items-center gap-2">
              <CalendarRange size={18} className="text-brand-600" />
              <h2 className="text-lg font-semibold">Today</h2>
            </div>
            {!todaySlots.length ? (
              <EmptyState
                compact
                title="No classes today"
                description="Enjoy the breathing room, or check the weekly schedule for upcoming slots."
              />
            ) : (
              <div className="space-y-3">
                {sortClassSlots(todaySlots).map((slot) => (
                  <div key={slot.id} className="rounded-2xl border border-brand-100 bg-brand-50/70 px-4 py-3 dark:border-brand-900/40 dark:bg-brand-950/20">
                    <p className="text-sm font-semibold text-slate-950 dark:text-slate-50">{slot.subject_name || slot.display_label || 'Class Slot'}</p>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{slot.subject_code || slot.offering_type || 'Course offering'}</p>
                    <div className="mt-3 grid gap-2 text-xs text-slate-600 dark:text-slate-300">
                      <span className="inline-flex items-center gap-2"><Clock size={14} /> {formatSlotTime(slot)}</span>
                      <span className="inline-flex items-center gap-2"><MapPin size={14} /> {slot.room_code || '-'}</span>
                      <span className="inline-flex items-center gap-2"><UserRound size={14} /> {slot.teacher_name || 'Faculty not assigned'}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card className="space-y-4">
            <div className="flex items-center gap-2">
              <BookOpen size={18} className="text-brand-600" />
              <h2 className="text-lg font-semibold">Weekly Class Slots</h2>
            </div>
            <div className="space-y-4">
              {dayEntries.map(([day, slots]) => (
                <section key={day} className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-950/40">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-semibold text-slate-950 dark:text-slate-50">{day}</h3>
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                      {slots.length} slot{slots.length === 1 ? '' : 's'}
                    </span>
                  </div>
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    {slots.map((slot) => (
                      <div key={slot.id} className="rounded-2xl border border-slate-200 px-3 py-3 dark:border-slate-700">
                        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{slot.subject_name || slot.display_label || 'Class Slot'}</p>
                        <p className="mt-1 text-xs text-slate-500">
                          {slot.section_name || 'Section'}{slot.group_name ? ` | ${slot.group_name}` : ''}
                        </p>
                        <div className="mt-3 flex flex-wrap gap-2 text-xs">
                          <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                            {formatSlotTime(slot)}
                          </span>
                          <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                            {slot.room_code || 'Room -'}
                          </span>
                          <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                            {slot.teacher_name || 'Faculty -'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </Card>
        </div>
      ) : null}
    </div>
  );
}

export default function ClassSlotsPage() {
  const { user } = useAuth();
  const isStudent = user?.role === 'student';
  const [offerings, setOfferings] = useState([]);
  const [sections, setSections] = useState([]);

  useEffect(() => {
    async function loadOfferings() {
      if (isStudent) return;
      const [offeringsRes, sectionsRes] = await Promise.allSettled([
        apiClient.get('/course-offerings/', { params: { skip: 0, limit: 100 } }),
        getSectionPage({}, 100)
      ]);
      setOfferings(offeringsRes.status === 'fulfilled' ? offeringsRes.value.data || [] : []);
      setSections(sectionsRes.status === 'fulfilled' ? sectionsRes.value || [] : []);
    }
    loadOfferings();
  }, [isStudent]);

  function sectionLabel(item) {
    if (!item) return '';
    return item.display_label || `${item.name} (${item.public_id || 'Section'})`;
  }

  function offeringLabel(item) {
    if (!item) return '';
    const section = sectionMap[item.section_id] || item.section_name || 'Section';
    return item.display_label || `${section} | ${item.public_id || item.offering_type}`;
  }

  const sectionOptions = useMemo(
    () =>
      sections.map((item) => ({
        value: item.id,
        label: sectionLabel(item)
      })),
    [sections]
  );
  const sectionMap = useMemo(
    () => Object.fromEntries(sections.map((item) => [item.id, sectionLabel(item)])),
    [sections]
  );

  const offeringOptions = useMemo(
    () =>
      offerings.map((item) => ({
        value: item.id,
        label: offeringLabel(item)
      })),
    [offerings, sectionMap]
  );
  const offeringMap = useMemo(
    () =>
      Object.fromEntries(
        offerings.map((item) => [item.id, offeringLabel(item)])
      ),
    [offerings, sectionMap]
  );

  const filters = useMemo(
    () => [
      { name: 'section_id', label: 'Section', type: 'select', options: sectionOptions, placeholder: 'All Sections' },
      { name: 'course_offering_id', label: 'Offering', type: 'select', options: offeringOptions, placeholder: 'All Offerings' },
      { name: 'day', label: 'Day', type: 'select', options: DAY_OPTIONS, placeholder: 'All Days' },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [offeringOptions, sectionOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'course_offering_id', label: 'Offering', type: 'select', options: offeringOptions, required: true },
      { name: 'day', label: 'Day', type: 'select', options: DAY_OPTIONS, required: true },
      { name: 'start_time', label: 'Start Time', placeholder: 'HH:MM', required: true },
      { name: 'end_time', label: 'End Time', placeholder: 'HH:MM', required: true },
      { name: 'room_code', label: 'Room / Lab', required: true }
    ],
    [offeringOptions]
  );
  const editFields = useMemo(
    () => [
      ...createFields,
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: true }
    ],
    [createFields]
  );

  const columns = useMemo(
    () => [
      { key: 'public_id', label: 'Short ID', render: (row) => row.public_id || '-' },
      { key: 'course_offering_id', label: 'Offering', render: (row) => offeringMap[row.course_offering_id] || '-' },
      { key: 'day', label: 'Day' },
      { key: 'start_time', label: 'Start' },
      { key: 'end_time', label: 'End' },
      { key: 'room_code', label: 'Room' }
    ],
    [offeringMap]
  );

  if (isStudent) {
    return <StudentClassSlotsView />;
  }

  return (
    <EntityManager
      title="Class Slots"
      endpoint="/class-slots/"
      filters={filters}
      createFields={createFields}
      editFields={editFields}
      columns={columns}
      enableEdit={!isStudent}
      enableDelete={!isStudent}
      hideCreate={isStudent}
    />
  );
}
