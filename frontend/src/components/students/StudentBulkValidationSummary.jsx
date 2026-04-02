import { AlertTriangle, CheckCircle2, FileCheck2, ShieldCheck } from 'lucide-react';

function StatCard({ label, value, tone = 'slate' }) {
  const tones = {
    slate: 'border-slate-200 bg-slate-50 text-slate-800',
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    amber: 'border-amber-200 bg-amber-50 text-amber-800',
    rose: 'border-rose-200 bg-rose-50 text-rose-800'
  };

  return (
    <div className={`rounded-2xl border p-4 ${tones[tone] || tones.slate}`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.22em] opacity-70">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function StatCell({ label, value, tone = 'slate' }) {
  const tones = {
    slate: 'border-slate-200 bg-slate-50/90 text-slate-800',
    emerald: 'border-emerald-200 bg-emerald-50/90 text-emerald-800',
    amber: 'border-amber-200 bg-amber-50/90 text-amber-800',
    rose: 'border-rose-200 bg-rose-50/90 text-rose-800'
  };

  return (
    <div className={`min-w-0 rounded-[1rem] border px-3 py-2.5 ${tones[tone] || tones.slate}`}>
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] opacity-70">{label}</p>
      <p className="mt-1 text-sm font-semibold leading-5">{value}</p>
    </div>
  );
}

