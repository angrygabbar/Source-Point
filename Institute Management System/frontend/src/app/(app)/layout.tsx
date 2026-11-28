import { AppShell, PortalGuard } from "@/components/layout/app-shell";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <PortalGuard>
      <AppShell>{children}</AppShell>
    </PortalGuard>
  );
}
