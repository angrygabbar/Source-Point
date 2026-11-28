"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, EmptyState, ErrorState, Field, Input, Menu, Modal, PageHeader, Select, SimpleTable, Skeleton, StatCard, StatusBadge, Tabs } from "@/components/ui";
import { useActionRunner } from "@/components/data/action-runner";
import { RefSelect } from "@/components/data/ref-select";
import { ResourceForm } from "@/components/data/resource-form";
import { DocumentsPanel } from "@/features/documents/documents-panel";
import { useMeta } from "@/hooks/use-meta";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage, openFile } from "@/lib/api";
import { RESOURCE_ACTIONS } from "@/lib/resource-actions";
import { fmtDate, fmtDateTime, fmtMoney, todayISO } from "@/lib/utils";
import type { Row } from "@/types";

/* eslint-disable @typescript-eslint/no-explicit-any */
type Profile = any;

export default function StudentProfilePage() {
  const { id } = useParams<{ id: string }>();
  const { me, can } = useSession();
  const qc = useQueryClient();
  const meta = useMeta("students");
  const q = useQuery({ queryKey: ["student-profile", id], queryFn: () => api<Profile>(`/students/${id}/profile`) });
  const [editing, setEditing] = useState(false);
  const [dialog, setDialog] = useState<null | "enroll" | "transfer" | "branch" | "parent">(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const runner = useActionRunner(() => qc.invalidateQueries({ queryKey: ["student-profile", id] }));
  const cur = me?.institute?.currency ?? "INR";
  const tz = me?.institute?.timezone;

  if (q.isLoading) return <Skeleton className="h-96" />;
  if (q.isError || !q.data) return <ErrorState error={q.error} />;
  const p = q.data;
  const s = p.student as Row;
  const att = p.attendance.summary;
  const staff = can("students.read");
  const actions = (RESOURCE_ACTIONS.students ?? []).filter((a) => (!a.perms || can(...a.perms)) && (!a.when || a.when(s)));

  const submit = async (path: string, body: unknown, msg: string) => {
    setBusy(true);
    try {
      await api(path, { method: "POST", body });
      toast.success(msg);
      setDialog(null);
      setForm({});
      q.refetch();
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const activeEnrollments = p.enrollments.filter((e: any) => e.status === "active");

  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={<Link href="/r/students" className="hover:underline">Students</Link>}
        title={<span className="flex items-center gap-2">{String(s.full_name)} <StatusBadge value={String(s.status)} /></span>}
        description={`${s.student_code} · admitted ${fmtDate(String(s.admission_date))}`}
        actions={
          <>
            {staff && can("enrollments.write") && (
              <Menu trigger={<Button variant="outline" size="sm">Enrollment</Button>} items={[
                { label: "Enroll in batch", onClick: () => { setForm({ start_date: todayISO() }); setDialog("enroll"); } },
                { label: "Transfer batch / course", onClick: () => { setForm({ effective_date: todayISO() }); setDialog("transfer"); }, hidden: !activeEnrollments.length },
                { label: "Transfer branch", onClick: () => { setForm({ effective_date: todayISO() }); setDialog("branch"); }, hidden: !can("students.write") },
                { label: "Link parent / guardian", onClick: () => { setForm({ relation: "guardian" }); setDialog("parent"); }, hidden: !can("parents.write") },
              ]} />
            )}
            <Menu trigger={<Button variant="outline" size="sm">Documents</Button>} items={[
              ...actions.filter((a) => a.kind === "pdf").map((a) => ({ label: a.label, onClick: () => runner.run(a, s) })),
              { label: "Marksheet", onClick: () => openFile(`/students/${id}/marksheet.pdf`).catch((e) => toast.error(errorMessage(e))) },
              { label: "Report card", onClick: () => openFile(`/students/${id}/report-card.pdf`).catch((e) => toast.error(errorMessage(e))) },
            ]} />
            {actions.filter((a) => a.kind === "post").map((a) => <Button key={a.label} size="sm" variant={a.danger ? "danger" : "outline"} onClick={() => runner.run(a, s)}>{a.label}</Button>)}
            {meta.data?.can.update && <Button size="sm" onClick={() => setEditing(true)}>Edit</Button>}
          </>
        }
      />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Attendance" value={att.percentage !== null ? `${att.percentage}%` : "—"} hint={`${att.present + att.late}/${att.total_sessions} sessions`} tone="green" />
        <StatCard label="Absent / excused / leave" value={`${att.absent} / ${att.excused} / ${att.approved_leave}`} tone="amber" />
        <StatCard label="Active batches" value={activeEnrollments.length} />
        {p.fees && <StatCard label="Outstanding" value={fmtMoney(p.fees.balance.outstanding, cur)} hint={`Advance ${fmtMoney(p.fees.balance.advance, cur)}`} tone="red" />}
      </div>
      <Tabs
        tabs={[
          { value: "overview", label: "Overview", content: (
            <div className="grid gap-4 lg:grid-cols-2">
              <Card title="Current enrollments">{activeEnrollments.length ? activeEnrollments.map((e: any) => <p key={e.id} className="flex justify-between py-1 text-sm"><span>{e.batch} · {e.course}</span><span className="text-slate-500">since {fmtDate(e.start_date)}</span></p>) : <EmptyState title="Not enrolled" />}</Card>
              <Card title="Parents & guardians">{p.parents.length ? p.parents.map((g: any) => <p key={g.id} className="flex justify-between py-1 text-sm"><span>{g.full_name} {g.is_primary && <Badge tone="indigo">primary</Badge>}</span><span className="text-slate-500">{g.relation} · {g.phone ?? "—"}</span></p>) : <EmptyState title={`Guardian on record: ${s.guardian_name ?? "—"}`} />}</Card>
              <Card title="Attendance by subject" bodyClass="p-0"><SimpleTable headers={["Subject", "Sessions", "Present", "%"]} rows={p.attendance.by_subject.map((x: any) => [x.subject, x.total, x.present, x.percentage ?? "—"])} /></Card>
              <Card title="Latest results" bodyClass="p-0"><SimpleTable headers={["Exam", "Subject", "Marks", "Grade"]} rows={p.results.slice(0, 6).map((r: any) => [r.exam, r.subject, r.is_absent ? "AB" : `${r.marks ?? "—"}/${r.max_marks}`, r.grade ?? "—"])} empty="No results" /></Card>
            </div>
          ) },
          { value: "personal", label: "Personal details", content: (
            <Card><dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{(meta.data?.fields ?? []).filter((f) => !f.system && f.type !== "json").map((f) => (
              <div key={f.name}><dt className="text-xs text-slate-500">{f.label}</dt><dd className="text-sm">{String(s.display?.[f.name] ?? s[f.name] ?? "—")}</dd></div>
            ))}</dl></Card>
          ) },
          { value: "enrollments", label: "Enrollment history", content: (
            <Card bodyClass="p-0"><SimpleTable headers={["Batch", "Course", "Start", "End", "Status"]} rows={p.enrollments.map((e: any) => [e.batch, e.course, fmtDate(e.start_date), fmtDate(e.end_date), <StatusBadge key={e.id} value={e.status} />])} /></Card>
          ) },
          { value: "attendance", label: "Attendance", content: (
            <Card bodyClass="p-0"><SimpleTable headers={["Date", "Subject", "Status", "Remarks"]} rows={p.attendance.recent.map((a: any, i: number) => [fmtDate(a.date), a.subject, <StatusBadge key={i} value={a.status} />, a.remarks ?? ""])} empty="No attendance recorded" /></Card>
          ) },
          { value: "homework", label: "Homework", content: (
            <Card bodyClass="p-0"><SimpleTable headers={["Assignment", "Due", "Status", "Marks", "Feedback"]} rows={p.homework.map((h: any) => [<Link key={h.assignment_id} href={`/assignments/${h.assignment_id}`} className="text-brand-800 hover:underline">{h.title}</Link>, fmtDateTime(h.due_at, tz), <StatusBadge key="s" value={h.is_late && h.status !== "not_submitted" ? "late" : h.status} />, h.marks !== null ? `${h.marks}/${h.max_marks}` : "—", h.feedback ?? ""])} empty="No homework" /></Card>
          ) },
          { value: "exams", label: "Examinations", content: (
            <Card bodyClass="p-0"><SimpleTable headers={["Exam", "Subject", "Date", "Marks", "%", "Grade", "Rank", "Status", "Recommendation"]} rows={p.results.map((r: any, i: number) => [r.exam, r.subject, fmtDate(r.date), r.is_absent ? "AB" : `${r.marks ?? "—"}/${r.max_marks}`, r.percentage ?? "—", r.grade ?? "—", r.rank ?? "—", <StatusBadge key={i} value={r.status} />, r.remedial_recommendation ?? ""])} empty="No results" /></Card>
          ) },
          { value: "materials", label: "Materials", hidden: !staff, content: (
            <Card bodyClass="p-0"><SimpleTable headers={["Material", "Downloaded"]} rows={(p.material_access ?? []).map((m: any) => [m.material, fmtDateTime(m.downloaded_at, tz)])} empty="No material downloads recorded" /></Card>
          ) },
          { value: "fees", label: "Fees & payments", hidden: !p.fees, content: p.fees && (
            <div className="space-y-4">
              <div className="flex gap-2">
                <Link href={`/finance/ledger/${id}`}><Button size="sm" variant="outline">Open ledger</Button></Link>
                {can("payments.write") && <Link href={`/finance/collect?student=${id}`}><Button size="sm">Collect payment</Button></Link>}
                {can("invoices.write") && <Link href={`/finance/invoices/new?student=${id}`}><Button size="sm" variant="outline">New invoice</Button></Link>}
              </div>
              <Card title="Invoices" bodyClass="p-0"><SimpleTable headers={["Invoice", "Issued", "Due", "Total", "Balance", "Status"]} rows={p.fees.invoices.map((i: any) => [<Link key={i.id} href={`/finance/invoices/${i.id}`} className="text-brand-800 hover:underline">{i.invoice_number ?? "Draft"}</Link>, fmtDate(i.issue_date), fmtDate(i.due_date), fmtMoney(i.total, cur), fmtMoney(i.balance_due, cur), <StatusBadge key="s" value={i.status} />])} empty="No invoices" /></Card>
              <Card title="Payments" bodyClass="p-0"><SimpleTable headers={["Receipt", "Date", "Amount", "Method", "Status", ""]} rows={p.fees.payments.map((x: any) => [x.receipt_number, fmtDate(x.paid_at), fmtMoney(x.amount, cur), x.method.replace(/_/g, " "), <StatusBadge key="s" value={x.status} />, <Button key="r" size="sm" variant="ghost" onClick={() => openFile(`/payments/${x.id}/receipt.pdf`)}>Receipt</Button>])} empty="No payments" /></Card>
              <Card title="Fee agreements" bodyClass="p-0"><SimpleTable headers={["Billing", "Amount", "Discount", "From", "To", "Status"]} rows={p.fees.agreements.map((a: any) => [a.billing_type, fmtMoney(a.amount, cur), a.discount_type === "none" ? "—" : `${a.discount_value} (${a.discount_type})`, fmtDate(a.effective_from), fmtDate(a.effective_to), <StatusBadge key="s" value={a.status} />])} empty="No agreements" /></Card>
            </div>
          ) },
          { value: "documents", label: "Documents", hidden: !staff, content: <DocumentsPanel ownerType="student" ownerId={id} /> },
          { value: "timeline", label: "Activity timeline", hidden: !staff, content: (
            <Card>{(p.timeline ?? []).length ? <ol className="space-y-2">{p.timeline.map((t: any, i: number) => <li key={i} className="text-sm"><span className="font-medium">{t.action.replace(/_/g, " ")}</span> <span className="text-slate-500">· {t.entity} · {t.actor ?? "system"} · {fmtDateTime(t.at, tz)}</span>{t.reason && <p className="text-xs text-amber-700">{t.reason}</p>}</li>)}</ol> : <EmptyState title="No activity" />}</Card>
          ) },
        ]}
      />
      <Modal open={editing} onOpenChange={setEditing} title="Edit student" wide>
        {meta.data && <ResourceForm meta={meta.data} initial={s} onSaved={() => { setEditing(false); q.refetch(); }} onCancel={() => setEditing(false)} />}
      </Modal>
      <Modal open={dialog === "enroll"} onOpenChange={() => setDialog(null)} title="Enroll in batch"
        footer={<Button loading={busy} disabled={!form.batch_id} onClick={() => submit("/enrollments", { student_id: id, batch_id: form.batch_id, start_date: form.start_date }, "Enrolled")}>Enroll</Button>}>
        <div className="space-y-3">
          <Field label="Batch" required><RefSelect resource="batches" value={form.batch_id ?? null} onChange={(v) => setForm({ ...form, batch_id: v ?? "" })} /></Field>
          <Field label="Start date" required><Input type="date" value={form.start_date ?? ""} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></Field>
        </div>
      </Modal>
      <Modal open={dialog === "transfer"} onOpenChange={() => setDialog(null)} title="Transfer batch / course"
        footer={<Button loading={busy} disabled={!form.enrollment_id || !form.to_batch_id || (form.reason ?? "").length < 3} onClick={() => submit(`/students/${id}/transfer-batch`, form, "Transferred")}>Transfer</Button>}>
        <div className="space-y-3">
          <Field label="From enrollment" required><Select value={form.enrollment_id ?? ""} onChange={(e) => setForm({ ...form, enrollment_id: e.target.value })}><option value="">Select…</option>{activeEnrollments.map((e: any) => <option key={e.id} value={e.id}>{e.batch}</option>)}</Select></Field>
          <Field label="To batch" required><RefSelect resource="batches" value={form.to_batch_id ?? null} onChange={(v) => setForm({ ...form, to_batch_id: v ?? "" })} /></Field>
          <Field label="Effective date" required><Input type="date" value={form.effective_date ?? ""} onChange={(e) => setForm({ ...form, effective_date: e.target.value })} /></Field>
          <Field label="Reason" required><Input value={form.reason ?? ""} onChange={(e) => setForm({ ...form, reason: e.target.value })} /></Field>
        </div>
      </Modal>
      <Modal open={dialog === "branch"} onOpenChange={() => setDialog(null)} title="Transfer branch"
        footer={<Button loading={busy} disabled={!form.branch_id || (form.reason ?? "").length < 3} onClick={() => submit(`/students/${id}/transfer-branch`, form, "Branch updated")}>Transfer</Button>}>
        <div className="space-y-3">
          <Field label="New branch" required><RefSelect resource="branches" value={form.branch_id ?? null} onChange={(v) => setForm({ ...form, branch_id: v ?? "" })} /></Field>
          <Field label="Effective date" required><Input type="date" value={form.effective_date ?? ""} onChange={(e) => setForm({ ...form, effective_date: e.target.value })} /></Field>
          <Field label="Reason" required><Input value={form.reason ?? ""} onChange={(e) => setForm({ ...form, reason: e.target.value })} /></Field>
          <p className="text-xs text-slate-500">Active enrollments are closed as transferred; enroll the student into batches of the new branch afterwards.</p>
        </div>
      </Modal>
      <Modal open={dialog === "parent"} onOpenChange={() => setDialog(null)} title="Link parent / guardian"
        footer={<Button loading={busy} disabled={!form.parent_id && !form.full_name} onClick={() => submit(`/students/${id}/parents`, { ...form, parent_id: form.parent_id || undefined, email: form.email || undefined }, "Linked")}>Link</Button>}>
        <div className="space-y-3">
          <Field label="Existing parent"><RefSelect resource="parents" value={form.parent_id ?? null} onChange={(v) => setForm({ ...form, parent_id: v ?? "" })} /></Field>
          <p className="text-center text-xs text-slate-400">— or create new —</p>
          <Field label="Full name"><Input value={form.full_name ?? ""} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Phone"><Input value={form.phone ?? ""} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
            <Field label="Email"><Input type="email" value={form.email ?? ""} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
          </div>
          <Field label="Relation"><Select value={form.relation} onChange={(e) => setForm({ ...form, relation: e.target.value })}>{["father", "mother", "guardian", "other"].map((r) => <option key={r}>{r}</option>)}</Select></Field>
        </div>
      </Modal>
      {runner.dialog}
    </div>
  );
}
