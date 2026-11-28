"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button, Card, Field, Input, PageHeader } from "@/components/ui";
import { ResourceList } from "@/components/data/resource-list";
import { api, errorMessage } from "@/lib/api";
import { addDaysISO, todayISO } from "@/lib/utils";

export default function BillingRunsPage() {
  const [asOf, setAsOf] = useState(todayISO());
  const [from, setFrom] = useState(addDaysISO(todayISO(), -30));
  const [to, setTo] = useState(todayISO());
  const [issue, setIssue] = useState(todayISO());
  const [due, setDue] = useState(addDaysISO(todayISO(), 10));
  const [busy, setBusy] = useState<string | null>(null);
  const [key, setKey] = useState(0);
  const run = async (name: string, path: string, body: unknown) => {
    setBusy(name);
    try {
      const r = await api<Record<string, unknown>>(path, { method: "POST", body });
      toast.success(Object.entries(r).map(([k, v]) => `${k.replace(/_/g, " ")}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join(" · "));
      setKey((k) => k + 1);
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };
  return (
    <>
      <PageHeader title="Billing runs" description="Generate periodic invoices from fee agreements, and review per-class charges before invoicing." />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="1 · Periodic invoices">
          <p className="mb-3 text-sm text-slate-500">Creates monthly / quarterly / annual / instalment invoices for active agreements up to the selected date. Idempotent — periods already invoiced are skipped.</p>
          <Field label="Bill up to"><Input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} /></Field>
          <Button className="mt-3" loading={busy === "scheduled"} onClick={() => run("scheduled", "/billing/generate-invoices", { as_of: asOf })}>Generate invoices</Button>
        </Card>
        <Card title="2 · Per-class charges">
          <p className="mb-3 text-sm text-slate-500">Creates reviewable charges from completed classes with submitted attendance (present/late) and an active per-class agreement. Never duplicates a student/class charge.</p>
          <div className="grid grid-cols-2 gap-2"><Field label="From"><Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></Field><Field label="To"><Input type="date" value={to} onChange={(e) => setTo(e.target.value)} /></Field></div>
          <Button className="mt-3" loading={busy === "charges"} onClick={() => run("charges", "/billing/per-class/generate", { from_date: from, to_date: to })}>Generate charges</Button>
        </Card>
        <Card title="3 · Invoice approved charges">
          <p className="mb-3 text-sm text-slate-500">Groups approved charges into one invoice per student.</p>
          <div className="grid grid-cols-2 gap-2"><Field label="Issue date"><Input type="date" value={issue} onChange={(e) => setIssue(e.target.value)} /></Field><Field label="Due date"><Input type="date" value={due} onChange={(e) => setDue(e.target.value)} /></Field></div>
          <Button className="mt-3" loading={busy === "invoice"} onClick={() => run("invoice", "/billing/per-class/invoice", { issue_date: issue, due_date: due })}>Create invoices</Button>
        </Card>
      </div>
      <div className="mt-4 space-y-4">
        <ResourceList key={`p${key}`} resource="billable-charges" title="Charges awaiting review" fixedFilters={{ status: "pending_review" }} hideCreate />
        <ResourceList key={`a${key}`} resource="billable-charges" title="Approved — ready to invoice" fixedFilters={{ status: "approved" }} hideCreate compact />
      </div>
    </>
  );
}
