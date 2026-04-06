import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type StatusValue = "ADMIN" | "OPERATOR" | "CITIZEN" | "GUEST" | "BANNED";

const statusClasses: Record<StatusValue, string> = {
  ADMIN: "border-sky-500/30 bg-sky-500/10 text-sky-200",
  OPERATOR: "border-slate-500/30 bg-slate-500/10 text-slate-200",
  CITIZEN: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
  GUEST: "border-amber-500/30 bg-amber-500/10 text-amber-100",
  BANNED: "border-rose-500/30 bg-rose-500/10 text-rose-200",
};

interface StatusBadgeProps {
  value: StatusValue;
  className?: string;
}

export function StatusBadge({ value, className }: StatusBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "rounded-full px-2.5 py-1 font-medium tracking-[0.18em]",
        statusClasses[value],
        className,
      )}
    >
      {value}
    </Badge>
  );
}
