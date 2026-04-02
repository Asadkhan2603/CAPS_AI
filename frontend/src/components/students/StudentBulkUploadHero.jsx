import { useMemo, useRef, useState } from 'react';
import { FileSpreadsheet, RefreshCcw, Trash2, UploadCloud } from 'lucide-react';
import { cn } from '../../utils/cn';

function formatFileSize(size = 0) {
  if (!size) return '0 KB';
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = size;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value >= 10 || index === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[index]}`;
}

export default function StudentBulkUploadHero({
  workflow,
  file,
  onFileSelect,
  onRemoveFile,
  disabled = false,
  onRequestDestination
}) {
  const inputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);

  const requiredColumns = useMemo(
    () =>
      workflow === 'create_students'
        ? ['full_name', 'email', 'roll_number', 'enrollment_number', 'phone']
        : ['student_id', 'email or enrollment_number', 'group (optional)'],
    [workflow]
  );

  function handleFiles(fileList) {
    const nextFile = fileList?.[0] || null;
    if (nextFile) {
      onFileSelect?.(nextFile);
    }
  }

  return (
    <div className="space-y-3.5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">File Upload</p>
          <h3 className="mt-1 text-lg font-semibold text-slate-950 dark:text-white">Upload the student sheet</h3>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">
            Drop a CSV or XLSX file, then validate it before any rows are written.
          </p>
        </div>
        <div className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700">
          Supports CSV and XLSX
        </div>
      </div>

      <div className="grid gap-3 xl:grid-cols-[minmax(0,1.45fr)_minmax(220px,0.72fr)_minmax(220px,0.76fr)] xl:items-stretch">
        <label
          className={cn(
            'group relative flex min-h-[164px] cursor-pointer flex-col items-center justify-center overflow-hidden rounded-[1.35rem] border border-dashed px-5 py-4 text-center transition-all',
            dragActive
              ? 'border-brand-400 bg-brand-50 shadow-[0_24px_56px_-38px_rgba(79,70,229,0.35)]'
              : 'border-brand-200/70 bg-gradient-to-br from-slate-50 via-white to-brand-50/45 hover:border-brand-300 hover:shadow-[0_24px_60px_-42px_rgba(79,70,229,0.32)]',
            disabled && 'cursor-not-allowed border-slate-200 bg-slate-50 opacity-90 hover:border-slate-200 hover:shadow-none'
          )}
          onDragOver={(event) => {
            if (disabled) return;
            event.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(event) => {
            if (disabled) return;
            event.preventDefault();
            setDragActive(false);
            handleFiles(event.dataTransfer.files);
          }}
        >
          <div className="absolute inset-x-12 top-0 h-16 rounded-b-[999px] bg-gradient-to-b from-brand-100/55 to-transparent blur-2xl" />
          <div className="relative flex h-12 w-12 items-center justify-center rounded-[1rem] border border-brand-200 bg-white text-brand-600 shadow-[0_18px_36px_-28px_rgba(79,70,229,0.5)]">
            {file ? <FileSpreadsheet size={22} /> : <UploadCloud size={22} />}
          </div>

          <div className="relative mt-3 space-y-1.5">
            <p className="text-base font-semibold text-slate-900">
              {disabled ? 'Select a section to unlock upload' : file ? 'File ready for validation' : 'Drag and drop CSV/XLSX here'}
            </p>
            <p className="mx-auto max-w-xl text-sm text-slate-500">
              {disabled
                ? 'Choose the import destination first. Upload stays locked until a section is selected.'
                : file
                  ? 'Validate next to check rows, duplicates, and mapping conflicts.'
                  : workflow === 'create_students'
                    ? 'Upload the student sheet to create global student records first.'
                    : 'Upload the student sheet after selecting the destination.'}
            </p>
          </div>

          <div className="relative mt-3 flex flex-wrap items-center justify-center gap-2.5">
            {disabled ? (
              <button
                type="button"
                className="btn-secondary !rounded-full !px-3.5 !py-2 text-sm"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  onRequestDestination?.();
                }}
              >
                Choose section first
              </button>
            ) : (
              <>
                <span className="rounded-full border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-600">
                  Browse file
                </span>
                <span className="text-[11px] uppercase tracking-[0.24em] text-slate-400">or drop here</span>
              </>
            )}
          </div>

          <input
            ref={inputRef}
            type="file"
            accept=".csv,.xlsx"
            className="hidden"
            disabled={disabled}
            onChange={(event) => handleFiles(event.target.files)}
          />
        </label>

        <div className="rounded-[1.15rem] border border-slate-200/70 bg-slate-50/55 px-3.5 py-3">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Required Columns</p>
              <p className="mt-1 text-xs text-slate-500">Use the template to keep structure consistent.</p>
            </div>
            {file ? (
              <div className="rounded-full border border-brand-200 bg-brand-50 px-2.5 py-1 text-[11px] font-semibold text-brand-700">
                Ready
              </div>
            ) : null}
          </div>

          <div className="mt-3 flex flex-wrap gap-1.5">
            {requiredColumns.map((column) => (
              <span
                key={column}
                className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-700"
              >
                {column}
              </span>
            ))}
          </div>

          <p className="mt-3 text-xs leading-5 text-slate-500">
            Keep headers unchanged for cleaner validation and fewer column-mapping errors.
          </p>
        </div>

        <div className="rounded-[1.15rem] border border-slate-200/70 bg-white/80 px-3.5 py-3 shadow-[0_18px_44px_-38px_rgba(15,23,42,0.28)]">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">File Status</p>
              <p className="mt-1 text-xs text-slate-500">Validation unlocks after a supported file is attached.</p>
            </div>
            <div className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
              {file ? 'Attached' : 'Waiting'}
            </div>
          </div>

          {file ? (
            <div className="mt-3 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-slate-900">{file.name}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {formatFileSize(file.size)} | {workflow === 'create_students' ? 'Create students' : 'Map existing'}
                  </p>
                </div>
                <FileSpreadsheet size={18} className="mt-0.5 shrink-0 text-brand-600" />
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-secondary !rounded-xl !px-3 !py-1.5 text-xs"
                  onClick={() => inputRef.current?.click()}
                >
                  <RefreshCcw size={13} />
                  Replace
                </button>
                <button
                  type="button"
                  className="btn-secondary !rounded-xl !px-3 !py-1.5 text-xs !text-rose-600"
                  onClick={() => {
                    if (inputRef.current) inputRef.current.value = '';
                    onRemoveFile?.();
                  }}
                >
                  <Trash2 size={13} />
                  Remove
                </button>
              </div>
            </div>
          ) : (
            <div className="mt-3 space-y-1.5">
              <p className="text-sm font-medium text-slate-700">No file selected yet</p>
              <p className="text-xs leading-5 text-slate-500">
                Upload a file to unlock validation, row counts, and duplicate checks.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
