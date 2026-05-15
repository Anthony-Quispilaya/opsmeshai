import type { ReactNode } from "react";
import { Sidebar } from "@/components/layout/sidebar";

export type DashboardShellProps = {
  children: ReactNode;
};

export function DashboardShell({ children }: DashboardShellProps) {
  return (
    <div className="min-h-[100dvh] bg-gradient-to-br from-surface-elevated/25 via-canvas to-canvas">
      <div className="flex min-h-[100dvh] flex-col gap-4 px-2 py-3 lg:flex-row lg:gap-4 lg:px-3 lg:py-4">
        <Sidebar />
        <main className="flex min-w-0 flex-1 flex-col gap-4">{children}</main>
      </div>
    </div>
  );
}
