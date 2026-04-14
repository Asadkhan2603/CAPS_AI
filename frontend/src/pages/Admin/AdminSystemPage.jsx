import React from 'react';
import { Link } from 'react-router-dom';
import Badge from '../../components/ui/Badge';
import Card from '../../components/ui/Card';
import EmptyState from '../../components/ui/EmptyState';
import InlineErrorState from '../../components/ui/InlineErrorState';
import PageLoader from '../../components/ui/PageLoader';
import { useToast } from '../../hooks/useToast';
import AlertRoutingHistorySection from './system/AlertRoutingHistorySection';
import { AUTO_REFRESH_MS, useAdminSystemHealth } from './system/useAdminSystemHealth';
import { formatDateTime, statusClasses } from './system/adminSystemFormatters';
import { buildSystemOverviewModel, getAlertLevelMeta } from './system/adminOperationsViewModel';

export default function AdminSystemPage() {
  const { pushToast } = useToast();
  const {
    aiMetrics,
    alertRouteHistory,
    alertRouting,
    clubsMetrics,
    data,
    error,
    isAutoRefresh,
    isRefreshing,
    loadHealth,
    localSnapshots,
    setIsAutoRefresh,
    snapshotStore,
  } = useAdminSystemHealth({ pushToast });

  const model = buildSystemOverviewModel({
    data,
    aiMetrics,
    clubsMetrics,
    snapshotStore,
  });
  const initialLoading = !data && !error && isRefreshing;

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-3">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div className="space-y-2">
            <div>
              <h1 className="text-2xl font-semibold">System Health</h1>
              <p className="text-sm text-slate-500">
                Operator overview for platform health, live incidents, traffic pressure, and storage posture.
              </p>
            </div>
            <Link className="btn-secondary w-fit" to="/admin/observability">
              Open deep observability
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
          </div>
        </div>
        <div className="grid gap-2 text-xs text-slate-500 md:grid-cols-4">
          <div>Auto refresh cadence: {AUTO_REFRESH_MS / 1000}s</div>
          <div>Latest payload: {formatDateTime(data?.timestamp)}</div>
          <div>Persisted snapshots: {data?.snapshot_history?.length ?? 0}</div>
          <div>Local snapshots retained: {localSnapshots.length}</div>
        </div>
      </Card>

      {error ? (
        <InlineErrorState
          title="System overview unavailable"
          description={error}
          onRetry={() => void loadHealth({ silent: false, forceRefresh: true })}
        />
      ) : null}

      {initialLoading ? <PageLoader compact label="Loading system overview..." /> : null}

      <SectionCard
        title="Health Summary"
        description="Core availability and trust signals operators should see first."
      >
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {model.healthCards.map((card) => (
            <MetricCard key={card.label} {...card} />
          ))}
        </div>
      </SectionCard>

      <SectionCard
        title="Active Alerts"
        description="Current incidents that need review or follow-up."
      >
        {data?.alerts?.length ? (
          <div className="space-y-2">
            {data.alerts.map((alert) => (
              <AlertRow key={alert.code} alert={alert} />
            ))}
          </div>
        ) : (
          <EmptyState compact title="No active operational alerts" description="Current health payload shows no active incidents that need operator follow-up." />
        )}
      </SectionCard>

      <SectionCard
        title="Traffic and Throughput"
        description="Recent demand, latency, and error pressure across general and club-specific traffic."
      >
        {model.hasRequestMetrics ? (
          <div className="space-y-3">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {model.trafficCards.map((card) => (
                <MetricCard key={card.label} {...card} />
              ))}
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {model.clubsTrafficCards.map((card) => (
                <MetricCard key={card.label} {...card} />
              ))}
            </div>
          </div>
        ) : (
          <PanelFallback message="No request metrics available in the latest health payload." />
        )}
      </SectionCard>

      <SectionCard
        title="AI and Scheduler Capacity"
        description="Queue pressure, fallback behavior, and scheduled delivery readiness."
      >
        {model.hasAiMetrics ? (
          <div className="space-y-3">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {model.capacityCards.map((card) => (
                <CapacityCard key={card.label} {...card} />
              ))}
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {model.schedulerCards.map((card) => (
                <MetricCard key={card.label} {...card} />
              ))}
            </div>
          </div>
        ) : (
          <PanelFallback message="No AI capacity metrics are available in the latest health payload." />
        )}
      </SectionCard>

      <SectionCard
        title="Data and Storage Posture"
        description="Snapshot retention health and tracked collection counts."
      >
        <div className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {model.storageCards.map((card) => (
              <MetricCard key={card.label} {...card} />
            ))}
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {model.storageRows.map((row) => (
              <CompactStat key={row.label} label={row.label} value={row.value} />
            ))}
          </div>
          {model.hasCollectionRows ? (
            <div className="overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-700">
              <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
                <thead className="bg-slate-50 dark:bg-slate-900/60">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">Collection</th>
                    <th className="px-4 py-3 text-right font-medium text-slate-600 dark:text-slate-300">Count</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                  {model.collectionRows.map((row) => (
                    <tr key={row.name}>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{row.name}</td>
                      <td className="px-4 py-3 text-right font-medium text-slate-900 dark:text-slate-100">{row.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <PanelFallback message="Collection counts are not available in the latest health payload." />
          )}
        </div>
      </SectionCard>

      <SectionCard
        title="Recent Anomalies and Slow Queries"
        description="Recent anomalies that help triage incidents without leaving the overview."
      >
        <div className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {model.anomalyCards.map((card) => (
              <MetricCard key={card.label} {...card} />
            ))}
          </div>
          {data?.slow_query_logs?.length ? (
            <div className="space-y-2">
              {data.slow_query_logs.map((row, index) => (
                <div
                  key={`${row.created_at || 'slow-query'}-${index}`}
                  className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm dark:border-slate-700 dark:bg-slate-900/60"
                >
                  <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
                    <p className="font-medium text-slate-900 dark:text-slate-100">{row.resource || 'unknown resource'}</p>
                    <p className="text-xs text-slate-500">{formatDateTime(row.created_at)}</p>
                  </div>
                  <p className="text-sm text-slate-600 dark:text-slate-300">{row.detail || 'No additional detail recorded.'}</p>
                </div>
              ))}
            </div>
          ) : (
            <PanelFallback message="No slow-query logs were recorded in the last 24 hours." />
          )}
        </div>
      </SectionCard>

      <AlertRoutingHistorySection alertRouting={alertRouting} alertRouteHistory={alertRouteHistory} />
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

function CapacityCard({ label, value, status, detail }) {
  return (
    <div className={`rounded-2xl border px-4 py-4 ${statusClasses(status)}`}>
      <p className="text-xs uppercase tracking-wide opacity-80">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
      <p className="mt-1 text-xs uppercase tracking-wide">{status}</p>
      <p className="mt-2 text-sm opacity-80">{detail}</p>
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

function AlertRow({ alert }) {
  const meta = getAlertLevelMeta(alert?.level);

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm dark:border-slate-700 dark:bg-slate-900/60">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium text-slate-900 dark:text-slate-100">{alert?.code || 'unnamed_alert'}</p>
          <Badge variant={meta.variant}>{meta.label}</Badge>
        </div>
      </div>
      <p className="mt-2 text-slate-600 dark:text-slate-300">{alert?.message || 'No alert message provided.'}</p>
    </div>
  );
}

function PanelFallback({ message }) {
  return <EmptyState compact title="No section data available" description={message} />;
}
