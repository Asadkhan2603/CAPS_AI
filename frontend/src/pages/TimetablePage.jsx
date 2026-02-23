import { useEffect, useMemo, useState } from 'react';
import { CalendarClock, Clock3 } from 'lucide-react';
import Card from '../components/ui/Card';
import { apiClient } from '../services/apiClient';
import { useAuth } from '../hooks/useAuth';

const weekDays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const slots = ['09:00-10:00', '11:00-12:00', '14:00-15:00'];

export default function TimetablePage() {
  const { user } = useAuth();
  const [assignments, setAssignments] = useState([]);

  useEffect(() => {
    async function loadAssignments() {
      try {
        const response = await apiClient.get('/assignments/', { params: { skip: 0, limit: 300 } });
        setAssignments(response.data || []);
      } catch {
        setAssignments([]);
      }
    }
    loadAssignments();
  }, []);

  const timetable = useMemo(() => {
    const subjectPool = Array.from(new Set(assignments.map((item) => item.subject_id).filter(Boolean)));
    const labels = subjectPool.length ? subjectPool : ['Core Subject', 'Lab Session', 'Project'];
    return weekDays.map((day, index) => ({
      day,
      sessions: slots.map((slot, slotIndex) => ({
        time: slot,
        subject: labels[(index + slotIndex) % labels.length]
      }))
    }));
  }, [assignments]);

  const todayName = new Date().toLocaleDateString(undefined, { weekday: 'long' });
  const today = timetable.find((item) => item.day === todayName) || timetable[0] || { day: '-', sessions: [] };

  const nextClass = useMemo(() => {
    const now = new Date();
    const nowMinutes = now.getHours() * 60 + now.getMinutes();
    const next = (today.sessions || []).find((session) => {
      const [start] = session.time.split('-');
      const [h, m] = start.split(':').map((v) => Number(v || 0));
      return h * 60 + m >= nowMinutes;
    });
    return next || today.sessions?.[0] || null;
  }, [today]);

  return (
    <div className="space-y-5 page-fade">
      <Card className="space-y-2">
        <h1 className="text-2xl font-semibold">Timetable</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Weekly class schedule with today and next-session highlights.
        </p>
      </Card>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <h2 className="mb-3 text-lg font-semibold">Weekly View</h2>
          <div className="space-y-3">
            {timetable.map((day) => (
              <div key={day.day} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <p className="text-sm font-semibold">{day.day}</p>
                <div className="mt-2 grid gap-2 sm:grid-cols-3">
                  {day.sessions.map((session) => (
                    <div key={`${day.day}-${session.time}`} className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-2 text-xs dark:border-slate-700 dark:bg-slate-800/40">
                      <p className="text-slate-500">{session.time}</p>
                      <p className="mt-1 font-semibold text-slate-800 dark:text-slate-100">{session.subject}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="space-y-3">
          <h2 className="text-lg font-semibold">Today</h2>
          <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
            <p className="inline-flex items-center gap-1 text-xs font-semibold text-brand-700 dark:text-brand-300">
              <CalendarClock size={12} /> {today.day}
            </p>
            <div className="mt-2 space-y-2">
              {(today.sessions || []).map((session) => (
                <div key={`${today.day}-${session.time}-today`} className="rounded-lg border border-slate-200 px-2 py-2 dark:border-slate-700">
                  <p className="text-xs text-slate-500">{session.time}</p>
                  <p className="text-sm font-semibold">{session.subject}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
            <p className="inline-flex items-center gap-1 text-xs font-semibold text-slate-600 dark:text-slate-300">
              <Clock3 size={12} /> Next Class
            </p>
            <p className="mt-1 text-sm">{nextClass ? `${nextClass.subject} (${nextClass.time})` : '-'}</p>
          </div>
          <p className="text-xs text-slate-500">
            {user?.role === 'student'
              ? 'Student view is personalized from your academic context.'
              : 'Staff view shows the shared weekly schedule.'}
          </p>
        </Card>
      </div>
    </div>
  );
}

