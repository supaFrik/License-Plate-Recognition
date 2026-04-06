import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-6">
      <div className="w-full max-w-xl rounded-3xl border border-border bg-card p-10 text-center shadow-2xl shadow-black/20">
        <div className="text-xs uppercase tracking-[0.32em] text-muted-foreground">
          VietPlateAI
        </div>
        <h1 className="mt-4 text-4xl font-semibold tracking-tight text-foreground">
          Route not found
        </h1>
        <p className="mt-4 text-sm leading-6 text-muted-foreground">
          The requested console route does not exist or is no longer available.
        </p>
        <Button asChild className="mt-8">
          <Link to="/">Return to console</Link>
        </Button>
      </div>
    </div>
  );
}
