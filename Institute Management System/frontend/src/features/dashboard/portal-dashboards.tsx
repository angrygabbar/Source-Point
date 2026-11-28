"use client";

import { useQuery } from "@tanstack/react-query";
import { BookOpenCheck, CalendarCheck, Clock, Users } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge, Card, EmptyState, ErrorState, PageHeader, Select, Skeleton, StatCard, StatusBadge } from "@/components/ui";
import { SessionRow, type SessionItem } from "@/features/sessions/session-row";
import { useSession } from "@/hooks/use-session";
import { api } from "@/lib/api";
import { fmtDate, fmtDateTime, fmtMoney } from "@/lib/utils";

interface TeacherData {
  date: string;
  todays_classes: SessionItem[];
  upcoming_classes: SessionItem[];
  attendance_pending: SessionItem[];
  batches_subjects: { batch: string; subject: string; batch_id: string }[];
  student_count: number;
  evaluations_pending: { assignment_id: string; title: string; count: number }[];
  upcoming_deadlines: { id: string; title: string; due_at: string }[];
  recent_materials: { id: string; title: string; created_at: string }[];
  workload: { sessions_this_month: number; teaching_hours_this_month: number };
  leaves: { id: string; leave_type: string; start_date: string; end_date: string; status: string }[];
}

function Announcements() {
  const q = useQuery({ queryKey: ["ann-feed"], queryFn: () => api<{ id: string; title: string; body: string; priority: string; published_at: string }[]>("/announcements/feed/mine") });
  return (
    <Card title="Announcements" actions={<Link href="/announcements" className="text-xs font-medium text-brand-800">All</Link>}>
      {q.data?.length ? (
        <ul className="space-y-2">{q.data.slice(0, 5).map((a) => (
          <li key={a.id} className="text-sm"><p className="font-medium text-slate-800">{a.title} {a.priority !== "normal" && <Badge tone={a.priority === "urgent" ? "red" : "amber"}>{a.priority}</Badge>}</p><p className="line-clamp-2 text-xs text-slate-500">{a.body}</p></li>
        ))}</ul>
      ) : <EmptyState title="No announcements" />}
    </Card>
  );
}

export function TeacherDashboard() {
  const { me } = useSession();
  const tz = me?.institute?.timezone;
  const q = useQuery({ queryKey: ["dash-teacher"], queryFn: () => api<TeacherData>("/dashboard/teacher") });
  if (q.isLoading) return <Skeleton className="h-64" />;
  if (q.isError || !q.data) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const d = q.data;
  return (
    <div className="space-y-5">
      <PageHeader title={`Good day, ${me?.user.full_name.split(" ")[0]}`} description={fmtDate(d.date)} />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Classes today" value={d.todays_classes.length} icon={<CalendarCheck className="h-5 w-5" />} />
        <StatCard label="Attendance pending" value={d.attendance_pending.length} icon={<Clock className="h-5 w-5" />} tone="amber" />
        <StatCard label="My students" value={d.student_count} icon={<Users className="h-5 w-5" />} tone="teal" />
        <StatCard label="Teaching hours (month)" value={d.workload.teaching_hours_this_month} hint={`${d.workload.sessions_this_month} sessions completed`} icon={<BookOpenCheck className="h-5 w-5" />} tone="green" />
      </div>
      <div className="grid gap-4 xl:grid-cols-3">
        <Card title="Today's classes" className="xl:col-span-2">
          {d.todays_classes.length ? d.todays_classes.map((s) => <SessionRow key={s.id} s={s} tz={tz} />) : <EmptyState title="No classes today" />}
        </Card>
        <Card title="Attendance pending">
          {d.attendance_pending.length ? d.attendance_pending.map((s) => <SessionRow key={s.id} s={s} tz={tz} showDate extra={<StatusBadge value={s.attendance_state} />} />) : <EmptyState title="All attendance submitted" />}
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Upcoming classes">
          {d.upcoming_classes.length ? d.upcoming_classes.map((s) => <SessionRow key={s.id} s={s} tz={tz} showDate />) : <EmptyState title="Nothing scheduled this week" />}
        </Card>
        <Card title="Homework to evaluate">
          {d.evaluations_pending.length ? <ul className="space-y-2">{d.evaluations_pending.map((e) => <li key={e.assignment_id} className="flex justify-between text-sm"><Link className="text-brand-800 hover:underline" href={`/assignments/${e.assignment_id}`}>{e.title}</Link><Badge tone="amber">{e.count}</Badge></li>)}</ul> : <EmptyState title="Nothing pending" />}
          {d.upcoming_deadlines.length > 0 && (
            <div className="mt-4 border-t border-slate-100 pt-3">
              <p className="mb-2 text-xs font-semibold uppercase text-slate-500">Upcoming deadlines</p>
              {d.upcoming_deadlines.map((a) => <p key={a.id} className="flex justify-between text-sm"><Link href={`/assignments/${a.id}`} className="hover:underline">{a.title}</Link><span className="text-xs text-slate-500">{fmtDateTime(a.due_at, tz)}</span></p>)}
            </div>
          )}
        </Card>
        <Card title="My batches & subjects">
          {d.batches_subjects.length ? <ul className="space-y-1.5 text-sm">{d.batches_subjects.map((b, i) => <li key={i} className="flex justify-between"><span>{b.batch}</span><span className="text-slate-500">{b.subject}</span></li>)}</ul> : <EmptyState title="No active assignments" />}
        </Card>
        <Card title="Recent materials">
          {d.recent_materials.length ? d.recent_materials.map((m) => <p key={m.id} className="flex justify-between text-sm"><span>{m.title}</span><span className="text-xs text-slate-400">{fmtDate(m.created_at)}</span></p>) : <EmptyState title="No materials yet" action={<Link href="/materials" className="text-sm text-brand-800">Upload</Link>} />}
        </Card>
        <Card title="Leave status" actions={<Link href="/r/teacher-leaves" className="text-xs font-medium text-brand-800">Apply</Link>}>
          {d.leaves.length ? d.leaves.map((l) => <p key={l.id} className="flex justify-between text-sm"><span>{l.leave_type} · {fmtDate(l.start_date)}–{fmtDate(l.end_date)}</span><StatusBadge value={l.status} /></p>) : <EmptyState title="No leave requests" />}
        </Card>
        <Announcements />
      </div>
    </div>
  );
}

