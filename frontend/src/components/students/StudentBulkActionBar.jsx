import { ArrowRight, CheckCircle2, Eye, ShieldCheck } from 'lucide-react';

export default function StudentBulkActionBar({
  previewing,
  committing,
  canCommit,
  hasPreview,
  hasFile,
  onPreview,
  onCommit,
  compact = false,
  embedded = false,
  previewDisabledReason = '',
  commitDisabledReason = ''
}) {
  const compactEmbedded = compact && embedded;

  if (compactEmbedded) {
    return (
      <div className="rounded-[1.1rem] border border-brand-200/25 bg-gradient-to-br from-slate-950 via-slate-900 to-brand-950 px-4 py-3.5 text-white shadow-[0_20px_48px_-34px_rgba(15,23,42,0.65)]">
        <div className="flex flex-col gap-3">
          <div className="min-w-0">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/70">
              Next Action
            </div>
            <p className="mt-2 text-base font-semibold text-white">
              {hasPreview ? 'Review the preview, then import only the safe rows.' : 'Validate the file first to unlock import.'}
            </p>
            <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1.5 text-[11px] text-white/70">
              <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
                <ShieldCheck size={14} />
                Invalid rows never import silently
              </span>
              <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
                <CheckCircle2 size={14} />
                Existing records stay protected
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <button
              type="button"
              className="btn-primary !rounded-xl !px-4 !py-2.5 text-sm sm:min-w-[180px]"
              onClick={onPreview}
              disabled={previewing || !hasFile}
            >
              <Eye size={16} />
              {previewing ? 'Validating...' : hasPreview ? 'Validate Again' : 'Validate File'}
            </button>
            <button
              type="button"
              className={`${hasPreview && canCommit ? 'btn-primary' : 'btn-secondary'} !rounded-xl !px-4 !py-2.5 text-sm sm:min-w-[180px] disabled:cursor-not-allowed disabled:opacity-60`}
              onClick={onCommit}
              disabled={!canCommit || committing}
            >
              {committing ? 'Importing...' : 'Import Safe Rows'}
              {!committing ? <ArrowRight size={16} /> : null}
            </button>
          </div>
        </div>
        {previewDisabledReason || commitDisabledReason ? (
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-white/65">
            {previewDisabledReason ? <p>{previewDisabledReason}</p> : null}
            {commitDisabledReason ? <p>{commitDisabledReason}</p> : null}
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div
      className={`${
        embedded
          ? 'rounded-[1.35rem] bg-gradient-to-br from-slate-950 via-slate-900 to-brand-950 p-4 text-white'
          : `rounded-[1.5rem] border p-4 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.55)] ${
              compact ? 'border-brand-200/80 bg-gradient-to-br from-slate-950 via-slate-900 to-brand-950 text-white' : 'border-slate-200/80 bg-slate-950 text-white'
            }`
      }`}
    >
      <div className={`flex flex-col gap-4 ${compact ? '' : 'xl:flex-row xl:items-center xl:justify-between'}`}>
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-white/70">
            Next Action
          </div>
          <h3 className="text-lg font-semibold">
            {hasPreview ? 'Review the preview, then import only the safe rows' : 'Validate the file first to unlock import'}
          </h3>
          <div className="flex flex-wrap gap-3 text-sm text-white/75">
            <span className="inline-flex items-center gap-2">
              <ShieldCheck size={16} />
              Invalid rows never import silently
            </span>
            <span className="inline-flex items-center gap-2">
              <CheckCircle2 size={16} />
              Existing records stay protected
            </span>
          </div>
        </div>

        <div className={`flex flex-col gap-3 ${compact ? '' : 'sm:flex-row'}`}>
          <button type="button" className={`btn-primary !rounded-2xl !px-5 !py-3 ${compact ? 'w-full' : ''}`} onClick={onPreview} disabled={previewing || !hasFile}>
            <Eye size={18} />
            {previewing ? 'Validating...' : hasPreview ? 'Validate Again' : 'Validate File'}
          </button>
          <button
            type="button"
            className={`${hasPreview && canCommit ? 'btn-primary' : 'btn-secondary'} !rounded-2xl !px-5 !py-3 disabled:cursor-not-allowed disabled:opacity-60 ${compact ? 'w-full' : ''}`}
            onClick={onCommit}
            disabled={!canCommit || committing}
          >
            {committing ? 'Importing...' : 'Import Safe Rows'}
            {!committing ? <ArrowRight size={18} /> : null}
          </button>
        </div>
      </div>
      {previewDisabledReason || commitDisabledReason ? (
        <div className="mt-3 space-y-1 text-xs text-white/70">
          {previewDisabledReason ? <p>{previewDisabledReason}</p> : null}
          {commitDisabledReason ? <p>{commitDisabledReason}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
