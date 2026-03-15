export function Stat(props: { label: string; value: string | number }) {
  return (
    <div className="card p-4">
      <div className="text-xs text-slate-400">{props.label}</div>
      <div className="mt-1 text-xl font-semibold">{props.value}</div>
    </div>
  );
}

