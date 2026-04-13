import { useEffect, useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import SearchableSelect from '../components/ui/SearchableSelect';
import FormInput from '../components/ui/FormInput';
import { apiClient } from '../services/apiClient';
import {
  getAttendanceAnalytics,
  getAttendanceMarkingLookups,
  getAttendanceRoster,
  getAttendanceSectionSummary,
  getMyAttendanceAnalytics,
  getMyAttendanceSummary,
  markAttendanceBulk
} from '../services/attendanceApi';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { pushApiErrorToast } from '../utils/errorToast';

const STATUS_OPTIONS = [
  { value: 'present', label: 'Present' },
  { value: 'absent', label: 'Absent' },
  { value: 'late', label: 'Late' },
  { value: 'excused', label: 'Excused' }
];

function statusTone(status) {
  if (status === 'present') return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  if (status === 'late') return 'border-amber-200 bg-amber-50 text-amber-700';
  if (status === 'excused') return 'border-sky-200 bg-sky-50 text-sky-700';
  if (status === 'absent') return 'border-rose-200 bg-rose-50 text-rose-700';
  return 'border-slate-200 bg-slate-50 text-slate-600';
}

function slotLabel(item) {
  if (!item) return '';
  const section = item.section_name || 'Section';
  return `${section} | ${item.day} ${item.start_time}-${item.end_time} | ${item.subject_name || item.room_code || item.public_id || 'Slot'}`;
}

export default function AttendanceRecordsPage() {
  const { user } = useAuth();
  const { pushToast } = useToast();
  const isStudent = user?.role === 'student';
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lookupRows, setLookupRows] = useState([]);
  const [selectedSectionId, setSelectedSectionId] = useState('');
  const [selectedSlotId, setSelectedSlotId] = useState('');
  const [roster, setRoster] = useState(null);
  const [sectionSummary, setSectionSummary] = useState(null);
  const [sectionAnalytics, setSectionAnalytics] = useState(null);
  const [studentSummary, setStudentSummary] = useState(null);
  const [studentAnalytics, setStudentAnalytics] = useState(null);
  const [draftRows, setDraftRows] = useState({});
  const [studentRows, setStudentRows] = useState([]);
  const [rosterSearch, setRosterSearch] = useState('');
  const [rosterView, setRosterView] = useState('all');

  useEffect(() => {
    async function loadPage() {
      setLoading(true);
      try {
        if (isStudent) {
          const [response, summary, analytics] = await Promise.all([
            apiClient.get('/attendance-records/', { params: { skip: 0, limit: 200 } }),
            getMyAttendanceSummary(),
            getMyAttendanceAnalytics()
          ]);
          setStudentRows(response.data || []);
          setStudentSummary(summary || null);
          setStudentAnalytics(analytics || null);
          return;
        }
        const items = await getAttendanceMarkingLookups();
        setLookupRows(items || []);
      } catch (err) {
        pushApiErrorToast(pushToast, err, 'Unable to load attendance workspace');
        setLookupRows([]);
        setStudentRows([]);
        setStudentSummary(null);
        setStudentAnalytics(null);
      } finally {
        setLoading(false);
      }
    }
    loadPage();
  }, [isStudent, pushToast]);

  useEffect(() => {
    if (isStudent || !selectedSectionId) {
      setSectionSummary(null);
      setSectionAnalytics(null);
      return;
    }
    let cancelled = false;
    async function loadSectionSummary() {
      try {
        const [nextSummary, nextAnalytics] = await Promise.all([
          getAttendanceSectionSummary(selectedSectionId),
          getAttendanceAnalytics(selectedSectionId)
        ]);
        if (!cancelled) {
          setSectionSummary(nextSummary);
          setSectionAnalytics(nextAnalytics);
        }
      } catch (err) {
        if (!cancelled) {
          setSectionSummary(null);
          setSectionAnalytics(null);
          pushApiErrorToast(pushToast, err, 'Unable to load attendance summary');
        }
      }
    }
    loadSectionSummary();
    return () => {
      cancelled = true;
    };
  }, [isStudent, pushToast, selectedSectionId]);

  useEffect(() => {
    if (!selectedSlotId || isStudent) {
      setRoster(null);
      setDraftRows({});
      return;
    }
    let cancelled = false;
    async function loadRoster() {
      setLoading(true);
      try {
        const nextRoster = await getAttendanceRoster(selectedSlotId);
        if (cancelled) return;
        setRoster(nextRoster);
        setDraftRows(
          Object.fromEntries(
            (nextRoster?.students || []).map((student) => [
              student.student_id,
              {
                status: student.status || '',
                note: student.note || ''
              }
            ])
          )
        );
      } catch (err) {
        if (!cancelled) {
          pushApiErrorToast(pushToast, err, 'Unable to load attendance roster');
          setRoster(null);
          setDraftRows({});
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    loadRoster();
    return () => {
      cancelled = true;
    };
  }, [isStudent, pushToast, selectedSlotId]);

  const sectionOptions = useMemo(() => {
    const seen = new Map();
    lookupRows.forEach((item) => {
      const sectionId = item.section_id || '';
      if (!sectionId || seen.has(sectionId)) return;
      seen.set(sectionId, {
        value: sectionId,
        label: item.section_name || sectionId
      });
    });
    return Array.from(seen.values());
  }, [lookupRows]);

  const visibleSlots = useMemo(
    () => lookupRows.filter((item) => !selectedSectionId || String(item.section_id) === String(selectedSectionId)),
    [lookupRows, selectedSectionId]
  );

  const slotOptions = useMemo(
    () => visibleSlots.map((item) => ({ value: item.id, label: slotLabel(item) })),
    [visibleSlots]
  );

  const selectedSlotLabel = useMemo(
    () => slotOptions.find((item) => String(item.value) === String(selectedSlotId))?.label || '',
    [selectedSlotId, slotOptions]
  );

  function updateDraft(studentId, patch) {
    setDraftRows((prev) => ({
      ...prev,
      [studentId]: { ...(prev[studentId] || { status: '', note: '' }), ...patch }
    }));
  }

  function markAllPresent() {
    setDraftRows((prev) =>
      Object.fromEntries(
        (visibleRosterStudents || []).map((student) => [
          student.student_id,
          { ...(prev[student.student_id] || { note: '' }), status: 'present' }
        ])
      )
    );
  }

  function markVisibleStatus(status) {
    setDraftRows((prev) =>
      Object.fromEntries(
        (roster?.students || []).map((student) => {
          if (!visibleRosterStudents.find((item) => item.student_id === student.student_id)) {
            return [student.student_id, prev[student.student_id] || { status: student.status || '', note: student.note || '' }];
          }
          return [student.student_id, { ...(prev[student.student_id] || { note: '' }), status }];
        })
      )
    );
  }

  function clearVisibleStatuses() {
    setDraftRows((prev) =>
      Object.fromEntries(
        (roster?.students || []).map((student) => {
          if (!visibleRosterStudents.find((item) => item.student_id === student.student_id)) {
            return [student.student_id, prev[student.student_id] || { status: student.status || '', note: student.note || '' }];
          }
          return [student.student_id, { ...(prev[student.student_id] || { note: '' }), status: '' }];
        })
      )
    );
  }

  async function onSubmitAttendance() {
    const students = roster?.students || [];
    const incomplete = students.find((student) => !draftRows[student.student_id]?.status);
    if (incomplete) {
      pushToast({
        title: 'Incomplete attendance',
        description: `Select a status for ${incomplete.student_name} before submitting.`,
        variant: 'warning'
      });
      return;
    }

    setSaving(true);
    try {
      await markAttendanceBulk({
        class_slot_id: roster.class_slot_id,
        records: students.map((student) => ({
          class_slot_id: roster.class_slot_id,
          student_id: student.student_id,
          status: draftRows[student.student_id]?.status || 'present',
          note: draftRows[student.student_id]?.note || ''
        }))
      });
      if (selectedSectionId) {
        const [nextSummary, nextAnalytics] = await Promise.all([
          getAttendanceSectionSummary(selectedSectionId),
          getAttendanceAnalytics(selectedSectionId)
        ]);
        setSectionSummary(nextSummary);
        setSectionAnalytics(nextAnalytics);
      }
      pushToast({
        title: 'Attendance saved',
        description: `Saved attendance for ${students.length} students.`,
        variant: 'success'
      });
      const nextRoster = await getAttendanceRoster(roster.class_slot_id);
      setRoster(nextRoster);
    } catch (err) {
      pushApiErrorToast(pushToast, err, 'Unable to save attendance');
    } finally {
      setSaving(false);
    }
  }

  const visibleRosterStudents = useMemo(() => {
    const rows = roster?.students || [];
    return rows.filter((student) => {
      const query = rosterSearch.trim().toLowerCase();
      const draftStatus = draftRows[student.student_id]?.status || student.status || '';
      const matchesQuery =
        !query ||
        String(student.student_name || '').toLowerCase().includes(query) ||
        String(student.roll_number || '').toLowerCase().includes(query);
      const matchesView =
        rosterView === 'all' ||
        (rosterView === 'unmarked' && !draftStatus) ||
        (rosterView === 'exceptions' && draftStatus && draftStatus !== 'present') ||
        (rosterView === 'present' && draftStatus === 'present') ||
        (rosterView === 'absent' && draftStatus === 'absent');
      return matchesQuery && matchesView;
    });
  }, [draftRows, roster?.students, rosterSearch, rosterView]);

  if (isStudent) {
    return (
      <div className="space-y-5 page-fade">
        <Card className="space-y-2">
          <h1 className="text-2xl font-semibold">Attendance Logs</h1>
          <p className="text-sm text-slate-500">Your recorded attendance history across marked class slots.</p>
        </Card>
        {studentSummary ? (
          <div className="grid gap-3 md:grid-cols-4">
            {[
              ['Attendance %', `${studentSummary.attendance_percent ?? 0}%`],
              ['Marked Slots', studentSummary.total_marked_slots || 0],
              ['Present-like', studentSummary.present_like_slots || 0],
              ['Shortage Risk', studentSummary.shortage_risk ? 'Yes' : 'No']
            ].map(([label, value]) => (
              <Card key={label} className="!p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
                <p className="mt-1 text-2xl font-semibold">{value}</p>
              </Card>
            ))}
          </div>
        ) : null}
        {studentAnalytics ? (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
            <Card className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold">Attendance Trend</h2>
                <p className="text-sm text-slate-500">Weekly trend for the last {studentAnalytics.range_days} days.</p>
              </div>
              <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                {(studentAnalytics.trend || []).map((point) => (
                  <div key={point.label} className="rounded-2xl border border-slate-200 bg-slate-50/70 p-3">
                    <p className="text-xs uppercase tracking-wide text-slate-500">{point.label}</p>
                    <p className="mt-1 text-xl font-semibold">{point.attendance_percent}%</p>
                    <p className="text-xs text-slate-500">{point.total_marked_slots} marked slots</p>
                  </div>
                ))}
              </div>
            </Card>
            <Card className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold">Subject-wise Attendance</h2>
                <p className="text-sm text-slate-500">Published from recorded attendance in your section.</p>
              </div>
              <div className="space-y-2">
                {(studentAnalytics.subjects || []).map((subject) => (
                  <div key={`${subject.subject_id || 'subject'}-${subject.subject_name}`} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50/70 p-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{subject.subject_name || 'Unassigned Subject'}</p>
                      <p className="text-xs text-slate-500">
                        Present-like: {subject.present_like_slots} | Absent: {subject.absent_slots}
                      </p>
                    </div>
                    <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${subject.shortage_risk ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-emerald-200 bg-emerald-50 text-emerald-700'}`}>
                      {subject.attendance_percent}%
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        ) : null}
        {loading ? <Card>Loading attendance...</Card> : null}
        {!loading && studentRows.length === 0 ? <Card>No attendance records are available yet.</Card> : null}
        {!loading && studentRows.length > 0 ? (
          <div className="grid gap-3 lg:grid-cols-2">
            {studentRows.map((row) => (
              <Card key={row.id} className="space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold">{row.public_id || row.class_slot_id}</p>
                  <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${statusTone(row.status)}`}>
                    {row.status}
                  </span>
                </div>
                <p className="text-xs text-slate-500">Marked at: {row.marked_at ? new Date(row.marked_at).toLocaleString() : '-'}</p>
                <p className="text-sm text-slate-600">{row.note || 'No note added.'}</p>
              </Card>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-5 page-fade">
      <Card className="space-y-2">
        <h1 className="text-2xl font-semibold">Attendance Workspace</h1>
        <p className="text-sm text-slate-500">
          Select a section and class slot, review the roster, and submit attendance for the full class in one action.
        </p>
      </Card>

      <Card className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
          <SearchableSelect
            label="Section"
            value={selectedSectionId}
            options={sectionOptions}
            allowEmpty
            emptyLabel="All sections"
            selectedLabel={sectionOptions.find((item) => item.value === selectedSectionId)?.label || ''}
            onValueChange={(value) => {
              setSelectedSectionId(value || '');
              setSelectedSlotId('');
            }}
          />
          <SearchableSelect
            label="Class Slot"
            value={selectedSlotId}
            options={slotOptions}
            selectedLabel={selectedSlotLabel}
            placeholder={selectedSectionId ? 'Select a class slot' : 'Select section or search all slots'}
            onValueChange={(value) => setSelectedSlotId(value || '')}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-secondary" onClick={markAllPresent} disabled={!roster?.students?.length}>
            Mark Visible Roster Present
          </button>
          <button className="btn-secondary" onClick={() => markVisibleStatus('absent')} disabled={!visibleRosterStudents.length}>
            Mark Visible Absent
          </button>
          <button className="btn-secondary" onClick={clearVisibleStatuses} disabled={!visibleRosterStudents.length}>
            Clear Visible
          </button>
          <button className="btn-primary" onClick={onSubmitAttendance} disabled={!roster?.students?.length || saving}>
            {saving ? 'Saving...' : 'Save Attendance'}
          </button>
        </div>
      </Card>

      {sectionSummary ? (
        <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          {[
            ['Students', sectionSummary.total_students],
            ['Tracked Slots', sectionSummary.total_slots],
            ['Marked Records', sectionSummary.total_marked_records],
            ['Avg Attendance', `${sectionSummary.average_attendance_percent ?? 0}%`],
            ['Shortage Threshold', `${sectionSummary.shortage_threshold ?? 75}%`],
            ['At Risk', sectionSummary.shortage_risk_count]
          ].map(([label, value]) => (
            <Card key={label} className="!p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
              <p className="mt-1 text-2xl font-semibold">{value}</p>
            </Card>
          ))}
        </div>
      ) : null}

      {sectionAnalytics ? (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
          <Card className="space-y-3">
            <div>
              <h2 className="text-lg font-semibold">Section Attendance Trend</h2>
              <p className="text-sm text-slate-500">Weekly attendance movement for the last {sectionAnalytics.range_days} days.</p>
            </div>
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
              {(sectionAnalytics.trend || []).map((point) => (
                <div key={point.label} className="rounded-2xl border border-slate-200 bg-slate-50/70 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-500">{point.label}</p>
                  <p className="mt-1 text-xl font-semibold">{point.attendance_percent}%</p>
                  <p className="text-xs text-slate-500">{point.total_marked_slots} marked slots</p>
                </div>
              ))}
            </div>
          </Card>
          <Card className="space-y-3">
            <div>
              <h2 className="text-lg font-semibold">Subject-wise Attendance</h2>
              <p className="text-sm text-slate-500">Use this to spot shortage pressure by subject instead of only by section.</p>
            </div>
            <div className="space-y-2">
              {(sectionAnalytics.subjects || []).map((subject) => (
                <div key={`${subject.subject_id || 'subject'}-${subject.subject_name}`} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50/70 p-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{subject.subject_name || 'Unassigned Subject'}</p>
                    <p className="text-xs text-slate-500">
                      Present-like: {subject.present_like_slots} | Absent: {subject.absent_slots} | Marked: {subject.total_marked_slots}
                    </p>
                  </div>
                  <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${subject.shortage_risk ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-emerald-200 bg-emerald-50 text-emerald-700'}`}>
                    {subject.attendance_percent}%
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      ) : null}

      {loading ? <Card>Loading attendance roster...</Card> : null}

      {roster ? (
        <>
          <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
            {[
              ['Students', roster.summary.total_students],
              ['Marked', roster.summary.marked_students],
              ['Present', roster.summary.present],
              ['Late', roster.summary.late],
              ['Excused', roster.summary.excused],
              ['Absent', roster.summary.absent]
            ].map(([label, value]) => (
              <Card key={label} className="!p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
                <p className="mt-1 text-2xl font-semibold">{value}</p>
              </Card>
            ))}
          </div>

          <Card className="space-y-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">{roster.section_name || 'Section'} Attendance Roster</h2>
                <p className="text-sm text-slate-500">
                  {roster.subject_name || 'Subject'} | {roster.day} {roster.start_time}-{roster.end_time} | {roster.room_code || 'Room TBA'}
                </p>
                <p className="text-xs text-slate-500">
                  Teacher: {roster.teacher_name || '-'}{roster.group_name ? ` | Group: ${roster.group_name}` : ''}
                </p>
              </div>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600">
                Unmarked: {roster.summary.unmarked}
              </span>
            </div>

            <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px]">
              <FormInput
                label="Search roster"
                value={rosterSearch}
                onChange={(event) => setRosterSearch(event.target.value)}
                placeholder="Search by student name or roll number"
              />
              <FormInput
                as="select"
                label="View"
                value={rosterView}
                onChange={(event) => setRosterView(event.target.value)}
              >
                <option value="all">All students</option>
                <option value="unmarked">Unmarked only</option>
                <option value="exceptions">Exceptions only</option>
                <option value="present">Present only</option>
                <option value="absent">Absent only</option>
              </FormInput>
            </div>

            <div className="sticky bottom-3 z-10 rounded-2xl border border-sky-200 bg-white/95 px-4 py-3 shadow-sm backdrop-blur">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-slate-600">
                  Visible roster: <span className="font-semibold text-slate-900">{visibleRosterStudents.length}</span> students
                </p>
                <div className="flex flex-wrap gap-2">
                  <button className="btn-secondary" onClick={markAllPresent} disabled={!visibleRosterStudents.length}>
                    Present Visible
                  </button>
                  <button className="btn-secondary" onClick={() => markVisibleStatus('late')} disabled={!visibleRosterStudents.length}>
                    Late Visible
                  </button>
                  <button className="btn-primary" onClick={onSubmitAttendance} disabled={!roster?.students?.length || saving}>
                    {saving ? 'Saving...' : 'Save Attendance'}
                  </button>
                </div>
              </div>
            </div>

            <div className="grid gap-3">
              {visibleRosterStudents.map((student) => (
                <div key={student.student_id} className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                  <div className="grid gap-3 xl:grid-cols-[minmax(0,1.2fr)_160px_minmax(0,1fr)]">
                    <div className="space-y-1">
                      <p className="text-sm font-semibold text-slate-900">{student.student_name}</p>
                      <p className="text-xs text-slate-500">
                        {student.roll_number || 'No roll number'}{student.group_name ? ` | ${student.group_name}` : ''}
                      </p>
                      <p className="text-xs text-slate-500">
                        Attendance health: {student.attendance_percent != null ? `${student.attendance_percent}%` : 'Not enough data yet'}
                      </p>
                    </div>
                    <FormInput
                      as="select"
                      label="Status"
                      value={draftRows[student.student_id]?.status || ''}
                      onChange={(event) => updateDraft(student.student_id, { status: event.target.value })}
                    >
                      <option value="">Select status</option>
                      {STATUS_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </FormInput>
                    <FormInput
                      label="Note"
                      value={draftRows[student.student_id]?.note || ''}
                      onChange={(event) => updateDraft(student.student_id, { note: event.target.value })}
                      placeholder="Optional note"
                    />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </>
      ) : null}

      {!loading && !roster ? (
        <Card>Select a class slot to load the attendance roster.</Card>
      ) : null}
    </div>
  );
}
