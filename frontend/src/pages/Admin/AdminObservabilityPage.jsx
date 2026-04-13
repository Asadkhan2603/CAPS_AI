import React from 'react';
import { Link } from 'react-router-dom';
import Badge from '../../components/ui/Badge';
import Card from '../../components/ui/Card';
import { useToast } from '../../hooks/useToast';
import ClubObservabilityTrendSection from './system/ClubObservabilityTrendSection';
import SystemHealthHistoryCharts from './system/SystemHealthHistoryCharts';
import { AUTO_REFRESH_MS, useAdminSystemHealth } from './system/useAdminSystemHealth';
import { buildObservabilityDiagnosticsModel } from './system/adminOperationsViewModel';

export default function AdminObservabilityPage() {
  const { pushToast } = useToast();
  const {
    clubsObservability,
    clearSnapshots,
    data,
    error,
    exportSnapshots,
    historyData,
    isAutoRefresh,
    isRefreshing,
    loadHealth,
    localHistoryData,
    localSnapshots,
    persistedHistoryData,
    setIsAutoRefresh,
    snapshotStore,
  } = useAdminSystemHealth({ pushToast });

  const model = buildObservabilityDiagnosticsModel({
    data,
    historyData,
    persistedHistoryData,
    localHistoryData,
    localSnapshots,
    snapshotStore,
  });

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-3">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div className="space-y-2">
            <div>
              <h1 className="text-2xl font-semibold">Observability</h1>
              <p className="text-sm text-slate-500">
                Deep diagnostics for history, endpoint breakdowns, club pressure trends, and snapshot retention.
              </p>
            </div>
            <Link className="btn-secondary w-fit" to="/admin/system">
              Back to system overview
            </Link>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => void loadHealth({ silent: false, forceRefresh: true })}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              {isRefreshing ? 'Refreshing...' : 'Refresh Now'}
            </button>
            <button
              type="button"
              onClick={() => setIsAutoRefresh((value) => !value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Auto Refresh: {isAutoRefresh ? 'On' : 'Off'}
            </button>
            <button
              type="button"
              onClick={() => void exportSnapshots()}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Export JSON
            </button>
            <button
              type="button"
              onClick={clearSnapshots}
              className="rounded-lg border border-rose-300 px-3 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50 dark:border-rose-800 dark:text-rose-200 dark:hover:bg-rose-950/40"
            >
              Clear Local History
            </button>
          </div>
        </div>
        <div className="grid gap-2 text-xs text-slate-500 md:grid-cols-4">
          <div>Auto refresh cadence: {AUTO_REFRESH_MS / 1000}s</div>
          <div>Live samples: {historyData.length}</div>
          <div>Persisted snapshots: {persistedHistoryData.length}</div>
          <div>Local snapshots retained: {localSnapshots.length}</div>
        </div>
      </Card>

      {error ? (
        <Card>
          <p className="text-sm text-rose-600">{error}</p>
        </Card>
      ) : null}

      <SectionCard
        title="Diagnostics Overview"
        description="Quick context for how much telemetry is available before diving into charts and details."
      >
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {model.summaryCards.map((card) => (
            <MetricCard key={card.label} {...card} />
          ))}
        </div>
      </SectionCard>

      <SectionCard
        title="Historical Trends"
        description="Trend charts for live, persisted, and locally retained health snapshots."
      >
        <SystemHealthHistoryCharts
          historyData={historyData}
          persistedHistoryData={persistedHistoryData}
          localHistoryData={localHistoryData}
        />
      </SectionCard>

      <SectionCard
        title="Clubs Diagnostics"
        description="Longer-horizon clubs pressure trends and retained pressure windows."
      >
        <ClubObservabilityTrendSection clubsObservability={clubsObservability} />
      </SectionCard>

      <SectionCard
        title="Endpoint Diagnostics"
        description="Path-level traffic breakdowns and the recent endpoint mix across general and club traffic."
      >
        <div className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {model.endpointSummaryCards.map((card) => (
              <MetricCard key={card.label} {...card} />
            ))}
          </div>
          <div className="grid gap-3 xl:grid-cols-2">
            <PathListCard
              title="Top Paths (15m)"
              rows={model.topPaths}
              emptyMessage="No recent endpoint activity is available in the latest health payload."
            />
            <PathListCard
              title="Clubs Workspace Paths (15m)"
              rows={model.clubTopPaths}
              emptyMessage="No recent clubs workspace path activity is available in the latest health payload."
            />
          </div>
        </div>
      </SectionCard>

      <SectionCard
        title="Snapshot Retention"
        description="Retention health, prune behavior, and browser-retained snapshot context."
      >
        <div className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {model.snapshotCards.map((card) => (
              <MetricCard key={card.label} {...card} />
            ))}
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300">
            Export the current telemetry set for offline analysis or clear browser-retained snapshots when local diagnostics drift from the server history.
          </div>
        </div>
      </SectionCard>

      <SectionCard
        title="Scheduler Detail"
        description="Operational scheduler metadata and dispatch state from the current health payload."
      >
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {model.schedulerRows.map((row) => (
            <CompactStat key={row.label} label={row.label} value={row.value} />
          ))}
        </div>
      </SectionCard>
    </div>
  );
}

function SectionCard({ title, description, children }) {
  return (
    <Card className="space-y-3">
      <div>
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
        <p className="text-sm text-slate-500">{description}</p>
      </div>
      {children}
    </Card>
  );
}

function MetricCard({ label, value, detail, tone = 'default' }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 dark:border-slate-700 dark:bg-slate-900/60">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
        {tone !== 'default' ? <Badge variant={tone}>{String(value)}</Badge> : null}
      </div>
      {tone === 'default' ? <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-100">{value}</p> : null}
      <p className="mt-2 text-sm text-slate-500">{detail}</p>
    </div>
  );
}

function CompactStat({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-900/60">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">{value}</p>
    </div>
  );
}

function PathListCard({ title, rows, emptyMessage }) {
  return (
    <Card className="space-y-3">
      <p className="text-sm font-medium text-slate-600 dark:text-slate-300">{title}</p>
      {rows?.length ? (
        <div className="space-y-2">
          {rows.map((row) => (
            <div
              key={row.path}
              className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm dark:border-slate-700 dark:bg-slate-900/60"
            >
              <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
                <p className="font-medium text-slate-900 dark:text-slate-100">{row.path}</p>
                <p className="text-xs text-slate-500">
                  requests={row.requests ?? 0} | 5xx={row.server_errors ?? 0} | slow={row.slow_requests ?? 0}
                </p>
              </div>
              <p className="text-xs text-slate-500">
                avg={row.avg_duration_ms ?? '-'} ms | p95={row.p95_duration_ms ?? '-'} ms
              </p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate-500">{emptyMessage}</p>
      )}
    </Card>
  );
}
