import { useMemo, useState } from 'react';
import Badge from '../ui/Badge';
import Card from '../ui/Card';

function badgeVariant(level) {
  if (level === 'critical') return 'danger';
  if (level === 'high') return 'warning';
  if (level === 'moderate') return 'info';
  return 'success';
}

function Stat({ label, value }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-2xl font-semibold">{value ?? 0}</p>
    </Card>
  );
}

function SelectField({ label, value, onChange, options }) {
  return (
    <label className="flex min-w-[160px] flex-col gap-1 text-sm">
      <span className="text-slate-500">{label}</span>
      <select
        className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-950"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function ReasonChips({ reasons = [] }) {
  if (!reasons.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {reasons.map((reason) => (
        <span key={reason} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-200">
          {reason}
        </span>
      ))}
    </div>
  );
}

function EvidenceGrid({ evidence = [] }) {
  if (!evidence.length) return null;
  return (
    <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
      {evidence.map((item) => (
        <div key={`${item.label}-${item.value ?? 'na'}`} className="rounded-2xl border border-slate-200 px-3 py-2 text-sm dark:border-slate-700">
          <p className="text-xs uppercase tracking-wide text-slate-500">{item.label}</p>
          <p className="mt-1 font-medium">{item.value ?? '-'}</p>
        </div>
      ))}
    </div>
  );
}

function ActionLinks({ links }) {
  return (
    <div className="mt-3 flex flex-wrap gap-2 text-sm">
      {links.map((item) => (
        <a key={`${item.href}-${item.label}`} href={item.href} className="rounded-full border border-slate-300 px-3 py-1.5 text-slate-700 transition hover:border-brand-500 hover:text-brand-700 dark:border-slate-700 dark:text-slate-200 dark:hover:border-brand-400 dark:hover:text-brand-300">
          {item.label}
        </a>
      ))}
    </div>
  );
}

function ItemShell({ title, subtitle, level, suggestedAction, reasons, evidence, links, extra = null }) {
  return (
    <div className="rounded-3xl border border-slate-200 p-4 dark:border-slate-700">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-base font-semibold">{title}</h4>
            <Badge variant={badgeVariant(level)}>{level}</Badge>
          </div>
          {subtitle ? <p className="mt-1 text-sm text-slate-500">{subtitle}</p> : null}
        </div>
      </div>
      {extra}
      <ReasonChips reasons={reasons} />
      <div className="mt-3 rounded-2xl bg-amber-50 px-3 py-2 text-sm text-amber-950 dark:bg-amber-950/20 dark:text-amber-100">
        {suggestedAction}
      </div>
      <EvidenceGrid evidence={evidence} />
      <ActionLinks links={links} />
    </div>
  );
}

export default function PredictiveOversightPanel({ overview, loading = false, error = '' }) {
  const [riskLevel, setRiskLevel] = useState('');
  const [sectionId, setSectionId] = useState('');
  const [teacherId, setTeacherId] = useState('');
  const [semesterId, setSemesterId] = useState('');

  const staffing = overview?.staffing_forecast || [];
  const sectionRisk = overview?.section_risk || [];
  const studentRisk = overview?.student_risk || [];
  const interventionQueue = overview?.intervention_queue || [];
  const summary = overview?.summary || {};

  const sectionOptions = useMemo(() => {
    const map = new Map();
    [...staffing, ...sectionRisk, ...studentRisk].forEach((item) => {
      if (item.section_id && !map.has(item.section_id)) {
        map.set(item.section_id, item.section_name || item.section_id);
      }
    });
    return [{ value: '', label: 'All Sections' }, ...Array.from(map.entries()).map(([value, label]) => ({ value, label }))];
  }, [staffing, sectionRisk, studentRisk]);

  const teacherOptions = useMemo(() => {
    const map = new Map();
    staffing.forEach((item) => {
      if (item.teacher_user_id && !map.has(item.teacher_user_id)) {
        map.set(item.teacher_user_id, item.teacher_name || item.teacher_user_id);
      }
    });
    return [{ value: '', label: 'All Teachers' }, ...Array.from(map.entries()).map(([value, label]) => ({ value, label }))];
  }, [staffing]);

  const semesterOptions = useMemo(() => {
    const map = new Map();
    [...staffing, ...sectionRisk, ...studentRisk].forEach((item) => {
      if (item.semester_id && !map.has(item.semester_id)) {
        map.set(item.semester_id, item.semester_label || item.semester_id);
      }
    });
    return [{ value: '', label: 'All Semesters' }, ...Array.from(map.entries()).map(([value, label]) => ({ value, label }))];
  }, [staffing, sectionRisk, studentRisk]);

  const filteredStaffing = useMemo(
    () =>
      staffing.filter((item) =>
        (!riskLevel || item.risk_level === riskLevel) &&
        (!sectionId || item.section_id === sectionId) &&
        (!teacherId || item.teacher_user_id === teacherId) &&
        (!semesterId || item.semester_id === semesterId)
      ),
    [riskLevel, sectionId, teacherId, semesterId, staffing]
  );

  const filteredSectionRisk = useMemo(
    () =>
      sectionRisk.filter((item) =>
        (!riskLevel || item.risk_level === riskLevel) &&
        (!sectionId || item.section_id === sectionId) &&
        (!semesterId || item.semester_id === semesterId)
      ),
    [riskLevel, sectionId, semesterId, sectionRisk]
  );

  const filteredStudentRisk = useMemo(
    () =>
      studentRisk.filter((item) =>
        (!riskLevel || item.risk_level === riskLevel) &&
        (!sectionId || item.section_id === sectionId) &&
        (!semesterId || item.semester_id === semesterId)
      ),
    [riskLevel, sectionId, semesterId, studentRisk]
  );

  return (
    <div className="space-y-4">
      <Card className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">Predictive Oversight</h2>
            <p className="text-sm text-slate-500">
              Forecast staffing pressure, section trust issues, and student academic risk before they become operational failures.
            </p>
          </div>
          {overview?.generated_at ? <p className="text-xs text-slate-500">Updated {new Date(overview.generated_at).toLocaleString()}</p> : null}
        </div>

        <div className="flex flex-wrap gap-3">
          <SelectField
            label="Risk Level"
            value={riskLevel}
            onChange={setRiskLevel}
            options={[
              { value: '', label: 'All Levels' },
              { value: 'critical', label: 'Critical' },
              { value: 'high', label: 'High' },
              { value: 'moderate', label: 'Moderate' },
              { value: 'low', label: 'Low' }
            ]}
          />
          <SelectField label="Section" value={sectionId} onChange={setSectionId} options={sectionOptions} />
          <SelectField label="Teacher" value={teacherId} onChange={setTeacherId} options={teacherOptions} />
          <SelectField label="Semester" value={semesterId} onChange={setSemesterId} options={semesterOptions} />
        </div>
      </Card>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <Stat label="Critical Staffing" value={summary.critical_staffing_items} />
        <Stat label="High Staffing" value={summary.high_staffing_items} />
        <Stat label="Critical Students" value={summary.critical_students} />
        <Stat label="Open Interventions" value={summary.open_interventions} />
        <Stat label="Sections Needing Action" value={summary.sections_requiring_attention} />
      </div>

      {loading ? (
        <Card>
          <p className="text-sm text-slate-500">Loading predictive oversight...</p>
        </Card>
      ) : null}
      {error ? (
        <Card>
          <p className="text-sm text-rose-600">{error}</p>
        </Card>
      ) : null}

      {!loading && !error ? (
        <>
          <div className="grid gap-4 xl:grid-cols-3">
            <Card className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Staffing Forecast</h3>
                <span className="text-xs text-slate-500">{filteredStaffing.length} items</span>
              </div>
              {filteredStaffing.length === 0 ? (
                <p className="text-sm text-slate-500">No staffing risks match the current filters.</p>
              ) : (
                <div className="space-y-3">
                  {filteredStaffing.slice(0, 8).map((item) => (
                    <ItemShell
                      key={`${item.section_id}-${item.teacher_user_id || 'unassigned'}`}
                      title={item.section_name}
                      subtitle={`${item.teacher_name || 'Unassigned'} | ${item.semester_label || 'No semester'} | score ${item.risk_score}`}
                      level={item.risk_level}
                      suggestedAction={item.suggested_action}
                      reasons={item.reasons}
                      evidence={item.evidence}
                      links={[
                        { href: '/course-offerings', label: 'Course Delivery' },
                        { href: '/sections', label: 'Sections' },
                        { href: '/timetable', label: 'Timetable' }
                      ]}
                    />
                  ))}
                </div>
              )}
            </Card>

            <Card className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Section Risk Summary</h3>
                <span className="text-xs text-slate-500">{filteredSectionRisk.length} items</span>
              </div>
              {filteredSectionRisk.length === 0 ? (
                <p className="text-sm text-slate-500">No section risks match the current filters.</p>
              ) : (
                <div className="space-y-3">
                  {filteredSectionRisk.slice(0, 8).map((item) => (
                    <ItemShell
                      key={item.section_id}
                      title={item.section_name}
                      subtitle={`${item.semester_label || 'No semester'} | ${item.at_risk_students} at-risk students | score ${item.risk_score}`}
                      level={item.risk_level}
                      suggestedAction={item.suggested_action}
                      reasons={item.reasons}
                      evidence={[
                        { label: 'Total students', value: item.total_students },
                        { label: 'At-risk students', value: item.at_risk_students },
                        { label: 'Timetable drift', value: item.timetable_drift },
                        { label: 'Unreleased results', value: item.unreleased_evaluation_count }
                      ]}
                      links={[
                        { href: '/sections', label: 'Sections' },
                        { href: '/attendance-records', label: 'Attendance Workspace' },
                        { href: '/evaluations', label: 'Evaluations' }
                      ]}
                    />
                  ))}
                </div>
              )}
            </Card>

            <Card className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Student Risk Queue</h3>
                <span className="text-xs text-slate-500">{filteredStudentRisk.length} items</span>
              </div>
              {interventionQueue.length ? (
                <div className="rounded-2xl border border-sky-200 bg-sky-50/70 p-3 text-sm dark:border-sky-900/40 dark:bg-sky-950/20">
                  <p className="font-semibold">Open Intervention Queue</p>
                  <p className="mt-1 text-slate-600 dark:text-slate-300">
                    {interventionQueue.length} student{interventionQueue.length === 1 ? '' : 's'} already have open follow-up records in this scope.
                  </p>
                </div>
              ) : null}
              {filteredStudentRisk.length === 0 ? (
                <p className="text-sm text-slate-500">No student risks match the current filters.</p>
              ) : (
                <div className="space-y-3">
                  {filteredStudentRisk.slice(0, 10).map((item) => (
                    <ItemShell
                      key={item.student_id}
                      title={item.student_name}
                      subtitle={`${item.roll_number || '-'} | ${item.section_name} | score ${item.risk_score}`}
                      level={item.risk_level}
                      suggestedAction={item.suggested_action}
                      reasons={item.reasons}
                      evidence={item.evidence}
                      links={[
                        { href: '/attendance-records', label: 'Attendance Workspace' },
                        { href: '/evaluations', label: 'Evaluations' },
                        { href: '/enrollments', label: 'Enrollments' }
                      ]}
                      extra={
                        item.latest_intervention ? (
                          <div className="mt-3 rounded-2xl border border-sky-200 bg-sky-50/70 px-3 py-2 text-sm dark:border-sky-900/40 dark:bg-sky-950/20">
                            <p className="font-medium">
                              Follow-up: {String(item.latest_intervention.status || 'open').replaceAll('_', ' ')}
                            </p>
                            <p className="mt-1 text-slate-600 dark:text-slate-300">{item.latest_intervention.note || 'No intervention note recorded.'}</p>
                          </div>
                        ) : null
                      }
                    />
                  ))}
                </div>
              )}
            </Card>
          </div>
        </>
      ) : null}
    </div>
  );
}
