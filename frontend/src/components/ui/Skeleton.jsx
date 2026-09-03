export function Skeleton({ className = "" }) {
  return (
    <div
      className={`relative overflow-hidden rounded-xl bg-hover/6 ${className}`}
    >
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-hover/70 to-transparent" />
    </div>
  );
}

export function SkeletonLine({ width = "w-full" }) {
  return <Skeleton className={`h-3.5 ${width}`} />;
}

export function SkeletonCard() {
  return (
    <div className="panel p-6">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="mt-4 h-8 w-32" />
      <Skeleton className="mt-3 h-3 w-40" />
    </div>
  );
}
