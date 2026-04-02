import { ResponsiveContainer } from 'recharts';

export default function SafeResponsiveContainer({
  width = '100%',
  height = '100%',
  minWidth = 0,
  minHeight = 1,
  debounce = 16,
  children,
  ...props
}) {
  return (
    <ResponsiveContainer
      width={width}
      height={height}
      minWidth={minWidth}
      minHeight={minHeight}
      debounce={debounce}
      {...props}
    >
      {children}
    </ResponsiveContainer>
  );
}
