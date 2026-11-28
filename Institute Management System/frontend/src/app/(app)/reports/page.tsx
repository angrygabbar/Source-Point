"use client";

import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button, Card, EmptyState, ErrorState, Field, Input, Menu, PageHeader, Select, SimpleTable, Skeleton } from "@/components/ui";
import { RefSelect } from "@/components/data/ref-select";
import { api, errorMessage, openFile } from "@/lib/api";
import { addDaysISO, cn, todayISO } from "@/lib/utils";

interface ReportDef { key: string; category: string; title: string }

const NEEDS: Record<string, string[]> = {
  "student-attendance": ["range", "batch_id", "subject_id"], "subject-attendance": ["range", "batch_id"], "batch-attendance": ["range"],
  "monthly-attendance": ["range", "batch_id"], "teacher-attendance": ["range"], "class-completion": ["range"], "makeup-sessions": ["range"],
  "teacher-workload": ["range"], "syllabus-completion": ["batch_id", "subject_id"], "homework-submission": ["range"], "exam-performance": ["range"],
  "student-progress": ["student_id"], "daily-collection": ["range"], "monthly-collection": ["range"], "revenue-by": ["range", "dimension"],
  "discounts-scholarships": ["range"], expenses: ["range"], "income-expenditure": ["range"], "profit-loss": ["range"], "teacher-payroll": ["payroll_period_id"],
  "admission-conversion": ["range"], "student-acquisition": ["range"], "student-retention": ["range"], "classroom-utilization": ["range"],
  "teacher-utilization": ["range"], "branch-comparison": ["range"], "operational-cost": ["range"],
};

export default function ReportsPage() {
  const list = useQuery({ queryKey: ["reports"], queryFn: () => api<ReportDef[]>("/reports") });
  const [sel, setSel] = useState<string | null>(null);
  const [params, setParams] = useState<Record<string, string>>({ start: addDaysISO(todayISO(), -30), end: todayISO(), dimension: "course" });
  const [run, setRun] = useState<Record<string, string> | null>(null);
  const data = useQuery({
    queryKey: ["report", sel, run],
    queryFn: () => api<{ title: string; headers: string[]; rows: unknown[][] }>(`/reports/${sel}`, { query: run ?? {} }),
    enabled: !!sel && !!run,
  });
  const needs = sel ? NEEDS[sel] ?? ["range"] : [];
  const grouped = (list.data ?? []).reduce<Record<string, ReportDef[]>>((a, r) => ((a[r.category] = [...(a[r.category] ?? []), r]), a), {});
  const query = () => Object.fromEntries(Object.entries(params).filter(([k, v]) => v && (k === "start" || k === "end" ? needs.includes("range") : needs.includes(k))));

  return (
    <>
      <PageHeader title="Reports & analytics" description="All reports read live data and respect your role, institute and branch scope." />
      <div className="grid gap-4 lg:grid-cols-4">
        <Card title="Reports" bodyClass="p-2">
          {list.isLoading ? <Skeleton className="h-60" /> : Object.entries(grouped).map(([cat, rs]) => (
            <div key={cat} className="mb-3">
              <p className="px-2 py-1 text-[11px] font-semibold uppercase text-slate-500">{cat}</p>
              {rs.map((r) => (
                <button key={r.key} onClick={() => { setSel(r.key); setRun(null); }} className={cn("block w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-slate-100", sel === r.key && "bg-indigo-50 font-medium text-brand-800")}>{r.title}</button>
              ))}
            </div>
          ))}
        </Card>
        <div className="space-y-4 lg:col-span-3">
          {!sel ? <Card><EmptyState title="Choose a report" description="Select a report, set filters and run it. Export to CSV, Excel or PDF." /></Card> : (
            <>
              <Card title="Filters">
                <div className="flex flex-wrap items-end gap-3">
                  {needs.includes("range") && <><Field label="From"><Input type="date" value={params.start} onChange={(e) => setParams({ ...params, start: e.target.value })} /></Field><Field label="To"><Input type="date" value={params.end} onChange={(e) => setParams({ ...params, end: e.target.value })} /></Field></>}
                  {needs.includes("batch_id") && <Field label="Batch" className="w-56"><RefSelect resource="batches" value={params.batch_id || null} onChange={(v) => setParams({ ...params, batch_id: v ?? "" })} /></Field>}
                  {needs.includes("subject_id") && <Field label="Subject" className="w-56"><RefSelect resource="subjects" value={params.subject_id || null} onChange={(v) => setParams({ ...params, subject_id: v ?? "" })} /></Field>}
                  {needs.includes("student_id") && <Field label="Student" className="w-56"><RefSelect resource="students" value={params.student_id || null} onChange={(v) => setParams({ ...params, student_id: v ?? "" })} /></Field>}
                  {needs.includes("payroll_period_id") && <Field label="Payroll period" className="w-56"><RefSelect resource="payroll-periods" value={params.payroll_period_id || null} onChange={(v) => setParams({ ...params, payroll_period_id: v ?? "" })} /></Field>}
                  {needs.includes("dimension") && <Field label="Group by"><Select value={params.dimension} onChange={(e) => setParams({ ...params, dimension: e.target.value })}>{["course", "subject", "batch", "branch"].map((d) => <option key={d}>{d}</option>)}</Select></Field>}
                  <Button onClick={() => setRun(query())}>Run report</Button>
                  <Menu trigger={<Button variant="outline"><Download className="h-4 w-4" /> Export</Button>} items={["csv", "xlsx", "pdf"].map((f) => ({
                    label: f.toUpperCase(), onClick: () => openFile(`/reports/${sel}`, { query: { ...query(), format: f }, download: true }).catch((e) => toast.error(errorMessage(e))),
                  }))} />
                </div>
              </Card>
              <Card title={data.data?.title ?? "Results"} bodyClass="p-0">
                {!run ? <EmptyState title="Run the report to see results" /> : data.isLoading ? <Skeleton className="m-4 h-40" /> : data.isError ? <div className="p-4"><ErrorState error={data.error} /></div> : (
                  <SimpleTable headers={data.data!.headers} rows={data.data!.rows.map((r) => r.map((c) => (c === null || c === undefined ? "—" : String(c))))} empty="No data for the selected filters" />
                )}
              </Card>
            </>
          )}
        </div>
      </div>
    </>
  );
}
