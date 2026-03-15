import "./globals.css";

export const metadata = {
  title: "Safe and Sound",
  description: "Local-first privacy + sycophancy analysis from chat exports"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="mx-auto max-w-6xl px-6 py-10">
          <header className="mb-8 flex flex-col gap-2">
            <div className="flex items-center justify-between gap-4">
              <h1 className="text-2xl font-semibold tracking-tight">Safe and Sound</h1>
              <span className="pill">local-first</span>
            </div>
            <p className="text-sm text-slate-300">
              Analyze your AI chat export locally: anonymize sensitive data, then find moments where the assistant changes its answer after you push back.
            </p>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
