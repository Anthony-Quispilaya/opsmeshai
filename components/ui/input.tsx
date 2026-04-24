import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type InputProps = InputHTMLAttributes<HTMLInputElement>;

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        "flex h-10 w-full rounded-md border border-border/10 bg-surface-elevated/40 px-3 py-2 text-sm text-foreground shadow-inner backdrop-blur-glass placeholder:text-muted focus-visible:shadow-focus",
        className,
      )}
      {...props}
    />
  ),
);

Input.displayName = "Input";
