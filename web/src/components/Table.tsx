type Column<T> = { key: string; header: string; render?: (row: T) => React.ReactNode };

export function Table<T extends Record<string, any>>(props: {
  columns: Array<Column<T>>;
  rows: T[];
  empty?: string;
}) {
  if (props.rows.length === 0) {
    return <div className="text-sm text-slate-400">{props.empty ?? "No rows"}</div>;
  }
  return (
    <div className="overflow-auto rounded-xl border border-slate-800">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-slate-900/60 text-xs uppercase text-slate-400">
          <tr>
            {props.columns.map((c) => (
              <th key={c.key} className="px-3 py-2 font-medium">
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {props.rows.map((r, i) => (
            <tr key={i} className="border-t border-slate-800 hover:bg-slate-900/30">
              {props.columns.map((c) => (
                <td key={c.key} className="px-3 py-2 align-top text-slate-200">
                  {c.render ? c.render(r) : String(r[c.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

