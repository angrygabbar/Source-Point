"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Button, Card, EmptyState, ErrorState, Modal, PageHeader, SimpleTable, Skeleton, StatCard, StatusBadge, Tabs } from "@/components/ui";
import { useActionRunner } from "@/components/data/action-runner";
import { ResourceForm } from "@/components/data/resource-form";
import { ResourceList } from "@/components/data/resource-list";
import { DocumentsPanel } from "@/features/documents/documents-panel";
import { useMeta } from "@/hooks/use-meta";
import { useSession } from "@/hooks/use-session";
import { api, openFile } from "@/lib/api";
import { RESOURCE_ACTIONS } from "@/lib/resource-actions";
import { fmtDate, fmtDateTime, fmtMoney } from "@/lib/utils";
import type { Row } from "@/types";

/* eslint-disable @typescript-eslint/no-explicit-any */
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function TeacherProfilePage() {
  const { id } = useParams<{ id: string }>();
  const { me, can } = useSession();
  const qc = useQueryClient();
  const meta = useMeta("teachers");
  const q = useQuery({ queryKey: ["teacher-profile", id], queryFn: () => api<any>(`/teachers/${id}/profile`) });
  const [editing, setEditing] = useState(false);
  const runner = useActionRunner(() => qc.invalidateQueries({ queryKey: ["teacher-profile", id] }));
  const cur = me?.institute?.currency ?? "INR";
  if (q.isLoading) return <Skeleton className="h-96" />;
  if (q.isError || !q.data) return <ErrorState error={q.error} />;
  const p = q.data;
  const t = p.teacher as Row;
  const w = p.workload_this_month;
  const actions = (RESOURCE_ACTIONS.teachers ?? []).filter((a) => (!a.perms || can(...a.perms)) && (!a.when || a.when(t)));
  const staff = can("teachers.read");

  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={staff ? <Link href="/r/teachers" className="hover:underline">Teachers</Link> : undefined}
        title={<span className="flex items-center gap-2">{String(t.full_name)} <StatusBadge value={String(t.employment_status)} /></span>}
        description={`${t.teacher_code} · ${t.specialization ?? "—"} · joined ${fmtDate(String(t.joining_date))}`}
        actions={<>
          {actions.map((a) => <Button key={a.label} size="sm" variant={a.danger ? "danger" : "outline"} onClick={() => runner.run(a, t)}>{a.label}</Button>)}
          {meta.data?.can.update && <Button size="sm" onClick={() => setEditing(true)}>Edit</Button>}
        </>}
      />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Scheduled sessions (month)" value={w.scheduled_sessions} />
        <StatCard label="Conducted (month)" value={w.conducted_sessions} tone="green" />
        <StatCard label="Teaching hours (month)" value={w.teaching_hours} tone="teal" />
        <StatCard label="Substitute sessions" value={w.substitute_sessions} tone="amber" />
      </div>
      <Tabs tabs={[
        { value: "overview", label: "Overview", content: (
          <Card><dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{(meta.data?.fields ?? []).filter((f) => !f.system && f.type !== "json" && t[f.name] !== undefined).map((f) => (
            <div key={f.name}><dt className="text-xs text-slate-500">{f.label}</dt><dd className="text-sm">{f.type === "money" ? fmtMoney(String(t[f.name] ?? ""), cur) : String(t.display?.[f.name] ?? t[f.name] ?? "—")}</dd></div>
          ))}</dl></Card>
        ) },
        { value: "subjects", label: "Subjects & batches", content: (
          <Card bodyClass="p-0"><SimpleTable headers={["Batch", "Subject", "Role", "From", "To", "Active"]} rows={p.assignments.map((a: any) => [a.batch, a.subject, a.role, fmtDate(a.start_date), fmtDate(a.end_date), a.is_active ? "Yes" : "No"])} empty="No assignments" /></Card>
        ) },
        { value: "timetable", label: "Timetable", content: (
          <Card bodyClass="p-0"><SimpleTable headers={["Day", "Time", "Batch", "Subject"]} rows={p.timetable.map((s: any) => [DAYS[s.day_of_week], `${s.start_time}–${s.end_time}`, s.batch, s.subject])} empty="No recurring classes" /></Card>
        ) },
        { value: "attendance", label: "Attendance", content: (
          <Card>{Object.keys(p.attendance).length ? <div className="flex flex-wrap gap-3">{Object.entries(p.attendance).map(([k, v]) => <StatCard key={k} label={k.replace(/_/g, " ")} value={String(v)} />)}</div> : <EmptyState title="No attendance recorded" />}</Card>
        ) },
        { value: "classes", label: "Classes conducted", content: <ResourceList resource="class-sessions" fixedFilters={{ scheduled_teacher_id: id }} compact hideCreate /> },
        { value: "leave", label: "Leave", content: (
          <Card bodyClass="p-0"><SimpleTable headers={["Type", "From", "To", "Days", "Status", "Reason"]} rows={p.leaves.map((l: any) => [l.leave_type, fmtDate(l.start_date), fmtDate(l.end_date), l.days, <StatusBadge key={l.id} value={l.status} />, l.reason ?? ""])} empty="No leave records" /></Card>
        ) },
        { value: "payslips", label: "Compensation & payslips", hidden: !p.payslips, content: (
          <Card bodyClass="p-0"><SimpleTable headers={["Payslip", "Net", "Status", "Created", ""]} rows={(p.payslips ?? []).map((s: any) => [s.payslip_number, fmtMoney(s.net_amount, cur), <StatusBadge key="s" value={s.status} />, fmtDate(s.created_at), <Button key="p" size="sm" variant="ghost" onClick={() => openFile(`/payslips/${s.id}/pdf`)}>PDF</Button>])} empty="No payslips" /></Card>
        ) },
        { value: "documents", label: "Documents", hidden: !staff, content: <DocumentsPanel ownerType="teacher" ownerId={id} title="Employment documents" /> },
        { value: "history", label: "Activity history", hidden: !staff, content: (
          <Card>{(p.timeline ?? []).length ? p.timeline.map((x: any, i: number) => <p key={i} className="text-sm"><span className="font-medium">{x.action.replace(/_/g, " ")}</span> <span className="text-slate-500">· {x.actor ?? "system"} · {fmtDateTime(x.at, me?.institute?.timezone)}</span></p>) : <EmptyState title="No activity" />}
            {(p.employment_records ?? []).length > 0 && <div className="mt-4 border-t pt-3"><p className="mb-2 text-xs font-semibold uppercase text-slate-500">Employment records</p>{p.employment_records.map((r: any) => <p key={r.id} className="text-sm">{fmtDate(r.effective_date)} · {r.event_type.replace(/_/g, " ")} {r.details ? `· ${r.details}` : ""}</p>)}</div>}
          </Card>
        ) },
      ]} />
      <Modal open={editing} onOpenChange={setEditing} title="Edit teacher" wide>
        {meta.data && <ResourceForm meta={meta.data} initial={t} onSaved={() => { setEditing(false); q.refetch(); }} onCancel={() => setEditing(false)} />}
      </Modal>
      {runner.dialog}
    </div>
  );
}