interface StudentData {
  student: { id: string; full_name: string; student_code: string };
  todays_classes: SessionItem[];
  week_timetable: SessionItem[];
  attendance: { total_sessions: number; present: number; late: number; absent: number; excused: number; approved_leave: number; percentage: number | null };
  recent_absences: { date: string; subject: string; status: string }[];
  pending_homework: { id: string; title: string; due_at: string; status: string; overdue: boolean }[];
  grades_feedback: { title: string; marks: string; max_marks: string; feedback: string | null; at: string }[];
  results: { exam: string; subject: string; marks: string | null; max_marks: string; percentage: string | null; grade: string | null }[];
  recent_materials: { id: string; title: string; category: string; created_at: string }[];
  fees?: {
    balance: { outstanding: string; advance: string };
    open_invoices: { id: string; invoice_number: string; due_date: string; balance_due: string; status: string }[];
    recent_payments: { id: string; receipt_number: string; paid_at: string; amount: string; method: string }[];
  };
}

export function StudentView({ d }: { d: StudentData }) {
  const { me } = useSession();
  const tz = me?.institute?.timezone;
  const cur = me?.institute?.currency ?? "INR";
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Attendance" value={d.attendance.percentage !== null ? `${d.attendance.percentage}%` : "—"} hint={`${d.attendance.present + d.attendance.late}/${d.attendance.total_sessions} sessions · excused ${d.attendance.excused} · leave ${d.attendance.approved_leave}`} icon={<CalendarCheck className="h-5 w-5" />} tone="green" />
        <StatCard label="Pending homework" value={d.pending_homework.length} icon={<BookOpenCheck className="h-5 w-5" />} tone="amber" />
        <StatCard label="Classes today" value={d.todays_classes.length} icon={<Clock className="h-5 w-5" />} />
        {d.fees && <StatCard label="Fees outstanding" value={fmtMoney(d.fees.balance.outstanding, cur)} hint={Number(d.fees.balance.advance) > 0 ? `Advance ${fmtMoney(d.fees.balance.advance, cur)}` : undefined} tone="red" />}
      </div>
      <div className="grid gap-4 xl:grid-cols-3">
        <Card title="This week's timetable" className="xl:col-span-2">
          {d.week_timetable.length ? d.week_timetable.map((s) => <SessionRow key={s.id} s={s} tz={tz} showDate />) : <EmptyState title="No classes scheduled this week" />}
        </Card>
        <Card title="Pending homework">
          {d.pending_homework.length ? d.pending_homework.map((h) => (
            <Link key={h.id} href={`/assignments/${h.id}`} className="flex items-center justify-between rounded-md px-1 py-1.5 text-sm hover:bg-slate-50">
              <span>{h.title}</span><span className={h.overdue ? "text-xs text-red-600" : "text-xs text-slate-500"}>{fmtDateTime(h.due_at, tz)}</span>
            </Link>)) : <EmptyState title="All caught up" />}
        </Card>
        <Card title="Grades & teacher feedback">
          {d.grades_feedback.length ? d.grades_feedback.map((g, i) => (
            <div key={i} className="border-b border-slate-100 py-2 text-sm last:border-0"><p className="flex justify-between"><span className="font-medium">{g.title}</span><span>{g.marks}/{g.max_marks}</span></p>{g.feedback && <p className="text-xs text-slate-500">{g.feedback}</p>}</div>
          )) : <EmptyState title="No graded work yet" />}
        </Card>
        <Card title="Exam results">
          {d.results.length ? d.results.map((r, i) => <p key={i} className="flex justify-between py-1 text-sm"><span>{r.exam} · {r.subject}</span><span>{r.marks ?? "AB"}/{r.max_marks} {r.grade && <Badge tone="indigo">{r.grade}</Badge>}</span></p>) : <EmptyState title="No published results" />}
        </Card>
        <Card title="Recent absences">
          {d.recent_absences.length ? d.recent_absences.map((a, i) => <p key={i} className="flex justify-between py-1 text-sm"><span>{a.subject}</span><span className="text-slate-500">{fmtDate(a.date)}</span></p>) : <EmptyState title="No absences recorded" />}
        </Card>
        {d.fees && (
          <Card title="Fee invoices" actions={<Link href="/r/invoices" className="text-xs font-medium text-brand-800">All</Link>}>
            {d.fees.open_invoices.length ? d.fees.open_invoices.map((i) => <Link key={i.id} href={`/finance/invoices/${i.id}`} className="flex justify-between py-1 text-sm hover:underline"><span>{i.invoice_number} · due {fmtDate(i.due_date)}</span><span className="font-medium">{fmtMoney(i.balance_due, cur)}</span></Link>) : <EmptyState title="No open invoices" />}
            {d.fees.recent_payments.length > 0 && <div className="mt-3 border-t border-slate-100 pt-2">{d.fees.recent_payments.map((p) => <p key={p.id} className="flex justify-between text-xs text-slate-500"><span>{p.receipt_number} · {fmtDate(p.paid_at)}</span><span>{fmtMoney(p.amount, cur)}</span></p>)}</div>}
          </Card>
        )}
        <Card title="Recent materials" actions={<Link href="/materials" className="text-xs font-medium text-brand-800">Library</Link>}>
          {d.recent_materials.length ? d.recent_materials.map((m) => <p key={m.id} className="flex justify-between py-1 text-sm"><span>{m.title}</span><span className="text-xs text-slate-400">{fmtDate(m.created_at)}</span></p>) : <EmptyState title="No materials yet" />}
        </Card>
        <Announcements />
      </div>
    </div>
  );
}

