import { Edit3, Trash2 } from 'lucide-react';
import { cn } from '../../utils/cn';

export default function Table({ columns, data, zebra = true, onEdit, onDelete, rowActions = [] }) {
  const hasActions = Boolean(onEdit || onDelete || rowActions.length);

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft dark:border-slate-800 dark:bg-slate-900">
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left dark:bg-slate-800/70">
            <tr>
              {columns.map((col) => (
                <th key={col.key} className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">
                  {col.label}
                </th>
              ))}
              {hasActions ? <th className="px-4 py-3 text-right">Actions</th> : null}
            </tr>
          </thead>
          <tbody>
            {data.map((row, idx) => (
              <tr
                key={row.id ?? idx}
                className={cn(
                  'border-t border-slate-200 transition hover:bg-brand-50/40 dark:border-slate-800 dark:hover:bg-brand-900/15',
                  zebra && idx % 2 === 1 ? 'bg-slate-50/60 dark:bg-slate-800/30' : ''
                )}
              >
                {columns.map((col) => (
                  <td key={col.key} className="px-4 py-3 text-slate-700 dark:text-slate-200">
                    {col.render ? col.render(row) : row[col.key] ?? '-'}
                  </td>
                ))}
                {hasActions ? (
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      {rowActions.map((action) => (
                        <button
                          key={action.key}
                          className={cn('btn-secondary !px-2 !py-1 text-xs', action.className)}
                          onClick={() => action.onClick(row)}
                          title={action.label}
                        >
                          {action.label}
                        </button>
                      ))}
                      {onEdit ? (
                        <button className="btn-secondary !p-2" onClick={() => onEdit(row)} title="Edit">
                          <Edit3 size={16} />
                        </button>
                      ) : null}
                      {onDelete ? (
                        <button
                          className="btn-secondary !p-2 text-rose-600 dark:text-rose-300"
                          onClick={() => onDelete(row)}
                          title="Delete"
                        >
                          <Trash2 size={16} />
                        </button>
                      ) : null}
                    </div>
                  </td>
                ) : null}
              </tr>
            ))}
            {data.length === 0 ? (
              <tr>
                <td colSpan={columns.length + (hasActions ? 1 : 0)} className="px-4 py-8 text-center text-slate-500 dark:text-slate-400">
                  No records found.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
