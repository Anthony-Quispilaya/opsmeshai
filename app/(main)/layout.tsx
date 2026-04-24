import type { ReactNode } from "react";
import { AuthGate } from "@/components/auth-gate";
import { DashboardShell } from "@/components/layout/dashboard-shell";

export default function MainLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <AuthGate>
      <DashboardShell>{children}</DashboardShell>
    </AuthGate>
  );
}
