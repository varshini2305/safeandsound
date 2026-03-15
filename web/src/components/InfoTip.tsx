"use client";

export function InfoTip(props: { text: string }) {
  return (
    <span
      className="ml-1 inline-flex h-4 w-4 cursor-help items-center justify-center rounded-full border border-slate-700 text-[10px] text-slate-300"
      title={props.text}
      aria-label={props.text}
    >
      ?
    </span>
  );
}

