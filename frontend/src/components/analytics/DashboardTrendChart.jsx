import { Area, AreaChart, CartesianGrid, Tooltip, XAxis } from 'recharts';
import SafeResponsiveContainer from '../charts/SafeResponsiveContainer';

export default function DashboardTrendChart({ chartChrome, data }) {
  return (
    <SafeResponsiveContainer>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="avgGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.35} />
            <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={chartChrome.grid} strokeDasharray="3 3" />
        <XAxis
          dataKey="month"
          tick={{ fill: chartChrome.axis, fontSize: 12 }}
          axisLine={{ stroke: chartChrome.grid }}
          tickLine={{ stroke: chartChrome.grid }}
        />
        <Tooltip
          cursor={{ stroke: chartChrome.grid, strokeWidth: 1 }}
          contentStyle={{
            background: chartChrome.tooltipBg,
            borderColor: chartChrome.tooltipBorder,
            borderRadius: '1rem',
            color: chartChrome.tooltipText
          }}
          labelStyle={{ color: chartChrome.tooltipText, fontWeight: 600 }}
          itemStyle={{ color: chartChrome.tooltipText }}
        />
        <Area type="monotone" dataKey="avg" stroke="#4f46e5" fill="url(#avgGradient)" strokeWidth={2.5} />
      </AreaChart>
    </SafeResponsiveContainer>
  );
}
