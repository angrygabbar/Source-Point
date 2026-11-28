"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { Button, Card, ErrorState, Modal, PageHeader, Skeleton } from "@/components/ui";
import { useActionRunner } from "@/components/data/action-runner";
import { renderCell, ResourceList } from "@/components/data/resource-list";
import { ResourceForm } from "@/components/data/resource-form";
import { DocumentsPanel } from "@/features/documents/documents-panel";
import { HistoryPanel } from "@/features/documents/history-panel";
import { useMeta } from "@/hooks/use-meta";
import { useSession } from "@/hooks/use-session";
import { api } from "@/lib/api";
import { RESOURCE_ACTIONS } from "@/lib/resource-actions";
import type { Row } from "@/types";

const RELATED: Record<string, { resource: string; field: string; title: string }[]> = {
  batches: [
    { resource: "batch-subjects", field: "batch_id", title: "Subjects" },
    { resource: "enrollments", field: "batch_id", title: "Enrollments" },
    { resource: "teacher-assignments", field: "batch_id", title: "Teacher assignments" },
    { resource: "schedules", field: "batch_id", title: "Timetable" },
  ],
  courses: [{ resource: "subjects", field: "course_id", title: "Subjects" }, { resource: "lms-modules", field: "course_id", title: "LMS modules" }],
  "fee-plans": [{ resource: "fee-plan-items", field: "fee_plan_id", title: "Fee items" }],
  enrollments: [{ resource: "enrollment-subjects", field: "enrollment_id", title: "Subjects" }],
  "lms-modules": [{ resource: "lms-lessons", field: "module_id", title: "Lessons" }],
  "payroll-periods": [{ resource: "teacher-payables", field: "payroll_period_id", title: "Payable entries" }, { resource: "payslips", field: "payroll_period_id", title: "Payslips" }],
  leads: [{ resource: "enquiries", field: "lead_id", title: "Enquiries" }],
  enquiries: [{ resource: "follow-ups", field: "enquiry_id", title: "Follow-ups" }, { resource: "demo-classes", field: "enquiry_id", title: "Demo classes" }],
  "inventory-items": [{ resource: "inventory-transactions", field: "item_id", title: "Stock movements" }],
  assets: [{ resource: "asset-assignments", field: "asset_id", title: "Assignments" }, { resource: "maintenance-records", field: "asset_id", title: "Maintenance" }],
  "library-members": [{ resource: "book-loans", field: "member_id", title: "Loans" }],
  books: [{ resource: "book-loans", field: "book_id", title: "Loans" }],
  "syllabus-chapters": [{ resource: "syllabus-chapters", field: "parent_id", title: "Topics" }],
  parents: [{ resource: "student-parents", field: "parent_id", title: "Linked students" }, { resource: "parent-consents", field: "parent_id", title: "Consents" }],
  schedules: [{ resource: "schedule-exceptions", field: "schedule_id", title: "Exceptions" }],
  "class-sessions": [{ resource: "student-attendance", field: "session_id", title: "Attendance" }],
  vendors: [{ resource: "purchase-records", field: "vendor_id", title: "Purchases" }, { resource: "expenses", field: "vendor_id", title: "Expenses" }],
  campaigns: [{ resource: "leads", field: "campaign_id", title: "Leads" }],
  "lms-lessons": [{ resource: "discussion-threads", field: "lesson_id", title: "Discussions" }],
};

const DOC_OWNERS: Record<string, string> = { parents: "parent", expenses: "expense", "admission-records": "admission" };

export default function ResourceDetailPage() {
  const { resource, id } = useParams<{ resource: string; id: string }>();
  const router = useRouter();
  const { can } = useSession();
  const qc = useQueryClient();
  const meta = useMeta(resource);
  const row = useQuery({ queryKey: ["row", resource, id], queryFn: () => api<Row>(`/${resource}/${id}`) });
  const [editing, setEditing] = useState(false);
  const runner = useActionRunner(() => qc.invalidateQueries({ queryKey: ["row", resource, id] }));

  if (meta.isLoading || row.isLoading) return <Skeleton className="h-64" />;
  if (meta.isError || row.isError || !meta.data || !row.data) return <ErrorState error={meta.error ?? row.error} />;
  const m = meta.data;
  const r = row.data;
  const title = String(r[m.title_field] ?? r.display?.[m.title_field] ?? m.label);
  const actions = (RESOURCE_ACTIONS[resource] ?? []).filter((a) => (!a.perms || can(...a.perms)) && (!a.when || a.when(r)));
  const fields = m.fields.filter((f) => f.name !== "id");

  return (
    <div className="space-y-4">
      <PageHeader
        title={title}
        breadcrumbs={<button className="hover:underline" onClick={() => router.push(`/r/${resource}`)}>{m.label}</button>}
        actions={
          <>
            {actions.map((a) => <Button key={a.label} variant={a.danger ? "danger" : "outline"} size="sm" onClick={() => runner.run(a, r)}>{a.label}</Button>)}
            {m.can.update && <Button size="sm" onClick={() => setEditing(true)}><Pencil className="h-3.5 w-3.5" /> Edit</Button>}
          </>
        }
      />
      <Card>
        <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
          {fields.map((f) => (
            <div key={f.name} className={f.type === "text" || f.type === "json" ? "sm:col-span-2 lg:col-span-3" : undefined}>
              <dt className="text-xs font-medium text-slate-500">{f.label}</dt>
              <dd className="mt-0.5 whitespace-pre-wrap break-words text-sm text-slate-800">
                {f.type === "json" ? <pre className="overflow-x-auto rounded bg-slate-50 p-2 text-xs">{JSON.stringify(r[f.name], null, 2)}</pre> : renderCell(f, r)}
              </dd>
            </div>
          ))}
        </dl>
      </Card>
      {(RELATED[resource] ?? []).map((rel) => (
        <ResourceList key={rel.resource + rel.field} resource={rel.resource} fixedFilters={{ [rel.field]: id }} title={rel.title} compact />
      ))}
      {DOC_OWNERS[resource] && <DocumentsPanel ownerType={DOC_OWNERS[resource]} ownerId={id} />}
      {m.read_mode === "all" && <HistoryPanel resource={resource} id={id} />}
      <Modal open={editing} onOpenChange={setEditing} title={`Edit ${m.label.toLowerCase()}`} wide>
        <ResourceForm meta={m} initial={r} onSaved={() => { setEditing(false); row.refetch(); }} onCancel={() => setEditing(false)} />
      </Modal>
      {runner.dialog}
    </div>
  );
}
