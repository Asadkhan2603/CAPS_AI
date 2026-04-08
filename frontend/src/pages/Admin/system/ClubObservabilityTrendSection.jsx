import { Area, AreaChart, CartesianGrid, Tooltip, XAxis, YAxis } from 'recharts';
import Card from '../../../components/ui/Card';
import SafeResponsiveContainer from '../../../components/charts/SafeResponsiveContainer';
import { formatDateTime, formatDuration } from './adminSystemFormatters';

export default function ClubObservabilityTrendSection({ clubsObservability }) {
  const summary = clubsObservability?.summary || {};
  const hourly24h = clubsObservability?.hourly24h || [];
  const daily14d = clubsObservability?.daily14d || [];
  const recentPressureWindows = clubsObservability?.recentPressureWindows || [];

  return (
    <div className="space-y-3">
      <Card className="space-y-2">
        <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Clubs Pressure Trends</p>
            <p className="text-xs text-slate-500">
              Hourly and daily club workspace pressure history for longer-horizon admin observability.
            </p>
          </div>
          <div className="text-xs text-slate-500">
            Retention: {summary.retention_days ?? '-'} days
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          <TrendMetric label="Latest Pressure" value={(summary.latest_pressure_level || 'ok').toUpperCase()} />
          <TrendMetric label="Pressure Windows (24h)" value={summary.pressure_windows_24h ?? 0} />
          <TrendMetric label="Critical Windows (24h)" value={summary.critical_windows_24h ?? 0} />
          <TrendMetric label="Peak Requests (24h)" value={summary.peak_requests_24h ?? 0} />
          <TrendMetric label="Peak P95 (24h)" value={formatDuration(summary.peak_p95_duration_ms_24h)} />
          <TrendMetric label="Pressure Days (14d)" value={summary.pressure_days_14d ?? 0} />
        </div>
      </Card>

      <div className="grid gap-3 xl:grid-cols-2">
        <TrendChartCard title="Club Requests Peak By Hour (24h)" empty={!hourly24h.length}>
          <SafeResponsiveContainer>
            <AreaChart data={hourly24h}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis allowDecimals={false} width={42} />
              <Tooltip />
              <Area type="monotone" dataKey="clubRequestsPeak" stroke="#2563eb" fill="#93c5fd" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </SafeResponsiveContainer>
        </TrendChartCard>
        <TrendChartCard title="Club P95 Peak By Hour (24h)" empty={!hourly24h.length}>
          <SafeResponsiveContainer>
            <AreaChart data={hourly24h}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis width={42} />
              <Tooltip formatter={(value) => [formatDuration(value), 'Club P95 Peak']} />
              <Area type="monotone" dataKey="clubP95Peak" stroke="#d97706" fill="#fcd34d" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </SafeResponsiveContainer>
        </TrendChartCard>
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        <TrendChartCard title="Club Requests Peak By Day (14d)" empty={!daily14d.length}>
          <SafeResponsiveContainer>
            <AreaChart data={daily14d}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis allowDecimals={false} width={42} />
              <Tooltip />
              <Area type="monotone" dataKey="clubRequestsPeak" stroke="#0f766e" fill="#5eead4" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </SafeResponsiveContainer>
        </TrendChartCard>
        <TrendChartCard title="Club Pressure Windows By Day (14d)" empty={!daily14d.length}>
          <SafeResponsiveContainer>
            <AreaChart data={daily14d}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis allowDecimals={false} width={42} />
              <Tooltip />
              <Area type="monotone" dataKey="pressureSignal" stroke="#be123c" fill="#fda4af" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </SafeResponsiveContainer>
        </TrendChartCard>
      </div>

      <Card className="space-y-2">
        <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Recent Club Pressure Windows</p>
        {recentPressureWindows.length ? (
          <div className="space-y-2">
            {recentPressureWindows.map((window) => (
              <div key={window.bucketStart} className="rounded-xl border border-slate-200 px-3 py-2 text-xs dark:border-slate-700">
                <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
                  <div className="font-medium">
                    {formatDateTime(window.bucketStart)} | {window.pressureLevel.toUpperCase()}
                  </div>
                  <div className="text-slate-500">
                    requests peak {window.clubRequestsPeak} | p95 peak {formatDuration(window.clubP95Peak)}
                  </div>
                </div>
                <div className="text-slate-600 dark:text-slate-300">
                  slow total {window.clubSlowTotal} | 5xx total {window.clubServerErrorsTotal}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-emerald-600 dark:text-emerald-400">No club pressure windows recorded in the retained trend history.</p>
        )}
      </Card>
    </div>
  );
}

function TrendChartCard({ title, children, empty }) {
  return (
    <Card className="space-y-3">
      <p className="text-sm font-medium text-slate-600 dark:text-slate-300">{title}</p>
      <div className="h-56 min-w-0">
        {empty ? <p className="text-sm text-slate-500">No retained club trend history yet.</p> : children}
      </div>
    </Card>
  );
}

function TrendMetric({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-200 px-3 py-3 dark:border-slate-700">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-semibold">{value}</div>
    </div>
  );
}
