/** Grey block matching the shape of the content it stands in for. No spinners on full pages. */
export function Skeleton({ className = '' }) {
  return <div className={`animate-pulse rounded bg-surface-hover ${className}`} />
}

export function SkeletonPanel({ rows = 3 }) {
  return (
    <div className="ss-card p-4 space-y-3">
      <Skeleton className="h-3 w-1/3" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-4 w-full" />
      ))}
    </div>
  )
}
