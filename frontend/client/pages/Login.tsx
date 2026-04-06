import { FormEvent, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Shield, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth";
import { toast } from "@/hooks/use-toast";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, status } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const redirectTarget =
    (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ??
    "/console";

  if (status === "authenticated") {
    return <Navigate replace to="/console" />;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);

    try {
      await login(email, password);
      toast({
        title: "Authenticated",
        description: "Secure session established for VietPlateAI.",
      });
      navigate(redirectTarget, { replace: true });
    } catch (error) {
      toast({
        title: "Authentication failed",
        description:
          error instanceof Error
            ? error.message
            : "Unable to sign in with the provided credentials.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-6 py-10">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.12),_transparent_32%),radial-gradient(circle_at_bottom,_rgba(15,23,42,0.85),_transparent_48%)]" />

      <div className="relative grid w-full max-w-5xl gap-10 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="hidden rounded-3xl border border-border bg-card/70 p-10 shadow-2xl shadow-black/20 lg:block">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/30 bg-primary/10 text-primary">
              <Shield className="h-6 w-6" />
            </div>
            <div>
              <div className="text-xl font-semibold tracking-tight text-foreground">
                VietPlateAI
              </div>
              <div className="text-xs uppercase tracking-[0.32em] text-muted-foreground">
                High-Trust Detection Operations
              </div>
            </div>
          </div>

          <div className="mt-14 max-w-xl">
            <h1 className="text-4xl font-semibold leading-tight tracking-tight text-foreground">
              Performance-first vehicle access intelligence for secured facilities.
            </h1>
            <p className="mt-5 text-base leading-7 text-muted-foreground">
              VietPlateAI is optimized for fast plate recognition, controlled
              operator access, and reliable audit history without unnecessary UI
              noise.
            </p>
          </div>

          <div className="mt-14 grid gap-4 sm:grid-cols-3">
            {[
              ["Protected API", "JWT access and rotating refresh sessions"],
              ["Focused Surface", "Detection, registry, and history only"],
              ["Low Friction", "Operator-first console with minimal overhead"],
            ].map(([title, description]) => (
              <div
                className="rounded-2xl border border-border bg-background/70 p-4"
                key={title}
              >
                <div className="text-sm font-medium text-foreground">{title}</div>
                <div className="mt-2 text-sm leading-6 text-muted-foreground">
                  {description}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-3xl border border-border bg-card/85 p-8 shadow-2xl shadow-black/25 sm:p-10">
          <div className="flex items-center gap-3 lg:hidden">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-primary/30 bg-primary/10 text-primary">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <div className="text-lg font-semibold tracking-tight text-foreground">
                VietPlateAI
              </div>
              <div className="text-[11px] uppercase tracking-[0.28em] text-muted-foreground">
                Secure Console
              </div>
            </div>
          </div>

          <div className="mt-8 flex items-center gap-2 text-sm text-primary">
            <ShieldCheck className="h-4 w-4" />
            Authenticated operator access
          </div>
          <h2 className="mt-4 text-3xl font-semibold tracking-tight text-foreground">
            Sign in
          </h2>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            Enter your assigned operator credentials to access detection,
            registry, and audit controls.
          </p>

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label className="text-xs font-medium uppercase tracking-[0.28em] text-muted-foreground">
                Email
              </label>
              <Input
                autoComplete="email"
                className="h-11 border-border bg-background/70"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="operator@vietplateai.local"
                required
                type="email"
                value={email}
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-medium uppercase tracking-[0.28em] text-muted-foreground">
                Password
              </label>
              <Input
                autoComplete="current-password"
                className="h-11 border-border bg-background/70"
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your secure password"
                required
                type="password"
                value={password}
              />
            </div>

            <Button className="h-11 w-full" disabled={isSubmitting} type="submit">
              {isSubmitting ? "Signing in..." : "Open secure console"}
            </Button>
          </form>

          <p className="mt-6 text-sm text-muted-foreground">
            Need an operator account?{" "}
            <Link className="text-primary hover:underline" to="/signup">
              Sign up
            </Link>
          </p>
        </section>
      </div>
    </div>
  );
}
