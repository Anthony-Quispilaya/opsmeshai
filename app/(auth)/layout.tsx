import type { ReactNode } from "react";
import Link from "next/link";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-[100dvh] bg-gradient-to-br from-surface-elevated/25 via-canvas to-canvas px-4 py-10 sm:px-6">
      <div className="mx-auto flex w-full max-w-md flex-col gap-8">
        <header className="text-center">
          <Link
            href="/login"
            className="inline-flex items-center gap-2 text-sm font-semibold tracking-tight text-foreground"
          >
            <span
              className="flex h-9 w-9 items-center justify-center rounded-md border border-border/10 bg-surface-elevated/60 text-xs font-bold text-accent-foreground shadow-glass backdrop-blur-glass"
              aria-hidden
            >
              OM
            </span>
            OpsMeshAI
          </Link>
          <p className="mt-2 text-xs text-muted">Enterprise AI agent on your phone</p>
        </header>
        {children}
      </div>
    </div>
  );
}
