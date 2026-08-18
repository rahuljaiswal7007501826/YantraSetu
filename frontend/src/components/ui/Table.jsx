/**
 * Minimal, reusable data table.
 *   columns: [{ key, label, align? }]
 *   rows:    array of row objects (should have a stable `id` where possible)
 *   renderCell(row, column): optional custom cell renderer
 *   onRowClick(row): optional; makes rows clickable
 *   activeId: highlights the row whose id matches
 */
export default function Table({
  columns,
  rows = [],
  renderCell,
  emptyLabel = 'No data',
  onRowClick,
  activeId,
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
            {columns.map((c) => (
              <th key={c.key} className={`px-3 py-2 font-medium ${c.align === 'right' ? 'text-right' : ''}`}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-3 py-6 text-center text-slate-400">
                {emptyLabel}
              </td>
            </tr>
          ) : (
            rows.map((row, i) => {
              const isActive = activeId != null && row.id === activeId
              return (
                <tr
                  key={row.id ?? i}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={`border-b border-slate-100 last:border-0 ${
                    onRowClick ? 'cursor-pointer' : ''
                  } ${isActive ? 'bg-emerald-50' : 'hover:bg-slate-50'}`}
                >
                  {columns.map((c) => (
                    <td key={c.key} className={`px-3 py-2 text-slate-700 ${c.align === 'right' ? 'text-right' : ''}`}>
                      {renderCell ? renderCell(row, c) : row[c.key]}
                    </td>
                  ))}
                </tr>
              )
            })
          )}
        </tbody>
      </table>
    </div>
  )
}
