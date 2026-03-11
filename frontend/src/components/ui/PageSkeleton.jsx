import Skeleton from './Skeleton';

export default function PageSkeleton() {
  return (
    <div className="page-canvas px-3 py-3 sm:px-4 sm:py-4 lg:px-5 lg:py-5">
      <Skeleton className="h-10 w-1/3" />
      <Skeleton className="h-28 w-full rounded-[1.5rem]" />
      <div className="grid gap-4 md:grid-cols-3">
        <Skeleton className="h-20 w-full rounded-[1.35rem]" />
        <Skeleton className="h-20 w-full rounded-[1.35rem]" />
        <Skeleton className="h-20 w-full rounded-[1.35rem]" />
      </div>
      <Skeleton className="h-72 w-full rounded-[1.5rem]" />
    </div>
  );
}