export function StudentDashboard() {
  const { me } = useSession();
  const q = useQuery({ queryKey: ["dash-student"], queryFn: () => api<StudentData>("/dashboard/student") });
  if (q.isLoading) return <Skeleton className="h-64" />;
  if (q.isError || !q.data) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  return (
    <>
      <PageHeader title={`Hello, ${me?.user.full_name.split(" ")[0]}`} description={`${q.data.student.student_code}`} />
      <StudentView d={q.data} />
    </>
  );
}

export function ParentDashboard() {
  const [child, setChild] = useState<string>("");
  const q = useQuery({
    queryKey: ["dash-parent", child],
    queryFn: () => api<{ children: { id: string; full_name: string; student_code: string }[]; selected: StudentData | null }>("/dashboard/parent", { query: { student_id: child || undefined } }),
  });
  if (q.isLoading) return <Skeleton className="h-64" />;
  if (q.isError || !q.data) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  if (!q.data.children.length) return <EmptyState title="No linked students" description="Ask the institute to link your account to your child's record." />;
  return (
    <>
      <PageHeader
        title="Parent dashboard"
        description={q.data.selected?.student.full_name}
        actions={
          <Select className="w-64" value={child || q.data.selected?.student.id} onChange={(e) => setChild(e.target.value)} aria-label="Select child">
            {q.data.children.map((c) => <option key={c.id} value={c.id}>{c.full_name} ({c.student_code})</option>)}
          </Select>
        }
      />
      {q.data.selected && <StudentView d={q.data.selected} />}
    </>
  );
}
