import { UploadCloud } from 'lucide-react';
import { useRef, useState } from 'react';
import { cn } from '../../utils/cn';

export default function FileUpload({ onFileSelect, progress = 0, status = 'idle', accept = '.pdf,.docx,.txt,.md' }) {
  const [drag, setDrag] = useState(false);
  const inputRef = useRef(null);
  const progressWidthClass =
    progress >= 100
      ? 'w-full'
      : progress >= 90
        ? 'w-11/12'
        : progress >= 80
          ? 'w-10/12'
          : progress >= 70
            ? 'w-9/12'
            : progress >= 60
              ? 'w-8/12'
              : progress >= 50
                ? 'w-7/12'
                : progress >= 40
                  ? 'w-6/12'
                  : progress >= 30
                    ? 'w-5/12'
                    : progress >= 20
                      ? 'w-4/12'
                      : progress >= 10
                        ? 'w-3/12'
                        : progress > 0
                          ? 'w-2/12'
                          : 'w-0';

  function pickFile(file) {
    if (file && onFileSelect) {
      onFileSelect(file);
    }
  }

  return (
    <div
      className={cn(
        'rounded-2xl border-2 border-dashed p-6 text-center transition',
        drag ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20' : 'border-slate-300 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/30'
      )}
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrag(false);
        pickFile(e.dataTransfer.files?.[0]);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept={accept}
        onChange={(e) => pickFile(e.target.files?.[0])}
      />
      <UploadCloud className="mx-auto mb-2 text-brand-600" />
      <p className="text-sm text-slate-600 dark:text-slate-300">Drag & drop your file, or click to browse.</p>
      <button type="button" className="btn-primary mt-3" onClick={() => inputRef.current?.click()}>
        Choose File
      </button>
      {status !== 'idle' ? (
        <div className="mt-4">
          <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
            <div className={`h-full bg-brand-600 transition-all ${progressWidthClass}`} />
          </div>
          <p className="mt-1 text-xs text-slate-500">{status === 'uploading' ? `Uploading ${progress}%` : status}</p>
        </div>
      ) : null}
    </div>
  );
}