export default function StudentBulkValidationSummary({
  workflow,
  file,
  preview,
  selectedSection,
  selectedGroupLabel,
  onViewIssues,
  compact = false,
  embedded = false
}) {
  const createStudents = workflow === 'create_students';
  const hasPreview = Boolean(preview);
  const summary = preview?.summary || {};
  const invalidOrBlocked = (summary.invalid_rows || 0) + (summary.blocked_rows || 0);
  const compactEmbedded = compact && embedded;

  if (compactEmbedded) {
    return (
      <div className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-2.5">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">Validation Checkpoint</p>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <h3 className="text-base font-semibold text-slate-950 dark:text-white">
                {hasPreview ? 'Validation ready' : file ? 'Ready to validate' : 'Waiting for file'}
              </h3>
              <span className="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-[11px] font-medium text-sky-700">
                Validated before import
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {hasPreview
                ? 'Review the metrics, then import only safe rows.'
                : file
                  ? createStudents
                    ? 'Preview will validate global student creation and duplicates.'
                    : 'Preview will validate duplicates and section mapping conflicts.'
                  : createStudents
                    ? 'Upload a sheet to unlock validation.'
                    : 'Choose a section and upload a sheet to unlock validation.'}
            </p>
          </div>
        </div>

        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          <StatCell
            label={createStudents ? 'Assignment Mode' : 'Selected Section'}
            value={createStudents ? 'Create globally first' : selectedSection?.label || 'Not selected'}
          />
          <StatCell
            label={createStudents ? 'Section Mapping' : 'Group Override'}
            value={createStudents ? 'Handled later in Section Mapping' : selectedGroupLabel || 'No override'}
          />
          <StatCell label="Rows Detected" value={hasPreview ? summary.total_rows : file ? 'Pending' : '0'} tone="slate" />
          <StatCell label="Valid Rows" value={hasPreview ? summary.valid_rows : '0'} tone="emerald" />
        </div>

        {hasPreview ? (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-[1rem] border border-slate-200 bg-slate-50/80 px-3 py-2.5 text-sm text-slate-700">
            <div className="flex min-w-0 items-center gap-2">
              {invalidOrBlocked ? (
                <AlertTriangle size={16} className="shrink-0 text-amber-600" />
              ) : (
                <ShieldCheck size={16} className="shrink-0 text-emerald-600" />
              )}
              <p className="min-w-0">
                {invalidOrBlocked
                  ? `${invalidOrBlocked} rows need attention and will stay blocked from import.`
                  : 'All ready rows are protected and safe to import.'}
              </p>
            </div>
            {invalidOrBlocked ? (
              <button
                type="button"
                className="shrink-0 text-xs font-semibold text-brand-700 underline underline-offset-4"
                onClick={onViewIssues}
              >
                View issues
              </button>
            ) : null}
          </div>
        ) : (
          <div className="flex items-start gap-2 rounded-[1rem] border border-slate-200 bg-slate-50/80 px-3 py-2.5 text-xs text-slate-600">
            <FileCheck2 size={15} className="mt-0.5 shrink-0 text-brand-600" />
            <p>
              {createStudents
                ? 'Preview checks row quality and duplicate student identities before any account is created.'
                : 'Preview checks row quality, duplicates, and section lock conflicts before any write.'}
            </p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`${embedded ? 'space-y-4' : 'space-y-4 rounded-[1.5rem] border border-slate-200/80 bg-white/90 p-5 shadow-[0_18px_50px_-38px_rgba(15,23,42,0.3)]'}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Validation Checkpoint</p>
          <h3 className="mt-1 text-lg font-semibold text-slate-950 dark:text-white">
            {hasPreview ? 'Validation ready' : file ? 'Ready to validate' : 'Waiting for file'}
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            {hasPreview
              ? 'Review the summary before import. Invalid rows stay protected.'
              : file
                ? createStudents
                  ? 'The next step will count rows, check duplicates, and validate global student creation.'
                  : 'The next step will count rows, check duplicates, and flag mapping conflicts.'
                : createStudents
                  ? 'Upload a sheet to unlock validation for global student creation.'
                  : 'Choose a section and upload a sheet to unlock validation.'}
          </p>
        </div>
        <div className="rounded-2xl border border-sky-200 bg-sky-50 px-3 py-2 text-xs font-medium text-sky-700">
          Validated before import
        </div>
      </div>

      <div className={`grid gap-3 ${compact ? 'grid-cols-2' : 'md:grid-cols-2 xl:grid-cols-4'}`}>
        <StatCard label={createStudents ? 'Assignment Mode' : 'Selected Section'} value={createStudents ? 'Create globally first' : selectedSection?.label || 'Not selected'} />
        <StatCard label={createStudents ? 'Section Mapping' : 'Group Override'} value={createStudents ? 'Handled later in Section Mapping' : selectedGroupLabel || 'No override'} />
        <StatCard label="Rows Detected" value={hasPreview ? summary.total_rows : file ? 'Pending' : '0'} tone="slate" />
        <StatCard label="Valid Rows" value={hasPreview ? summary.valid_rows : '0'} tone="emerald" />
      </div>

      {hasPreview ? (
        <div className={`grid gap-3 ${compact ? 'grid-cols-1' : 'md:grid-cols-2'}`}>
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900">
            <div className="flex items-start gap-3">
              <AlertTriangle size={18} className="mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-semibold">Rows needing attention</p>
                <p className="mt-1 text-sm">
                  {invalidOrBlocked} rows are invalid or blocked and will not be imported.
                </p>
                {invalidOrBlocked ? (
                  <button type="button" className="mt-3 text-sm font-semibold underline underline-offset-4" onClick={onViewIssues}>
                    View issues in preview
                  </button>
                ) : null}
              </div>
            </div>
          </div>
          {!compact ? (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-900">
              <div className="flex items-start gap-3">
                <ShieldCheck size={18} className="mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-semibold">Safe import protection</p>
                  <p className="mt-1 text-sm">
                    Only valid rows can be imported. Duplicate creation and unsafe remapping remain blocked.
                  </p>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      ) : (
        <div className={`grid gap-3 ${compact ? 'grid-cols-1' : 'md:grid-cols-2'}`}>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-slate-700">
            <div className="flex items-start gap-3">
              <FileCheck2 size={18} className="mt-0.5 shrink-0 text-brand-600" />
              <div>
                  <p className="text-sm font-semibold">Validate before import</p>
                  <p className="mt-1 text-sm">
                    {createStudents
                      ? 'Preview checks row quality and detects duplicate student identities before any account is created.'
                      : 'Preview checks row quality, detects duplicates, and identifies section-lock conflicts before any write.'}
                  </p>
              </div>
            </div>
          </div>
          {!compact ? (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-slate-700">
              <div className="flex items-start gap-3">
                <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-emerald-600" />
                <div>
                  <p className="text-sm font-semibold">Protected existing records</p>
                  <p className="mt-1 text-sm">
                    Existing student accounts and mappings remain protected from silent duplicate creation or accidental remap.
                  </p>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
