import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ShieldPlus, UserRoundPlus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth";
import { toast } from "@/hooks/use-toast";

export default function Signup() {
  const navigate = useNavigate();
  const { register, status } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (status === "authenticated") {
    return <Navigate replace to="/console" />;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (password !== confirmPassword) {
      toast({
        title: "Password mismatch",
        description: "Confirm password must match the password field.",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);

    try {
      await register(email, password);
      toast({
        title: "Account created",
        description: "Your operator account is ready and signed in.",
      });
      navigate("/console", { replace: true });
    } catch (error) {
      toast({
        title: "Signup failed",
        description:
          error instanceof Error
            ? error.message
            : "Unable to create the operator account.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-6 py-10">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.12),_transparent_32%),radial-gradient(circle_at_bottom,_rgba(15,23,42,0.85),_transparent_48%)]" />

      <div className="relative w-full max-w-xl rounded-3xl border border-border bg-card/85 p-8 shadow-2xl shadow-black/25 sm:p-10">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-primary/30 bg-primary/10 text-primary">
            <ShieldPlus className="h-5 w-5" />
          </div>
          <div>
            <div className="text-lg font-semibold tracking-tight text-foreground">
              VietPlateAI
            </div>
            <div className="text-[11px] uppercase tracking-[0.28em] text-muted-foreground">
              Operator Signup
            </div>
          </div>
        </div>

        <div className="mt-8 flex items-center gap-2 text-sm text-primary">
          <UserRoundPlus className="h-4 w-4" />
          Create a standard operator account
        </div>

        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-foreground">
          Sign up
        </h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          New signups are created as operator accounts. Admin permissions remain
          restricted to bootstrap or managed accounts.
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
              placeholder="operator@company.com"
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
              autoComplete="new-password"
              className="h-11 border-border bg-background/70"
              minLength={8}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="At least 8 characters"
              required
              type="password"
              value={password}
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium uppercase tracking-[0.28em] text-muted-foreground">
              Confirm password
            </label>
            <Input
              autoComplete="new-password"
              className="h-11 border-border bg-background/70"
              minLength={8}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="Re-enter your password"
              required
              type="password"
              value={confirmPassword}
            />
          </div>

          <Button className="h-11 w-full" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Creating account..." : "Create operator account"}
          </Button>
        </form>

        <p className="mt-6 text-sm text-muted-foreground">
          Already have access?{" "}
          <Link className="text-primary hover:underline" to="/login">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
