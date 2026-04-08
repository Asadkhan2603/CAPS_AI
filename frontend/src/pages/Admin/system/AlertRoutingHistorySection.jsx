import Card from '../../../components/ui/Card';

export default function AlertRoutingHistorySection({ alertRouting = {}, alertRouteHistory = [] }) {
  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Alert Routing History</p>
          <p className="text-sm text-slate-500">
            See which alerts were routed, cooled down, or resolved, and how often notification fanout actually fired.
          </p>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="Routing Enabled" value={alertRouting.enabled === false ? 'No' : 'Yes'} />
        <Metric label="Target Admins" value={alertRouting.target_user_count ?? 0} />
        <Metric label="Active Alerts" value={alertRouting.active_alert_count ?? 0} />
        <Metric label="Notifications This Refresh" value={alertRouting.notifications_created ?? 0} />
      </div>
      {alertRouteHistory.length ? (
        <div className="space-y-3">
          {alertRouteHistory.map((route) => (
            <div key={route.alert_code} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/60">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{route.alert_code}</p>
                    <span className={`rounded-full border px-2 py-0.5 text-[11px] uppercase tracking-wide ${routeStatusClass(route.is_active, route.level)}`}>
                      {route.is_active ? `Active - ${route.level || 'info'}` : 'Resolved'}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{route.message || 'No message recorded.'}</p>
                </div>
                <div className="text-right text-xs text-slate-500 dark:text-slate-400">
                  <div>Last seen: {formatDateTime(route.last_seen_at)}</div>
                  <div>Last sent: {formatDateTime(route.last_sent_at)}</div>
                  <div>Resolved: {formatDateTime(route.resolved_at)}</div>
                </div>
              </div>
              <div className="mt-3 grid gap-2 text-xs text-slate-600 dark:text-slate-300 md:grid-cols-2 xl:grid-cols-5">
                <div>Routed count: {route.routed_count ?? 0}</div>
                <div>Resolved count: {route.resolved_count ?? 0}</div>
                <div>Cooldown holds: {route.cooldown_suppressed_count ?? 0}</div>
                <div>Notifications sent: {route.notifications_sent_total ?? 0}</div>
                <div>Last outcome: {route.last_routing_outcome || '-'}</div>
              </div>
              {route.history?.length ? (
                <div className="mt-3 space-y-2">
                  {route.history.slice().reverse().slice(0, 4).map((entry, index) => (
                    <div key={`${route.alert_code}-${entry.timestamp || index}`} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-950/40">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-medium text-slate-800 dark:text-slate-100">
                          {entry.action} - {entry.level || 'info'}
                        </span>
                        <span className="text-slate-500 dark:text-slate-400">{formatDateTime(entry.timestamp)}</span>
                      </div>
                      <div className="mt-1 text-slate-600 dark:text-slate-300">{entry.message || '-'}</div>
                      <div className="mt-1 text-slate-500 dark:text-slate-400">
                        Notifications {entry.notifications_created ?? 0} - Targets {entry.target_user_count ?? 0}
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate-500">Alert routing history will appear after operational alerts are raised and routed.</p>
      )}
    </Card>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 dark:border-slate-700 dark:bg-slate-900/60">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-xl font-semibold text-slate-900 dark:text-slate-100">{value}</p>
    </div>
  );
}

function routeStatusClass(isActive, level) {
  if (!isActive) {
    return 'border-emerald-300 text-emerald-700 dark:border-emerald-700 dark:text-emerald-300';
  }
  if (level === 'critical' || level === 'high') {
    return 'border-rose-300 text-rose-700 dark:border-rose-700 dark:text-rose-300';
  }
  if (level === 'medium' || level === 'warning') {
    return 'border-amber-300 text-amber-700 dark:border-amber-700 dark:text-amber-300';
  }
  return 'border-slate-300 text-slate-600 dark:border-slate-600 dark:text-slate-300';
}

function formatDateTime(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}

