import { cn } from '../../utils/cn';

export default function Spinner({ size = 'md', className }) {
  const sizeMap = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
    xl: 'h-6 w-6'
  };

  return (
    <div className={cn('animate-spin', sizeMap[size], className)}>
      <div className="h-full w-full rounded-full border-2 border-current border-t-transparent" />
    </div>
  );
}
