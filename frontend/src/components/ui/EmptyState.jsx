/** One line of what's missing + one primary action. Left-aligned. No illustration. */
export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-start gap-3 py-8 px-1">
      <div className="flex items-center gap-2 text-primary">
        {Icon && <Icon size={16} className="text-tertiary" />}
        <span className="text-sm font-semibold">{title}</span>
      </div>
      {description && <p className="text-body text-secondary max-w-md">{description}</p>}
      {action}
    </div>
  )
}

export function ErrorState({ title = 'Something went wrong', description, onRetry }) {
  return (
    <div className="flex flex-col items-start gap-3 py-8 px-1">
      <span className="text-sm font-semibold text-down">{title}</span>
      {description && <p className="text-body text-secondary max-w-md">{description}</p>}
      {onRetry && (
        <button
          onClick={onRetry}
          className="ss-btn-ghost px-3 py-1.5 text-xs font-semibold"
        >
          Retry
        </button>
      )}
    </div>
  )
}
