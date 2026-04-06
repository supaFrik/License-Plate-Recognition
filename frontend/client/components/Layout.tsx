import { ReactNode, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  CarFront,
  History as HistoryIcon,
  LogOut,
  Menu,
  Shield,
  SquareTerminal,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/StatusBadge";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

interface LayoutProps {
  children: ReactNode;
  title: string;
  subtitle: string;
  actions?: ReactNode;
}

const navigationItems = [
  {
    label: "Detection Console",
    to: "/console",
    icon: SquareTerminal,
  },
  {
    label: "Vehicle Registry",
    to: "/vehicles",
    icon: CarFront,
  },
  {
    label: "Detections History",
    to: "/history",
    icon: HistoryIcon,
  },
];

export default function Layout({
  children,
  title,
  subtitle,
  actions,
}: LayoutProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const { logout, user } = useAuth();
  const roleValue = user?.role ?? "OPERATOR";

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex min-h-screen">
        <aside className="hidden w-72 shrink-0 border-r border-border bg-card/90 px-6 py-8 md:flex md:flex-col">
          <button
            className="flex items-center gap-3 text-left"
            onClick={() => navigate("/console")}
            type="button"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/30 bg-primary/10 text-primary">
              <Shield className="h-6 w-6" />
            </div>
            <div>
              <div className="text-lg font-semibold tracking-tight">
                VietPlateAI
              </div>
              <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
                Secure Console
              </div>
            </div>
          </button>

          <nav className="mt-10 space-y-2">
            {navigationItems.map(({ icon: Icon, label, to }) => (
              <NavLink
                key={to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-xl border px-4 py-3 text-sm font-medium transition-colors",
                    isActive
                      ? "border-primary/30 bg-primary/10 text-foreground"
                      : "border-transparent text-muted-foreground hover:border-border hover:bg-background/60 hover:text-foreground",
                  )
                }
                to={to}
              >
                <Icon className="h-4 w-4" />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="mt-auto rounded-2xl border border-border bg-background/70 p-4">
            <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
              Signed in as
            </div>
            <div className="mt-3 text-sm font-medium text-foreground">
              {user?.email ?? "Unknown user"}
            </div>
            <div className="mt-3">
              <StatusBadge value={roleValue} />
            </div>
            <Button
              className="mt-4 w-full justify-start"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
              variant="outline"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </Button>
          </div>
        </aside>

        <div className="flex min-h-screen flex-1 flex-col">
          <header className="border-b border-border bg-background/95 backdrop-blur">
            <div className="flex items-center justify-between gap-4 px-4 py-4 md:px-8">
              <div className="flex items-center gap-3 md:hidden">
                <Button
                  onClick={() => setMobileOpen((open) => !open)}
                  size="icon"
                  type="button"
                  variant="outline"
                >
                  {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
                </Button>
                <div>
                  <div className="text-sm font-semibold tracking-tight">
                    VietPlateAI
                  </div>
                  <div className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground">
                    Secure Console
                  </div>
                </div>
              </div>

              <div className="hidden min-w-0 flex-1 md:block">
                <h1 className="text-2xl font-semibold tracking-tight text-foreground">
                  {title}
                </h1>
                <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
              </div>

              <div className="flex items-center gap-3">
                <div className="hidden md:block">
                  <StatusBadge value={roleValue} />
                </div>
                {actions}
              </div>
            </div>

            {mobileOpen && (
              <div className="border-t border-border bg-card px-4 py-4 md:hidden">
                <div className="mb-4">
                  <div className="text-sm font-semibold">{title}</div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {subtitle}
                  </div>
                </div>
                <nav className="space-y-2">
                  {navigationItems.map(({ icon: Icon, label, to }) => (
                    <NavLink
                      key={to}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center gap-3 rounded-xl border px-4 py-3 text-sm font-medium transition-colors",
                          isActive
                            ? "border-primary/30 bg-primary/10 text-foreground"
                            : "border-transparent text-muted-foreground hover:border-border hover:bg-background/60 hover:text-foreground",
                        )
                      }
                      onClick={() => setMobileOpen(false)}
                      to={to}
                    >
                      <Icon className="h-4 w-4" />
                      <span>{label}</span>
                    </NavLink>
                  ))}
                </nav>
                <Button
                  className="mt-4 w-full justify-start"
                  onClick={async () => {
                    await logout();
                    navigate("/login");
                  }}
                  variant="outline"
                >
                  <LogOut className="h-4 w-4" />
                  Logout
                </Button>
              </div>
            )}
          </header>

          <main className="flex-1 px-4 py-6 md:px-8 md:py-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
