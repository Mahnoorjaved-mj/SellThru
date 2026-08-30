/** Panel: bg-surface, 1px border, 6px radius. Header = eyebrow left, actions right. */
export function Panel({ className = '', children, ...rest }) {
  return (
    <div className={`bg-surface border border-line rounded-panel ${className}`} {...rest}>
      {children}
    </div>
  )
}

export function PanelHeader({ title, description, actions, className = '' }) {
  return (
    <div className={`flex items-start justify-between gap-4 border-b border-line px-4 py-3 ${className}`}>
      <div>
        <h3 className="ss-eyebrow">{title}</h3>
        {description && <p className="text-body text-secondary mt-1">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>}
    </div>
  )
}

export function PanelBody({ className = '', children }) {
  return <div className={`p-4 ${className}`}>{children}</div>
}
