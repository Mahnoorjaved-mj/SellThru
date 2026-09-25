/** Modern SaaS Panel Card: elevated, clean border, subtle shadow. Header = title & actions. */
export function Panel({ className = '', children, ...rest }) {
  return (
    <div
      className={`rounded-2xl border border-line/80 bg-surface shadow-card transition-all duration-200 ${className}`}
      {...rest}
    >
      {children}
    </div>
  )
}

export function PanelHeader({ title, description, actions, className = '' }) {
  return (
    <div className={`flex items-start justify-between gap-4 border-b border-line/60 px-5 py-4 ${className}`}>
      <div>
        <h3 className="text-sm font-bold tracking-tight text-primary">{title}</h3>
        {description && <p className="text-xs text-secondary mt-0.5">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>}
    </div>
  )
}

export function PanelBody({ className = '', children }) {
  return <div className={`p-5 ${className}`}>{children}</div>
}
