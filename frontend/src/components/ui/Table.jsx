/** Dense table: 36px rows, 12px font, sticky header, right-aligned numerics. No zebra striping. */
export function Table({ className = '', children }) {
  return (
    <div className="overflow-x-auto">
      <table className={`ss-table min-w-full ${className}`}>{children}</table>
    </div>
  )
}

export function Th({ className = '', numeric = false, children }) {
  return <th className={`${numeric ? 'text-right' : ''} ${className}`}>{children}</th>
}

export function Td({ className = '', numeric = false, children }) {
  return (
    <td className={`${numeric ? 'text-right ss-num' : ''} ${className}`}>{children}</td>
  )
}
