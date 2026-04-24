import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-accent text-accent-foreground hover:opacity-90 active:opacity-80 border border-transparent",
  secondary:
    "bg-surface-elevated/80 text-foreground border border-border/10 backdrop-blur-glass hover:bg-surface-elevated",
  ghost:
    "bg-transparent text-foreground border border-transparent hover:bg-surface-elevated/60",
  danger:
    "bg-danger/15 text-danger border border-danger/30 hover:bg-danger/25",
};

const baseClasses =
  "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50";

export function buttonClassName(
  variant: ButtonVariant = "primary",
  className?: string,
) {
  return cn(baseClasses, variantClasses[variant], className);
}

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", type = "button", ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={buttonClassName(variant, className)}
      {...props}
    />
  ),
);

Button.displayName = "Button";
