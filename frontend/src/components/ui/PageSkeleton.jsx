import Skeleton from './Skeleton';

export default function PageSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <Skeleton className="h-10 w-1/3" />
      <Skeleton className="h-32 w-full" />
      <div className="grid gap-4 md:grid-cols-3">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
      <Skeleton className="h-80 w-full" />
    </div>
  );
}
