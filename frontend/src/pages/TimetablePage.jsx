import { useEffect, useMemo, useState } from 'react';
import { Download, Lock, Sparkles } from 'lucide-react';
import Card from '../components/ui/Card';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import {
  createTimetable,
  getTimetableShifts,
  listClassTimetables,
  publishTimetable,
  updateTimetable
} from '../services/timetableApi';
import { apiClient } from '../services/apiClient';
import { pushApiErrorToast } from '../utils/errorToast';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const SESSION_TYPES = [
  { value: 'theory', label: 'Theory' },
  { value: 'practical', label: 'Practical' },
  { value: 'workshop', label: 'Workshop' },
  { value: 'interaction', label: 'Interaction' }
];

function entryKey(day, slotKey) {
  return `${day}::${slotKey}`;
}

export default function TimetablePage() {
  const { user } = useAuth();
  const { pushToast } = useToast();

  const isStudent = user?.role === 'student';
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);

  const [shifts, setShifts] = useState([]);
  const [classes, setClasses] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [teacherBySubject, setTeacherBySubject] = useState({});

  const [selectedClassId, setSelectedClassId] = useState('');
  const [selectedSemester, setSelectedSemester] = useState('SEM-1');
  const [selectedShiftId, setSelectedShiftId] = useState('shift_1');
  const [selectedTimetableId, setSelectedTimetableId] = useState('');
  const [classTimetables, setClassTimetables] = useState([]);
  const [timetable, setTimetable] = useState(null);
  const [draftMap, setDraftMap] = useState({});
  const [studentClassSlots, setStudentClassSlots] = useState([]);
  const [studentOfferings, setStudentOfferings] = useState([]);

  async function loadLookups(classId) {
    const [shiftRes, lookupRes] = await Promise.all([
      getTimetableShifts(),
      apiClient
        .get('/timetables/lookups', {
          params: classId ? { class_id: classId } : undefined
        })
        .then((res) => res.data || {})
    ]);
    setShifts(shiftRes || []);
    setClasses(lookupRes.classes || []);
    setSubjects(lookupRes.subjects || []);
    setTeachers(lookupRes.teachers || []);
    setTeacherBySubject(lookupRes.teacher_by_subject || {});
    if (!selectedClassId && (lookupRes.classes || []).length > 0) {
      setSelectedClassId(lookupRes.classes[0].id);
    }
    if (!selectedShiftId && (shiftRes || []).length > 0) {
      setSelectedShiftId(shiftRes[0].id);
    }
  }

  async function loadStudentTimetable() {
    setLoading(true);
    try {
      const [slotsResp, offeringsResp] = await Promise.all([
        apiClient.get('/class-slots/my'),
        apiClient.get('/course-offerings/', { params: { skip: 0, limit: 100 } })
      ]);
      setStudentClassSlots(slotsResp.data || []);
      setStudentOfferings(offeringsResp.data || []);
    } catch (err) {
      setStudentClassSlots([]);
      setStudentOfferings([]);
      pushApiErrorToast(pushToast, err, 'Unable to load timetable slots');
    } finally {
      setLoading(false);
    }
  }

  async function loadClassTimetables(classId) {
    if (!classId) return;
    setLoading(true);
    try {
      const rows = await listClassTimetables(classId);
      setClassTimetables(rows);
      if (rows.length > 0) {
        const picked = rows[0];
        setSelectedTimetableId(picked.id);
        setTimetable(picked);
      } else {
        setSelectedTimetableId('');
        setTimetable(null);
      }
    } catch (err) {
      pushApiErrorToast(pushToast, err, 'Unable to load class timetables');
      setClassTimetables([]);
      setTimetable(null);
      setSelectedTimetableId('');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (isStudent) {
      loadStudentTimetable();
      return;
    }
    loadLookups();
  }, [isStudent]);

  useEffect(() => {
    if (isStudent || !selectedClassId) return;
    loadLookups(selectedClassId);
    loadClassTimetables(selectedClassId);
  }, [selectedClassId, isStudent]);

  useEffect(() => {
    if (!timetable) {
      setDraftMap({});
      return;
    }
    const next = {};
    (timetable.entries || []).forEach((entry) => {
      next[entryKey(entry.day, entry.slot_key)] = {
        subject_id: entry.subject_id || '',
        teacher_user_id: entry.teacher_user_id || '',
        room_code: entry.room_code || '',
        session_type: entry.session_type || 'theory'
      };
    });
    setDraftMap(next);
  }, [timetable?.id]);

  const shift = useMemo(() => {
    if (timetable?.shift_id) return shifts.find((item) => item.id === timetable.shift_id) || null;
    return shifts.find((item) => item.id === selectedShiftId) || null;
  }, [selectedShiftId, shifts, timetable?.shift_id]);

  const slots = useMemo(() => timetable?.slots || shift?.slots || [], [shift?.slots, timetable?.slots]);
  const days = useMemo(() => timetable?.days || DAYS, [timetable?.days]);
  const isLocked = Boolean(timetable?.admin_locked) || timetable?.status === 'published';

  const selectedClassName = useMemo(() => {
    const item = classes.find((it) => it.id === selectedClassId);
    return item ? item.name : '-';
  }, [classes, selectedClassId]);

  const studentOfferingMap = useMemo(
    () => Object.fromEntries(studentOfferings.map((item) => [item.id, item])),
    [studentOfferings]
  );

  const studentTimetableByDay = useMemo(() => {
    if (!studentClassSlots.length) return [];
    const grouped = {};
    for (const slot of studentClassSlots) {
      const offering = studentOfferingMap[slot.course_offering_id] || {};
      const day = slot.day || 'Unknown';
      if (!grouped[day]) grouped[day] = [];
      grouped[day].push({
        ...slot,
        subject: offering.subject_name || offering.subject_code || offering.subject_id || 'Subject',
        teacher: offering.teacher_name || offering.teacher_user_id || 'Teacher',
        group: offering.group_name || '',
        type: offering.offering_type || '-'
      });
    }
    return Object.entries(grouped)
      .map(([day, rows]) => ({
        day,
        rows: [...rows].sort((a, b) => String(a.start_time).localeCompare(String(b.start_time)))
      }))
      .sort((a, b) => DAY_ORDER.indexOf(a.day) - DAY_ORDER.indexOf(b.day));
  }, [studentClassSlots, studentOfferingMap]);

  function updateCell(day, slotKey, patch) {
    const key = entryKey(day, slotKey);
    setDraftMap((prev) => ({
      ...prev,
      [key]: { ...(prev[key] || { session_type: 'theory' }), ...patch }
    }));
  }

  function buildEntriesFromDraft() {
    const rows = [];
    for (const day of days) {
      for (const slot of slots) {
        if (slot.is_lunch) continue;
        const key = entryKey(day, slot.slot_key);
        const entry = draftMap[key] || {};
        if (!entry.subject_id && !entry.teacher_user_id && !entry.room_code) continue;
        if (!entry.subject_id || !entry.teacher_user_id || !entry.room_code) {
          throw new Error(`Please fill subject, teacher and room for ${day} ${slot.label}`);
        }
        rows.push({
          day,
          slot_key: slot.slot_key,
          subject_id: entry.subject_id,
          teacher_user_id: entry.teacher_user_id,
          room_code: entry.room_code,
          session_type: entry.session_type || 'theory'
        });
      }
    }
    return rows;
  }

  async function handleCreateDraft() {
    if (!selectedClassId || !selectedSemester || !selectedShiftId) {
      pushToast({ title: 'Missing fields', description: 'Select class, semester and shift.', variant: 'warning' });
      return;
    }
    setSaving(true);
    try {
      const created = await createTimetable({
        class_id: selectedClassId,
        semester: selectedSemester,
        shift_id: selectedShiftId,
        days: DAYS,
        entries: []
      });
      pushToast({ title: 'Draft created', description: 'Timetable draft is ready for allocation.', variant: 'success' });
      await loadClassTimetables(selectedClassId);
      setSelectedTimetableId(created.id);
    } catch (err) {
      pushApiErrorToast(pushToast, err, 'Unable to create timetable draft');
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveDraft() {
    if (!timetable?.id || isLocked) return;
    setSaving(true);
    try {
      const entries = buildEntriesFromDraft();
      const saved = await updateTimetable(timetable.id, { entries, days });
      setTimetable(saved);
      pushToast({ title: 'Saved', description: 'Timetable draft saved.', variant: 'success' });
      await loadClassTimetables(selectedClassId);
    } catch (err) {
      pushApiErrorToast(pushToast, err, 'Unable to save timetable');
    } finally {
      setSaving(false);
    }
  }

  async function handlePublish() {
    if (!timetable?.id || isLocked) return;
    setPublishing(true);
    try {
      const entries = buildEntriesFromDraft();
      await updateTimetable(timetable.id, { entries, days });
      const published = await publishTimetable(timetable.id);
      setTimetable(published);
      pushToast({ title: 'Published', description: 'Timetable published for students.', variant: 'success' });
      await loadClassTimetables(selectedClassId);
    } catch (err) {
      pushApiErrorToast(pushToast, err, 'Unable to publish timetable');
    } finally {
      setPublishing(false);
    }
  }

  if (isStudent) {
    return (
      <div className="space-y-5 page-fade">
        <Card className="space-y-2">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold">My Timetable</h1>
              <p className="text-sm text-slate-500">Section and group filtered timetable from class slots.</p>
            </div>
            <div className="flex items-center gap-2">
              <button className="btn-secondary" onClick={loadStudentTimetable}>Refresh</button>
              <button className="btn-secondary" onClick={() => window.print()}>
                <Download size={15} /> Download / Print
              </button>
            </div>
          </div>
        </Card>
        {loading ? <Card>Loading timetable...</Card> : null}
        {!loading && studentTimetableByDay.length === 0 ? <Card>No class slots available yet.</Card> : null}
        {!loading && studentTimetableByDay.length > 0 ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {studentTimetableByDay.map((dayBlock) => (
              <Card key={dayBlock.day} className="space-y-3">
                <h2 className="text-lg font-semibold">{dayBlock.day}</h2>
                <div className="space-y-2">
                  {dayBlock.rows.map((row) => (
                    <div key={row.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/30">
                      <p className="text-xs text-slate-500">{row.start_time} - {row.end_time}</p>
                      <p className="mt-1 text-sm font-semibold">{row.subject}</p>
                      <p className="text-xs text-slate-500">{row.teacher}</p>
                      <p className="text-xs text-slate-500">{row.room_code} | {row.type}{row.group ? ` | ${row.group}` : ''}</p>
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-5 page-fade">
      <Card className="space-y-4">
        <div>
          <h1 className="text-2xl font-semibold">Class Timetable Management</h1>
          <p className="text-sm text-slate-500">Class coordinators can generate shift-based timetable, allocate periods, and publish for students.</p>
          {user?.role === 'teacher' ? (
            <div className="mt-2 inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700 dark:border-indigo-700/40 dark:bg-indigo-900/20 dark:text-indigo-300">
              Assigned Section Only
            </div>
          ) : null}
        </div>
        <div className="grid gap-3 md:grid-cols-5">
          <label className="space-y-1 text-sm">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Class</span>
            <select className="input" value={selectedClassId} onChange={(e) => setSelectedClassId(e.target.value)}>
              <option value="">Select class</option>
              {classes.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Semester</span>
            <input className="input" value={selectedSemester} onChange={(e) => setSelectedSemester(e.target.value)} />
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Shift</span>
            <select className="input" value={selectedShiftId} onChange={(e) => setSelectedShiftId(e.target.value)}>
              {shifts.map((shiftItem) => (
                <option key={shiftItem.id} value={shiftItem.id}>
                  {shiftItem.label}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1 text-sm md:col-span-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Existing Timetable Version</span>
            <select
              className="input"
              value={selectedTimetableId}
              onChange={(e) => {
                setSelectedTimetableId(e.target.value);
                const picked = classTimetables.find((row) => row.id === e.target.value) || null;
                setTimetable(picked);
              }}
            >
              <option value="">No timetable selected</option>
              {classTimetables.map((row) => (
                <option key={row.id} value={row.id}>
                  v{row.version} | {row.status} | {row.semester} | {row.shift_label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button className="btn-primary" onClick={handleCreateDraft} disabled={saving || !selectedClassId}>
            <Sparkles size={15} /> Generate Draft
          </button>
          <button className="btn-secondary" onClick={handleSaveDraft} disabled={saving || !timetable || isLocked}>
            Save Draft
          </button>
          <button className="btn-secondary" onClick={handlePublish} disabled={publishing || !timetable || isLocked}>
            Publish Timetable
          </button>
          <span className="text-sm text-slate-500">
            {timetable
              ? `Selected: ${selectedClassName} | ${timetable.shift_label} | Status: ${timetable.status}`
              : 'Create or select a timetable to start allocation.'}
          </span>
          {user?.role === 'teacher' ? (
            <span className="text-xs text-slate-500">You can create and manage timetable only for your assigned section.</span>
          ) : null}
          {isLocked ? (
            <span className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
              <Lock size={12} /> Locked / Published
            </span>
          ) : null}
        </div>
      </Card>

      <Card>
        {loading ? <p>Loading timetable...</p> : null}
        {!loading && !timetable ? <p className="text-sm text-slate-500">No timetable selected.</p> : null}
        {!loading && timetable ? (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="rounded-full bg-slate-100 px-3 py-1 dark:bg-slate-800">{timetable.shift_label}</span>
              <span className="rounded-full bg-slate-100 px-3 py-1 dark:bg-slate-800">Semester: {timetable.semester}</span>
              <span className="rounded-full bg-slate-100 px-3 py-1 dark:bg-slate-800">Version: {timetable.version}</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1100px] text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    <th className="p-2 text-left">Slot</th>
                    {days.map((day) => (
                      <th key={day} className="p-2 text-left">{day}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {slots.map((slot) => (
                    <tr key={slot.slot_key} className="border-b border-slate-100 align-top dark:border-slate-800">
                      <td className="p-2 font-medium">
                        <div>{slot.label}</div>
                        <div className="text-xs text-slate-500">{slot.start_time} - {slot.end_time}</div>
                      </td>
                      {days.map((day) => {
                        if (slot.is_lunch) {
                          return (
                            <td key={`${day}-${slot.slot_key}`} className="p-2">
                              <div className="rounded-lg border border-amber-300 bg-amber-50 px-2 py-2 text-xs font-semibold text-amber-700">
                                Lunch Lock
                              </div>
                            </td>
                          );
                        }
                        const key = entryKey(day, slot.slot_key);
                        const value = draftMap[key] || { session_type: 'theory' };
                        return (
                          <td key={key} className="p-2">
                            <div className="space-y-1">
                              <select
                                className="input"
                                value={value.subject_id || ''}
                                disabled={isLocked}
                                onChange={(e) => updateCell(day, slot.slot_key, { subject_id: e.target.value })}
                              >
                                <option value="">Subject</option>
                                {subjects.map((subject) => (
                                  <option key={subject.id} value={subject.id}>
                                    {subject.name} ({subject.code})
                                  </option>
                                ))}
                              </select>
                              <select
                                className="input"
                                value={value.teacher_user_id || ''}
                                disabled={isLocked}
                                onChange={(e) => updateCell(day, slot.slot_key, { teacher_user_id: e.target.value })}
                              >
                                <option value="">Teacher</option>
                                {(() => {
                                  const allowedTeacherIds = teacherBySubject[value.subject_id] || [];
                                  const pool = allowedTeacherIds.length
                                    ? teachers.filter((teacher) => allowedTeacherIds.includes(teacher.id))
                                    : teachers;
                                  return pool.map((teacher) => (
                                    <option key={teacher.id} value={teacher.id}>
                                      {teacher.name}
                                    </option>
                                  ));
                                })()}
                              </select>
                              <input
                                className="input"
                                placeholder="Room/Lab"
                                value={value.room_code || ''}
                                disabled={isLocked}
                                onChange={(e) => updateCell(day, slot.slot_key, { room_code: e.target.value })}
                              />
                              <select
                                className="input"
                                value={value.session_type || 'theory'}
                                disabled={isLocked}
                                onChange={(e) => updateCell(day, slot.slot_key, { session_type: e.target.value })}
                              >
                                {SESSION_TYPES.map((item) => (
                                  <option key={item.value} value={item.value}>
                                    {item.label}
                                  </option>
                                ))}
                              </select>
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}
      </Card>
    </div>
  );
}

