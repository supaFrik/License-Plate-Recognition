import { Activity, ShieldCheck } from "lucide-react";

export default function LoadingScreen() {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-6">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.16),transparent_24%),linear-gradient(180deg,rgba(15,23,42,0.98),rgba(2,6,23,1))]" />

      <div className="relative w-full max-w-xl overflow-hidden rounded-3xl border border-border/80 bg-card/95 p-8 shadow-2xl shadow-black/30 backdrop-blur">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/70 to-transparent" />

        <div className="flex items-start justify-between gap-6">
          <div>
            <div className="text-xs font-medium uppercase tracking-[0.28em] text-primary">
              VietPlateAI
            </div>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-foreground">
              Loading secure console
            </h1>
            <p className="mt-3 max-w-md text-sm leading-6 text-muted-foreground">
              Establishing operator session, restoring access controls, and
              preparing live detection services.
            </p>
          </div>

          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
            <ShieldCheck className="h-7 w-7" />
          </div>
        </div>

        <div className="mt-8 rounded-2xl border border-border/80 bg-background/70 p-5">
          <div className="flex items-center justify-between gap-4 text-sm">
            <div className="flex items-center gap-3 text-foreground">
              <Activity className="h-4 w-4 animate-pulse text-primary" />
              Session bootstrap in progress
            </div>
            <span className="font-mono text-xs uppercase tracking-[0.24em] text-muted-foreground">
              Active
            </span>
          </div>

          <div className="mt-4 h-2 overflow-hidden rounded-full bg-muted">
            <div className="loading-screen-bar h-full w-1/3 rounded-full bg-gradient-to-r from-primary/80 via-sky-300 to-primary" />
          </div>

          <div className="mt-4 grid gap-3 text-xs uppercase tracking-[0.2em] text-muted-foreground sm:grid-cols-3">
            <div className="rounded-xl border border-border/80 bg-card/60 px-3 py-2">
              Refresh session
            </div>
            <div className="rounded-xl border border-border/80 bg-card/60 px-3 py-2">
              Validate token
            </div>
            <div className="rounded-xl border border-border/80 bg-card/60 px-3 py-2">
              Prepare routes
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
