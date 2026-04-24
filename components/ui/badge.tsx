import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type BadgeTone = "neutral" | "accent" | "success" | "danger";

const toneClasses: Record<BadgeTone, string> = {
  neutral: "border-border/10 bg-surface-elevated/60 text-muted",
  accent: "border-accent/30 bg-accent/15 text-accent-foreground",
  success: "border-success/30 bg-success/10 text-success",
  danger: "border-danger/30 bg-danger/10 text-danger",
};

export type BadgeProps = HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone };

export function Badge({
  className,
  tone = "neutral",
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium backdrop-blur-sm",
        toneClasses[tone],
        className,
      )}
      {...props}
    />
  );
}
