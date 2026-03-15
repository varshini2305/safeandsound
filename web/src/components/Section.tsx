export function Section(props: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="card p-6">
      <div className="mb-4 flex flex-col gap-1">
        <h2 className="text-lg font-semibold">{props.title}</h2>
        {props.subtitle ? <p className="text-sm text-slate-300">{props.subtitle}</p> : null}
      </div>
      {props.children}
    </section>
  );
}

