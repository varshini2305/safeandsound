import "./globals.css";

export const metadata = {
  title: "SwayBench",
  description: "Local-first privacy + sycophancy analysis from chat exports"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="mx-auto max-w-6xl px-6 py-10">
          <header className="mb-8 flex flex-col gap-2">
            <div className="flex items-center justify-between gap-4">
              <h1 className="text-2xl font-semibold tracking-tight">SwayBench</h1>
              <span className="pill">local-first</span>
            </div>
            <p className="text-sm text-slate-300">
              Analyze your AI chat export locally: anonymize sensitive data, then find moments where the assistant changes its answer after you push back.
            </p>
          </header>
          {children}
          <footer className="mt-10 text-xs text-slate-500">
            Backend: FastAPI on <span className="font-mono">localhost:8000</span>. Frontend: Next.js on{" "}
            <span className="font-mono">localhost:3000</span>.
          </footer>
        </div>
      </body>
    </html>
  );
}
