import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export type TopBarProps = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  className?: string;
};

export function TopBar({ title, subtitle, actions, className }: TopBarProps) {
  return (
    <header
      className={cn(
        "flex flex-col gap-4 border-b border-border/10 pb-6 sm:flex-row sm:items-end sm:justify-between",
        className,
      )}
    >
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle ? (
          <p className="mt-1 max-w-2xl text-sm text-muted">{subtitle}</p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex flex-wrap items-center gap-2">{actions}</div>
      ) : null}
    </header>
  );
}
