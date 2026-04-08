const SLOW_TRACE_MS = 1200;
const SLOW_LOAD_MS = 1800;
const WARNING_LOAD_MS = 1000;

function percentile(values, percentileValue) {
  if (!values.length) return null;
  const ordered = [...values].sort((left, right) => left - right);
  const index = Math.max(0, Math.min(ordered.length - 1, Math.ceil(ordered.length * percentileValue) - 1));
  return ordered[index];
}

function shortEndpointLabel(url) {
  if (!url) return '-';
  return String(url)
    .replace(/^.*\/api\/v1\//, '')
    .replace(/\?.*$/, '');
}

export function buildClubPerformanceMonitor({
  selectedClub,
  workspacePerformance,
  members = [],
  applications = [],
  events = [],
  eventRegistrations = []
}) {
  if (!selectedClub) return null;

  const traces = Array.isArray(workspacePerformance?.traces) ? workspacePerformance.traces : [];
  const durations = traces
    .map((entry) => Number(entry?.durationMs))
    .filter((value) => Number.isFinite(value) && value >= 0);
  const slowTraces = traces.filter((entry) => Number(entry?.durationMs) >= SLOW_TRACE_MS);
  const errorTraces = traces.filter((entry) => Number(entry?.status) >= 500 || Number(entry?.status) === 0);
  const p95DurationMs = percentile(durations, 0.95);
  const averageDurationMs = durations.length
    ? Math.round(durations.reduce((total, value) => total + value, 0) / durations.length)
    : null;
  const slowestTrace = traces.reduce((current, entry) => {
    if (!current) return entry;
    return Number(entry?.durationMs || 0) > Number(current?.durationMs || 0) ? entry : current;
  }, null);

  const selectedClubLoad = workspacePerformance?.selectedClub || null;
  const directoryLoad = workspacePerformance?.directory || null;
  const archivedEvents = events.filter((eventItem) => eventItem.status === 'archived').length;
  const datasetWeight = members.length + applications.length + events.length + eventRegistrations.length;

  let status = 'healthy';
  let statusLabel = 'Healthy';
  if (selectedClubLoad?.status === 'error' || directoryLoad?.status === 'error' || errorTraces.length >= 2) {
    status = 'critical';
    statusLabel = 'Critical';
  } else if (
    selectedClubLoad?.status === 'partial' ||
    Number(selectedClubLoad?.durationMs) >= SLOW_LOAD_MS ||
    Number(directoryLoad?.durationMs) >= SLOW_LOAD_MS ||
    Number(p95DurationMs) >= SLOW_TRACE_MS ||
    slowTraces.length >= 3
  ) {
    status = 'watch';
    statusLabel = 'Watch';
  } else if (
    Number(selectedClubLoad?.durationMs) >= WARNING_LOAD_MS ||
    Number(directoryLoad?.durationMs) >= WARNING_LOAD_MS
  ) {
    status = 'watch';
    statusLabel = 'Watch';
  }

  const recommendations = [];
  if (archivedEvents >= 12) {
    recommendations.push('Use Archive View for older event history instead of mixing it into live event work.');
  }
  if (Number(selectedClubLoad?.durationMs) >= SLOW_LOAD_MS || Number(p95DurationMs) >= SLOW_TRACE_MS) {
    recommendations.push('Start from analytics and exports first, then open drilldowns only for events that still need intervention.');
  }
  if (errorTraces.length) {
    recommendations.push('Use the retry panels to recover only the failing workspace slice and keep the rest of the club context intact.');
  }
  if (!recommendations.length) {
    recommendations.push('Current club load is stable. Keep using archive filters and saved queue views as the dataset grows.');
  }

  return {
    status,
    statusLabel,
    updatedAt: workspacePerformance?.updatedAt || selectedClubLoad?.loadedAt || directoryLoad?.loadedAt || null,
    selectedClubLoad,
    directoryLoad,
    datasetWeight,
    archivedEvents,
    p95DurationMs,
    averageDurationMs,
    slowTraceCount: slowTraces.length,
    errorTraceCount: errorTraces.length,
    recommendations,
    recentTraces: traces.slice(0, 6).map((entry) => ({
      ...entry,
      endpointLabel: shortEndpointLabel(entry?.url)
    })),
    slowestTrace: slowestTrace
      ? {
          ...slowestTrace,
          endpointLabel: shortEndpointLabel(slowestTrace?.url)
        }
      : null
  };
}
