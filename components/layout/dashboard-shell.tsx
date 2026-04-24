import type { ReactNode } from "react";
import { Sidebar } from "@/components/layout/sidebar";

export type DashboardShellProps = {
  children: ReactNode;
};

export function DashboardShell({ children }: DashboardShellProps) {
  return (
    <div className="min-h-[100dvh] bg-gradient-to-br from-surface-elevated/25 via-canvas to-canvas">
      <div className="mx-auto flex min-h-[100dvh] max-w-[1400px] flex-col gap-8 px-4 py-6 sm:px-6 lg:flex-row lg:px-10 lg:py-10">
        <Sidebar />
        <main className="flex min-w-0 flex-1 flex-col gap-8">{children}</main>
      </div>
    </div>
  );
}
