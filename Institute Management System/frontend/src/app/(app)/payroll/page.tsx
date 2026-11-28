"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Button, Card, Field, PageHeader } from "@/components/ui";
import { RefSelect } from "@/components/data/ref-select";
import { ResourceList } from "@/components/data/resource-list";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage } from "@/lib/api";

export default function PayrollPage() {
  const { can } = useSession();
  const qc = useQueryClient();
  const [period, setPeriod] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const run = async (name: string, path: string) => {
    setBusy(name);
    try {
      const r = await api<Record<string, unknown>>(path, { method: "POST" });
      toast.success(Object.entries(r).map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`).join(" · "));
      qc.invalidateQueries({ queryKey: ["list"] });
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };
  return (
    <>
      <PageHeader title="Teacher payroll" description="Fixed salaries are prorated; per-class and per-hour pay uses verified teacher attendance on completed classes only." />
      <ResourceList resource="payroll-periods" title="Payroll periods" compact />
      <Card title="Process a period" className="mt-4">
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Payroll period" className="w-72"><RefSelect resource="payroll-periods" value={period} onChange={setPeriod} /></Field>
          <Button disabled={!period || !can("payroll.write")} loading={busy === "gen"} onClick={() => run("gen", `/payroll-periods/${period}/generate`)}>1 · Generate payable entries</Button>
          <Button variant="accent" disabled={!period || !can("payroll.approve")} loading={busy === "app"} onClick={() => run("app", `/payroll-periods/${period}/approve`)}>2 · Approve & create payslips</Button>
        </div>
        <p className="mt-2 text-xs text-slate-500">Add bonuses, allowances or deductions as manual payable entries before approval. Record payouts from the payslip list.</p>
      </Card>
      {period && (
        <div className="mt-4 space-y-4">
          <ResourceList key={`e${period}`} resource="teacher-payables" title="Payable entries" fixedFilters={{ payroll_period_id: period }} />
          <ResourceList key={`s${period}`} resource="payslips" title="Payslips" fixedFilters={{ payroll_period_id: period }} hideCreate />
        </div>
      )}
    </>
  );
}
