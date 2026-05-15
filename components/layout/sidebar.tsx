"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { primaryNav } from "@/components/layout/nav-config";
import { Button } from "@/components/ui/button";
import { clearStoredToken } from "@/lib/auth-token";

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  function signOut() {
    clearStoredToken();
    router.replace("/login");
  }

  return (
    <aside className="flex w-full flex-col gap-3 lg:w-48 lg:shrink-0">
      <div className="px-1">
        <Link
          href="/dashboard"
          className="flex items-center gap-2 rounded-md px-2 py-1 text-sm font-semibold tracking-tight text-foreground focus-visible:shadow-focus"
        >
          <span
            className="flex h-8 w-8 items-center justify-center rounded-md border border-border/10 bg-surface-elevated/60 text-xs font-bold text-accent-foreground shadow-glass backdrop-blur-glass"
            aria-hidden
          >
            OM
          </span>
          <span>OpsMeshAI</span>
        </Link>
        <p className="mt-2 px-2 text-xs text-muted">AI agent on your phone</p>
      </div>
      <nav aria-label="Primary" className="flex flex-col gap-1">
        {primaryNav.map((item) => {
          const active =
            item.href === "/dashboard" ? pathname === "/dashboard" : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "rounded-md px-3 py-2 text-sm transition-colors focus-visible:shadow-focus",
                active
                  ? "bg-surface-elevated/80 text-foreground shadow-glass backdrop-blur-glass"
                  : "text-muted hover:bg-surface-elevated/40 hover:text-foreground",
              )}
            >
              <span className="block font-medium">{item.label}</span>
              <span className="mt-0.5 block text-xs font-normal text-muted">
                {item.description}
              </span>
            </Link>
          );
        })}
      </nav>
      <div className="px-1">
        <Button type="button" variant="ghost" className="w-full justify-start text-muted" onClick={signOut}>
          Sign out
        </Button>
      </div>
    </aside>
  );
}
