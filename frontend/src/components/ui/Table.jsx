import React from 'react';
import { Edit3, Trash2 } from 'lucide-react';
import { cn } from '../../utils/cn';

export default function Table({
  columns,
  data,
  zebra = true,
  onEdit,
  onDelete,
  rowActions = [],
  selectable = false,
  selectedRowIds = [],
  onToggleRow,
  onToggleAllRows,
  selectionLabel = 'Select row',
  responsive = false,
  mobileBreakpoint = 'md',
  mobileCardRender,
  stickyActions = false,
  density = 'comfortable',
  onRowClick,
  rowAriaLabel = 'Open row details',
  virtualization = null,
  rowClassName,
  mobileCardClassName
}) {
  const isCompact = density === 'compact';
  const hasActions = Boolean(onEdit || onDelete || rowActions.length);
  const allSelected = selectable && data.length > 0 && data.every((row) => selectedRowIds.includes(row.id));
  const breakpoint = mobileBreakpoint === 'sm' ? 'sm' : 'md';
  const desktopVisibilityClass = responsive ? `hidden ${breakpoint}:block` : 'block';
  const mobileVisibilityClass = responsive ? `${breakpoint}:hidden` : 'hidden';
  const virtualizationConfig = {
    enabled: false,
    threshold: 120,
    rowHeight: isCompact ? 44 : 56,
    viewportHeight: 560,
    overscan: 8,
    ...(virtualization || {})
  };
  const shouldVirtualizeDesktop =
    Boolean(virtualizationConfig.enabled) && data.length >= Number(virtualizationConfig.threshold || 120);
  const [virtualScrollTop, setVirtualScrollTop] = React.useState(0);

  React.useEffect(() => {
    if (!shouldVirtualizeDesktop) return;
    setVirtualScrollTop(0);
  }, [data.length, shouldVirtualizeDesktop]);

  const rowHeight = Math.max(28, Number(virtualizationConfig.rowHeight || (isCompact ? 44 : 56)));
  const viewportHeight = Math.max(220, Number(virtualizationConfig.viewportHeight || 560));
  const overscan = Math.max(2, Number(virtualizationConfig.overscan || 8));
  const startIndex = shouldVirtualizeDesktop
    ? Math.max(0, Math.floor(virtualScrollTop / rowHeight) - overscan)
    : 0;
  const visibleCount = shouldVirtualizeDesktop
    ? Math.ceil(viewportHeight / rowHeight) + overscan * 2
    : data.length;
  const endIndex = shouldVirtualizeDesktop ? Math.min(data.length, startIndex + visibleCount) : data.length;
  const desktopRows = shouldVirtualizeDesktop ? data.slice(startIndex, endIndex) : data;
  const topSpacerHeight = shouldVirtualizeDesktop ? startIndex * rowHeight : 0;
  const bottomSpacerHeight = shouldVirtualizeDesktop ? Math.max(0, (data.length - endIndex) * rowHeight) : 0;
  const rowColSpan = columns.length + (hasActions ? 1 : 0) + (selectable ? 1 : 0);

  function isInteractiveTarget(target) {
    if (!(target instanceof Element)) return false;
    return Boolean(
      target.closest(
        'a,button,input,select,textarea,label,[role="button"],[role="menuitem"],[data-row-action]'
      )
    );
  }

  function handleRowClick(event, row) {
    if (!onRowClick) return;
    if (isInteractiveTarget(event.target)) return;
    onRowClick(row);
  }

  function handleRowKeyDown(event, row) {
    if (!onRowClick) return;
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    onRowClick(row);
  }

  function renderRowActions(row) {
    return (
      <div className={cn('flex items-center justify-end gap-2', stickyActions ? 'sticky bottom-0 rounded-xl bg-white/95 py-2 dark:bg-slate-900/95' : '')}>
        {rowActions.map((action) => {
          const hidden = typeof action.hidden === 'function' ? action.hidden(row) : Boolean(action.hidden);
          if (hidden) return null;
          const disabled = typeof action.disabled === 'function' ? action.disabled(row) : Boolean(action.disabled);
          const label = typeof action.label === 'function' ? action.label(row) : action.label;
          const rawTitle =
            typeof action.title === 'function'
              ? action.title(row)
              : action.title ?? label;
          const title =
            typeof rawTitle === 'string' || typeof rawTitle === 'number'
              ? String(rawTitle)
              : undefined;
          return (
            <button
              key={action.key}
              type="button"
              className={cn('btn-sm', action.className)}
              onClick={() => action.onClick(row)}
              title={title}
              disabled={disabled}
            >
              {label}
            </button>
          );
        })}
        {onEdit ? (
          <button type="button" className="btn-compact" onClick={() => onEdit(row)} title="Edit" aria-label="Edit">
            <Edit3 size={16} />
          </button>
        ) : null}
        {onDelete ? (
          <button
            type="button"
            className="btn-compact text-rose-600 dark:text-rose-300"
            onClick={() => onDelete(row)}
            title="Delete"
            aria-label="Delete"
          >
            <Trash2 size={16} />
          </button>
        ) : null}
      </div>
    );
  }

  function renderDefaultMobileCard(row) {
    const highPriorityColumns = columns.filter((column) => column.priority === 'high');
    const mediumPriorityColumns = columns.filter((column) => column.priority !== 'high' && column.priority !== 'low');
    const lowPriorityColumns = columns.filter((column) => column.priority === 'low');
    const primaryColumns = highPriorityColumns.length ? highPriorityColumns : columns.slice(0, 2);

    return (
      <div className={cn('space-y-3', isCompact && 'space-y-2')}>
        <div className={cn('space-y-2', isCompact && 'space-y-1.5')}>
          {primaryColumns.map((column) => (
            <div key={column.key}>
              <p className={cn('text-xs font-semibold uppercase tracking-wide text-slate-500', isCompact && 'text-[11px]')}>{column.label}</p>
              <div className={cn('mt-1 text-sm text-slate-900 dark:text-slate-100', isCompact && 'mt-0.5 text-[13px]')}>
                {column.render ? column.render(row) : row[column.key] ?? '-'}
              </div>
            </div>
          ))}
        </div>

        {mediumPriorityColumns.length ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {mediumPriorityColumns.map((column) => (
              <div key={column.key}>
                <p className={cn('text-xs font-semibold uppercase tracking-wide text-slate-500', isCompact && 'text-[11px]')}>{column.label}</p>
                <div className={cn('mt-1 text-sm text-slate-700 dark:text-slate-200', isCompact && 'mt-0.5 text-[13px]')}>
                  {column.render ? column.render(row) : row[column.key] ?? '-'}
                </div>
              </div>
            ))}
          </div>
        ) : null}

        {lowPriorityColumns.length ? (
          <div className={cn('rounded-xl border border-dashed border-slate-200 px-3 py-3 text-sm dark:border-slate-700', isCompact && 'px-2.5 py-2.5')}>
            <div className={cn('space-y-2', isCompact && 'space-y-1.5')}>
              {lowPriorityColumns.map((column) => (
                <div key={column.key}>
                  <p className={cn('text-xs font-semibold uppercase tracking-wide text-slate-500', isCompact && 'text-[11px]')}>{column.label}</p>
                  <div className={cn('mt-1 text-sm text-slate-600 dark:text-slate-300', isCompact && 'mt-0.5 text-[13px]')}>
                    {column.render ? column.render(row) : row[column.key] ?? '-'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {hasActions ? renderRowActions(row) : null}
      </div>
    );
  }

  return (
    <>
      {responsive ? (
        <div className={cn('space-y-3', mobileVisibilityClass)}>
          {data.map((row, idx) => (
            <div
              key={row.id ?? idx}
              className={cn(
                'rounded-[1.4rem] border border-slate-200 bg-white p-4 shadow-[0_16px_40px_-34px_rgba(15,23,42,0.34)] dark:border-slate-800 dark:bg-slate-900',
                isCompact && 'p-3',
                typeof mobileCardClassName === 'function' ? mobileCardClassName(row) : mobileCardClassName
              )}
            >
              {mobileCardRender ? mobileCardRender(row, { renderRowActions }) : renderDefaultMobileCard(row)}
            </div>
          ))}
          {data.length === 0 ? (
            <div className="rounded-[1.4rem] border border-dashed border-slate-300 bg-white px-4 py-8 text-center text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
              No records found.
            </div>
          ) : null}
        </div>
      ) : null}

      <div className={desktopVisibilityClass}>
        <div className="overflow-hidden rounded-[1.4rem] border border-slate-200 bg-white shadow-[0_16px_40px_-34px_rgba(15,23,42,0.34)] dark:border-slate-800 dark:bg-slate-900">
          <div
            className={cn('overflow-x-auto', shouldVirtualizeDesktop && 'overflow-y-auto')}
            style={shouldVirtualizeDesktop ? { maxHeight: `${viewportHeight}px` } : undefined}
            onScroll={shouldVirtualizeDesktop ? (event) => setVirtualScrollTop(event.currentTarget.scrollTop) : undefined}
          >
            <table className={cn('min-w-full text-sm', isCompact && 'text-[13px]')}>
              <thead className={cn('bg-slate-50 text-left dark:bg-slate-800/70', shouldVirtualizeDesktop && 'sticky top-0 z-[1]')}>
                <tr>
                  {selectable ? (
                    <th className={cn('w-12 px-4 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-300', isCompact && 'px-3 py-2')}>
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                        checked={allSelected}
                        onChange={() => onToggleAllRows?.(data)}
                        aria-label="Select all rows"
                      />
                    </th>
                  ) : null}
                  {columns.map((col) => (
                    <th key={col.key} className={cn('px-4 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-300', isCompact && 'px-3 py-2 text-[11px]')}>
                      {col.label}
                    </th>
                  ))}
                  {hasActions ? <th className={cn('px-4 py-3 text-right text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-300', isCompact && 'px-3 py-2 text-[11px]')}>Actions</th> : null}
                </tr>
              </thead>
              <tbody>
                {shouldVirtualizeDesktop && topSpacerHeight > 0 ? (
                  <tr aria-hidden="true">
                    <td colSpan={rowColSpan} style={{ padding: 0, height: `${topSpacerHeight}px`, border: 0 }} />
                  </tr>
                ) : null}
                {desktopRows.map((row, idx) => {
                  const actualIndex = shouldVirtualizeDesktop ? startIndex + idx : idx;
                  return (
                  <tr
                    key={row.id ?? idx}
                    className={cn(
                      'border-t border-slate-200 transition hover:bg-brand-50/40 dark:border-slate-800 dark:hover:bg-brand-900/15',
                      zebra && actualIndex % 2 === 1 ? 'bg-slate-50/60 dark:bg-slate-800/30' : '',
                      onRowClick && 'cursor-pointer focus-within:bg-brand-50/40',
                      typeof rowClassName === 'function' ? rowClassName(row) : rowClassName
                    )}
                    onClick={(event) => handleRowClick(event, row)}
                    onKeyDown={(event) => handleRowKeyDown(event, row)}
                    tabIndex={onRowClick ? 0 : undefined}
                    aria-label={onRowClick ? (typeof rowAriaLabel === 'function' ? rowAriaLabel(row) : rowAriaLabel) : undefined}
                  >
                    {selectable ? (
                      <td className={cn('px-4 py-3 align-top', isCompact && 'px-3 py-2')}>
                        <input
                          type="checkbox"
                          className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                          checked={selectedRowIds.includes(row.id)}
                          onChange={() => onToggleRow?.(row)}
                          aria-label={typeof selectionLabel === 'function' ? selectionLabel(row) : selectionLabel}
                        />
                      </td>
                    ) : null}
                    {columns.map((col) => (
                      <td key={col.key} className={cn('px-4 py-3 text-slate-700 dark:text-slate-100', isCompact && 'px-3 py-2')}>
                        {col.render ? col.render(row) : row[col.key] ?? '-'}
                      </td>
                    ))}
                    {hasActions ? (
                      <td className={cn('px-4 py-3', isCompact && 'px-3 py-2')}>
                        {renderRowActions(row)}
                      </td>
                    ) : null}
                  </tr>
                  );
                })}
                {shouldVirtualizeDesktop && bottomSpacerHeight > 0 ? (
                  <tr aria-hidden="true">
                    <td colSpan={rowColSpan} style={{ padding: 0, height: `${bottomSpacerHeight}px`, border: 0 }} />
                  </tr>
                ) : null}
                {data.length === 0 ? (
                  <tr>
                    <td colSpan={rowColSpan} className="px-4 py-8 text-center text-slate-500 dark:text-slate-400">
                      No records found.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}
