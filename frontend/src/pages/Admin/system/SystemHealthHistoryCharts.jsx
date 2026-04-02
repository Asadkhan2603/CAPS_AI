import { Area, AreaChart, CartesianGrid, Tooltip, XAxis, YAxis } from 'recharts';
import Card from '../../../components/ui/Card';
import SafeResponsiveContainer from '../../../components/charts/SafeResponsiveContainer';

const LIVE_CHARTS = [
  {
    title: 'Live Queue Depth History',
    dataKey: 'queuedJobs',
    stroke: '#2563eb',
    fill: '#93c5fd',
    yAxisProps: { allowDecimals: false, width: 36 },
  },
  {
    title: 'Live Fallback Rate History',
    dataKey: 'fallbackRatePct',
    stroke: '#d97706',
    fill: '#fcd34d',
    yAxisProps: { width: 42, domain: [0, 'dataMax + 5'] },
    tooltipFormatter: (value) => [`${Number(value).toFixed(2)}%`, 'Fallback Rate'],
  },
  {
    title: 'Live Similarity Candidate History',
    dataKey: 'similarityCandidates',
    stroke: '#7c3aed',
    fill: '#c4b5fd',
    yAxisProps: { allowDecimals: false, width: 36 },
  },
];

const PERSISTED_CHARTS = [
  {
    title: 'Persisted Queue History',
    dataKey: 'queuedJobs',
    stroke: '#0f766e',
    fill: '#5eead4',
    yAxisProps: { allowDecimals: false, width: 36 },
  },
  {
    title: 'Persisted Fallback History',
    dataKey: 'fallbackRatePct',
    stroke: '#be123c',
    fill: '#fda4af',
    yAxisProps: { width: 42, domain: [0, 'dataMax + 5'] },
    tooltipFormatter: (value) => [`${Number(value).toFixed(2)}%`, 'Fallback Rate'],
  },
  {
    title: 'Persisted Similarity History',
    dataKey: 'similarityCandidates',
    stroke: '#4338ca',
    fill: '#a5b4fc',
    yAxisProps: { allowDecimals: false, width: 36 },
  },
  {
    title: 'Persisted Snapshot Row Count',
    dataKey: 'retainedRows',
    stroke: '#15803d',
    fill: '#86efac',
    yAxisProps: { allowDecimals: false, width: 42 },
  },
  {
    title: 'Persisted Snapshot Prune Activity',
    dataKey: 'prunedDeletedCount',
    stroke: '#b91c1c',
    fill: '#fca5a5',
    yAxisProps: { allowDecimals: false, width: 42 },
  },
];

const LOCAL_CHARTS = [
  {
    title: 'Local Queue Snapshot Retention',
    dataKey: 'queuedJobs',
    stroke: '#0369a1',
    fill: '#7dd3fc',
    yAxisProps: { allowDecimals: false, width: 36 },
  },
  {
    title: 'Local Fallback Snapshot Retention',
    dataKey: 'fallbackRatePct',
    stroke: '#7c2d12',
    fill: '#fdba74',
    yAxisProps: { width: 42, domain: [0, 'dataMax + 5'] },
    tooltipFormatter: (value) => [`${Number(value).toFixed(2)}%`, 'Fallback Rate'],
  },
  {
    title: 'Local Similarity Snapshot Retention',
    dataKey: 'similarityCandidates',
    stroke: '#581c87',
    fill: '#d8b4fe',
    yAxisProps: { allowDecimals: false, width: 36 },
  },
];

export default function SystemHealthHistoryCharts({
  historyData,
  persistedHistoryData,
  localHistoryData,
}) {
  return (
    <>
      <ChartGrid data={historyData} charts={LIVE_CHARTS} columnsClass="xl:grid-cols-3" />
      <ChartGrid data={persistedHistoryData} charts={PERSISTED_CHARTS.slice(0, 3)} columnsClass="xl:grid-cols-3" />
      <ChartGrid data={persistedHistoryData} charts={PERSISTED_CHARTS.slice(3)} columnsClass="xl:grid-cols-2" />
      <ChartGrid data={localHistoryData} charts={LOCAL_CHARTS} columnsClass="xl:grid-cols-3" />
    </>
  );
}

function ChartGrid({ data, charts, columnsClass }) {
  return (
    <div className={`grid gap-3 ${columnsClass}`}>
      {charts.map((chart) => (
        <HealthAreaChartCard key={chart.title} data={data} {...chart} />
      ))}
    </div>
  );
}

function HealthAreaChartCard({
  title,
  data,
  dataKey,
  stroke,
  fill,
  yAxisProps,
  tooltipFormatter,
}) {
  return (
    <Card className="space-y-3">
      <p className="text-sm font-medium text-slate-600 dark:text-slate-300">{title}</p>
      <div className="h-56 min-w-0">
        {!data.length ? (
          <p className="text-sm text-slate-500">No recent history yet.</p>
        ) : (
          <SafeResponsiveContainer>
            <AreaChart data={data}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis {...yAxisProps} />
              <Tooltip formatter={tooltipFormatter} />
              <Area type="monotone" dataKey={dataKey} stroke={stroke} fill={fill} fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </SafeResponsiveContainer>
        )}
      </div>
    </Card>
  );
}
