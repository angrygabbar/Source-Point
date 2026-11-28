"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, BookOpenCheck, CalendarCheck, CheckCircle2, ClipboardCheck, GraduationCap, IndianRupee, Layers, UserCheck, Users, Wallet } from "lucide-react";
import Link from "next/link";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, EmptyState, ErrorState, PageHeader, SimpleTable, Skeleton, StatCard, StatusBadge } from "@/components/ui";
import { SessionRow, type SessionItem } from "@/features/sessions/session-row";
import { useSession } from "@/hooks/use-session";
import { api } from "@/lib/api";
import { fmtDate, fmtDateTime, fmtMoney } from "@/lib/utils";

interface AdminData {
  date: string;
  stats: Record<string, unknown> & {
    active_students: number; active_teachers: number; active_batches: number; classes_today: number; classes_completed_today: number;
    student_attendance_today: { marked: number; present: number; percentage: number | null };
    teacher_attendance_today: { marked: number; present: number };
    upcoming_assignments: number; pending_evaluations: number; monthly_collection?: string; outstanding_fees?: string;
  };
  charts: {
    attendance_trend: { month: string; percentage: number | null }[];
    revenue_trend: { month: string; amount: number }[];
    subject_attendance: { subject: string; percentage: number | null }[];
    batch_strength: { batch: string; students: number; capacity: number }[];
    teacher_workload: { teacher: string; sessions: number }[];
    admission_funnel?: { stage: string; count: number }[];
  };
  sections: {
    todays_timetable: SessionItem[];
    students_needing_attention: { student_id: string; full_name: string; student_code: string; percentage: number; sessions: number }[];
    recent_uploads: { id: string; title: string; category: string; created_at: string }[];
    recent_activity: { at: string; actor: string; action: string; entity: string }[];
    upcoming_fee_dues?: { id: string; invoice_number: string; student: string; due_date: string; balance_due: string }[];
    recent_transactions?: { id: string; receipt_number: string; student: string; amount: string; method: string; paid_at: string; status: string }[];
  };
  onboarding: Record<string, boolean>;
}

const ONBOARD: [string, string, string][] = [
  ["branches", "Add branches", "/r/branches"],
  ["academic_year", "Create an academic year", "/r/academic-years"],
  ["courses", "Add courses", "/r/courses"],
  ["subjects", "Add subjects", "/r/subjects"],
  ["batches", "Create batches", "/r/batches"],
  ["teachers", "Add teachers", "/r/teachers"],
  ["students", "Add or import students", "/r/students"],
  ["schedules", "Build the timetable", "/r/schedules"],
  ["fee_plans", "Define fee plans", "/r/fee-plans"],
];

function ChartCard({ title, empty, children }: { title: string; empty: boolean; children: React.ReactElement }) {
  return (
    <Card title={title}>
      {empty ? <EmptyState title="No data yet" description="This chart fills in as records are captured." /> : (
        <div className="h-56"><ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer></div>
      )}
    </Card>
  );
}

