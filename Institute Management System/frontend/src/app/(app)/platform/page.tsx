"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, Field, Input, Modal, PageHeader, SimpleTable } from "@/components/ui";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage, withBasePath } from "@/lib/api";
import { fmtDate } from "@/lib/utils";

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function PlatformPage() {
  const { me } = useSession();
  const list = useQuery({ queryKey: ["platform-institutes"], queryFn: () => api<any[]>("/platform/institutes"), enabled: !!me?.user.is_superuser });
  const plans = useQuery({ queryKey: ["plans"], queryFn: () => api<any[]>("/platform/plans"), enabled: !!me?.user.is_superuser });
  const [open, setOpen] = useState(false);
  const [f, setF] = useState<Record<string, string>>({ branch_name: "Main Branch" });
  const [created, setCreated] = useState<string | null>(null);
  if (!me?.user.is_superuser) return <Card><p className="text-sm">Platform administration is restricted to super administrators.</p></Card>;
  return (
    <>
      <PageHeader title="Platform administration" description="Tenants (institutes) and subscription plans. Select an institute to operate inside it."
        actions={<Button onClick={() => setOpen(true)}>New institute</Button>} />
      <Card title="Institutes" bodyClass="p-0">
        <SimpleTable headers={["Name", "Code", "Status", "Created", ""]}
          rows={(list.data ?? []).map((i) => [i.name, i.code, i.is_active ? <Badge key="a" tone="green">active</Badge> : <Badge key="i">inactive</Badge>, fmtDate(i.created_at),
            <span key="x" className="flex gap-1">
              <Button size="sm" variant="outline" onClick={() => { localStorage.setItem("cf.institute", i.id); localStorage.removeItem("cf.branch"); window.location.href = withBasePath("/dashboard"); }}>Open</Button>
              <Button size="sm" variant="ghost" onClick={async () => { await api(`/platform/institutes/${i.id}`, { method: "PATCH", query: { is_active: !i.is_active } }); list.refetch(); }}>{i.is_active ? "Suspend" : "Activate"}</Button>
            </span>])} />
      </Card>
      <Card title="Subscription plans" className="mt-4" bodyClass="p-0">
        <SimpleTable headers={["Code", "Name", "Monthly", "Annual", "Trial days"]} rows={(plans.data ?? []).map((p) => [p.code, p.name, p.price_monthly, p.price_annual, p.trial_days])} />
      </Card>
      <Modal open={open} onOpenChange={setOpen} title="Provision institute"
        footer={<Button onClick={async () => {
          try { const r = await api<any>("/platform/institutes", { method: "POST", body: f }); setOpen(false); list.refetch(); setCreated(`Admin ${r.admin_email} temporary password: ${r.temporary_password}`); } catch (e) { toast.error(errorMessage(e)); }
        }}>Create</Button>}>
        <div className="space-y-3">
          {[["name", "Institute name"], ["code", "Code"], ["branch_name", "First branch"], ["admin_name", "Administrator name"], ["admin_email", "Administrator email"], ["plan_code", "Plan code (optional)"]].map(([k, l]) => (
            <Field key={k} label={l}><Input value={f[k] ?? ""} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></Field>
          ))}
        </div>
      </Modal>
      <Modal open={!!created} onOpenChange={() => setCreated(null)} title="Institute created"><p className="break-all font-mono text-sm">{created}</p></Modal>
    </>
  );
}