export function AdminDashboard() {
  const { me } = useSession();
  const tz = me?.institute?.timezone;
  const cur = me?.institute?.currency ?? "INR";
  const q = useQuery({ queryKey: ["dash-admin"], queryFn: () => api<AdminData>("/dashboard/admin"), refetchInterval: 120_000 });
  if (q.isLoading) return <div className="grid gap-4 md:grid-cols-4">{Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-24" />)}</div>;
  if (q.isError || !q.data) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const d = q.data;
  const s = d.stats;
  const pending = ONBOARD.filter(([k]) => !d.onboarding[k]);
  return (
    <div className="space-y-5">
      <PageHeader title={`Welcome, ${me?.user.full_name.split(" ")[0]}`} description={`Institute overview for ${fmtDate(d.date)}`} />
      {pending.length > 0 && (
        <Card title="Getting started" className="border-indigo-200 bg-indigo-50/40">
          <p className="mb-3 text-sm text-slate-600">Complete these steps to activate all dashboards. Each links to the relevant module.</p>
          <div className="flex flex-wrap gap-2">
            {ONBOARD.map(([k, label, href]) => (
              <Link key={k} href={href} className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${d.onboarding[k] ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-300 bg-white text-slate-700 hover:border-brand-500"}`}>
                {d.onboarding[k] && <CheckCircle2 className="h-3.5 w-3.5" />} {label}
              </Link>
            ))}
          </div>
        </Card>
      )}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <StatCard label="Active students" value={s.active_students} icon={<GraduationCap className="h-5 w-5" />} />
        <StatCard label="Active teachers" value={s.active_teachers} icon={<Users className="h-5 w-5" />} tone="teal" />
        <StatCard label="Active batches" value={s.active_batches} icon={<Layers className="h-5 w-5" />} />
        <StatCard label="Classes today" value={s.classes_today} hint={`${s.classes_completed_today} completed`} icon={<CalendarCheck className="h-5 w-5" />} tone="green" />
        <StatCard label="Student attendance today" value={s.student_attendance_today.percentage !== null ? `${s.student_attendance_today.percentage}%` : "—"} hint={`${s.student_attendance_today.present}/${s.student_attendance_today.marked} present`} icon={<UserCheck className="h-5 w-5" />} tone="green" />
        <StatCard label="Teacher attendance today" value={`${s.teacher_attendance_today.present}/${s.teacher_attendance_today.marked}`} hint="present / marked" icon={<ClipboardCheck className="h-5 w-5" />} tone="teal" />
        {s.monthly_collection !== undefined && <StatCard label="Collected this month" value={fmtMoney(s.monthly_collection, cur)} icon={<IndianRupee className="h-5 w-5" />} tone="green" />}
        {s.outstanding_fees !== undefined && <StatCard label="Outstanding fees" value={fmtMoney(s.outstanding_fees, cur)} icon={<Wallet className="h-5 w-5" />} tone="amber" />}
        <StatCard label="Assignments due (7 days)" value={s.upcoming_assignments} icon={<BookOpenCheck className="h-5 w-5" />} />
        <StatCard label="Pending evaluations" value={s.pending_evaluations} icon={<AlertTriangle className="h-5 w-5" />} tone="amber" />
      </div>
      <div className="grid gap-4 xl:grid-cols-3">
        <Card title="Today's timetable" className="xl:col-span-2" actions={<Link href="/timetable" className="text-xs font-medium text-brand-800">Open calendar</Link>}>
          {d.sections.todays_timetable.length ? (
            <div className="divide-y divide-slate-100">{d.sections.todays_timetable.map((x) => <SessionRow key={x.id} s={x} tz={tz} extra={<StatusBadge value={x.attendance_state} />} />)}</div>
          ) : <EmptyState title="No classes today" description="Generate sessions from schedules or add one-time classes." />}
        </Card>
        <Card title="Students needing attendance attention">
          {d.sections.students_needing_attention.length ? (
            <ul className="space-y-2">{d.sections.students_needing_attention.map((x) => (
              <li key={x.student_id} className="flex items-center justify-between text-sm">
                <Link href={`/students/${x.student_id}`} className="font-medium text-brand-800 hover:underline">{x.full_name}</Link>
                <span className="text-red-600">{x.percentage}% <span className="text-xs text-slate-400">({x.sessions})</span></span>
              </li>))}</ul>
          ) : <EmptyState title="All students above threshold" />}
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Monthly attendance trend (%)" empty={!d.charts.attendance_trend.some((x) => x.percentage !== null)}>
          <LineChart data={d.charts.attendance_trend}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="month" fontSize={11} /><YAxis domain={[0, 100]} fontSize={11} /><Tooltip /><Line type="monotone" dataKey="percentage" stroke="#1e2a78" strokeWidth={2} /></LineChart>
        </ChartCard>
        {d.charts.revenue_trend.length > 0 && (
          <ChartCard title="Collections trend" empty={!d.charts.revenue_trend.some((x) => x.amount > 0)}>
            <BarChart data={d.charts.revenue_trend}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="month" fontSize={11} /><YAxis fontSize={11} /><Tooltip formatter={(v: number) => fmtMoney(v, cur)} /><Bar dataKey="amount" fill="#0d9488" radius={[4, 4, 0, 0]} /></BarChart>
          </ChartCard>
        )}
        <ChartCard title="Subject-wise attendance (30 days)" empty={!d.charts.subject_attendance.length}>
          <BarChart data={d.charts.subject_attendance}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="subject" fontSize={11} /><YAxis domain={[0, 100]} fontSize={11} /><Tooltip /><Bar dataKey="percentage" fill="#2563eb" radius={[4, 4, 0, 0]} /></BarChart>
        </ChartCard>
        <ChartCard title="Batch strength" empty={!d.charts.batch_strength.length}>
          <BarChart data={d.charts.batch_strength}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="batch" fontSize={11} /><YAxis fontSize={11} /><Tooltip /><Bar dataKey="students" fill="#1e2a78" radius={[4, 4, 0, 0]} /><Bar dataKey="capacity" fill="#c7d2fe" radius={[4, 4, 0, 0]} /></BarChart>
        </ChartCard>
        <ChartCard title="Teacher workload (sessions this month)" empty={!d.charts.teacher_workload.length}>
          <BarChart data={d.charts.teacher_workload} layout="vertical"><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis type="number" fontSize={11} /><YAxis type="category" dataKey="teacher" width={110} fontSize={11} /><Tooltip /><Bar dataKey="sessions" fill="#0d9488" radius={[0, 4, 4, 0]} /></BarChart>
        </ChartCard>
        {d.charts.admission_funnel && (
          <ChartCard title="Admission pipeline" empty={!d.charts.admission_funnel.length}>
            <BarChart data={d.charts.admission_funnel}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="stage" fontSize={11} /><YAxis fontSize={11} allowDecimals={false} /><Tooltip /><Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]} /></BarChart>
          </ChartCard>
        )}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {d.sections.upcoming_fee_dues && (
          <Card title="Upcoming fee dues (14 days)" bodyClass="p-0">
            <SimpleTable headers={["Invoice", "Student", "Due", "Balance"]} empty="No dues in the next 14 days"
              rows={d.sections.upcoming_fee_dues.map((x) => [<Link key={x.id} className="text-brand-800 hover:underline" href={`/finance/invoices/${x.id}`}>{x.invoice_number}</Link>, x.student, fmtDate(x.due_date), fmtMoney(x.balance_due, cur)])} />
          </Card>
        )}
        {d.sections.recent_transactions && (
          <Card title="Recent transactions" bodyClass="p-0">
            <SimpleTable headers={["Receipt", "Student", "Amount", "Method", "Status"]} empty="No payments yet"
              rows={d.sections.recent_transactions.map((x) => [x.receipt_number, x.student, fmtMoney(x.amount, cur), x.method.replace(/_/g, " "), <StatusBadge key={x.id} value={x.status} />])} />
          </Card>
        )}
        <Card title="Recent uploads">
          {d.sections.recent_uploads.length ? <ul className="space-y-1.5 text-sm">{d.sections.recent_uploads.map((m) => <li key={m.id} className="flex justify-between"><span>{m.title}</span><span className="text-xs text-slate-400">{fmtDate(m.created_at)}</span></li>)}</ul> : <EmptyState title="No materials uploaded yet" />}
        </Card>
        <Card title="Recent activity">
          {d.sections.recent_activity.length ? <ul className="space-y-1.5 text-sm">{d.sections.recent_activity.map((a, i) => <li key={i} className="flex justify-between gap-2"><span className="truncate"><span className="font-medium">{a.actor ?? "system"}</span> · {a.action.replace(/_/g, " ")} · {a.entity.replace(/_/g, " ")}</span><span className="shrink-0 text-xs text-slate-400">{fmtDateTime(a.at, tz)}</span></li>)}</ul> : <EmptyState title="No activity yet" />}
        </Card>
      </div>
    </div>
  );
}
