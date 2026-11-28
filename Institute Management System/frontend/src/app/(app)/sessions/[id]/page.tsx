"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCheck, CloudOff, Save, Send } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, Field, Input, Modal, PageHeader, Select, SimpleTable, Skeleton, StatusBadge, Textarea } from "@/components/ui";
import { RefSelect } from "@/components/data/ref-select";
import { useSession } from "@/hooks/use-session";
import { api, ApiError, errorMessage } from "@/lib/api";
import { cn, fmtDate, fmtDateTime, fmtTime, todayISO } from "@/lib/utils";

/* eslint-disable @typescript-eslint/no-explicit-any */
const STATUSES = ["present", "absent", "late", "excused", "approved_leave"] as const;
const SHORT: Record<string, string> = { present: "P", absent: "A", late: "L", excused: "E", approved_leave: "AL" };
const TONE: Record<string, string> = { present: "bg-emerald-600 text-white", absent: "bg-red-600 text-white", late: "bg-amber-500 text-white", excused: "bg-teal-600 text-white", approved_leave: "bg-sky-600 text-white" };

function AttendancePanel({ sessionId, onChanged }: { sessionId: string; onChanged: () => void }) {
  const { can } = useSession();
  const q = useQuery({ queryKey: ["attendance", sessionId], queryFn: () => api<any>(`/class-sessions/${sessionId}/attendance`) });
  const draftKey = `cf.att.${sessionId}`;
  const [marks, setMarks] = useState<Record<string, { status: string; remarks: string }>>({});
  const [busy, setBusy] = useState(false);
  const [reopen, setReopen] = useState(false);
  const [correction, setCorrection] = useState<any>(null);
  const [corr, setCorr] = useState({ requested_status: "present", reason: "" });
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    if (!q.data) return;
    const init: Record<string, { status: string; remarks: string }> = {};
    q.data.records.forEach((r: any) => (init[r.student_id] = { status: r.status ?? "", remarks: r.remarks ?? "" }));
    const local = typeof window !== "undefined" ? localStorage.getItem(draftKey) : null;
    if (local && q.data.attendance_state !== "submitted") {
      try {
        const parsed = JSON.parse(local) as Record<string, { status: string; remarks: string }>;
        Object.keys(parsed).forEach((k) => init[k] && (init[k] = parsed[k]));
        setOffline(true);
      } catch {
        localStorage.removeItem(draftKey);
      }
    }
    setMarks(init);
  }, [q.data, draftKey]);

  if (q.isLoading) return <Skeleton className="h-40" />;
  if (q.isError) return <ErrorState error={q.error} />;
  const d = q.data;
  const locked = d.attendance_state === "submitted";
  const editable = d.can_mark && !locked && !["cancelled", "postponed"].includes(d.session_status);
  const counts = Object.values(marks).reduce<Record<string, number>>((acc, m) => ((acc[m.status || "unmarked"] = (acc[m.status || "unmarked"] ?? 0) + 1), acc), {});

  const setMark = (sid: string, patch: Partial<{ status: string; remarks: string }>) => {
    const next = { ...marks, [sid]: { ...marks[sid], ...patch } };
    setMarks(next);
    // Offline draft keeps only ids/statuses (no names or personal details).
    localStorage.setItem(draftKey, JSON.stringify(next));
  };

  const save = async (submit: boolean) => {
    const records = Object.entries(marks).filter(([, m]) => m.status).map(([student_id, m]) => ({ student_id, status: m.status, remarks: m.remarks || null }));
    setBusy(true);
    try {
      await api(`/class-sessions/${sessionId}/attendance`, { method: "PUT", body: { records, submit } });
      localStorage.removeItem(draftKey);
      setOffline(false);
      toast.success(submit ? "Attendance submitted and locked" : "Draft saved");
      q.refetch();
      onChanged();
    } catch (e) {
      if (e instanceof TypeError) toast.warning("You appear to be offline. The draft is kept on this device; sync when online.");
      else toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card
      title={<span className="flex items-center gap-2">Student attendance <StatusBadge value={d.attendance_state} /></span>}
      actions={
        <>
          {offline && <Badge tone="amber"><CloudOff className="mr-1 h-3 w-3" /> Unsynced draft on device</Badge>}
          {editable && <Button size="sm" variant="outline" onClick={() => { const n = { ...marks }; Object.keys(n).forEach((k) => (n[k] = { ...n[k], status: "present" })); setMarks(n); localStorage.setItem(draftKey, JSON.stringify(n)); }}><CheckCheck className="h-3.5 w-3.5" /> Mark all present</Button>}
          {editable && <Button size="sm" variant="outline" loading={busy} onClick={() => save(false)}><Save className="h-3.5 w-3.5" /> Save draft</Button>}
          {editable && <Button size="sm" loading={busy} onClick={() => save(true)}><Send className="h-3.5 w-3.5" /> Submit & lock</Button>}
          {locked && d.can_reopen && <Button size="sm" variant="outline" onClick={() => setReopen(true)}>Reopen</Button>}
        </>
      }
      bodyClass="p-0"
    >
      <div className="flex flex-wrap gap-2 border-b border-slate-100 px-4 py-2 text-xs text-slate-600">
        {Object.entries(counts).map(([k, v]) => <span key={k}>{k.replace("_", " ")}: <b>{v}</b></span>)}
      </div>
      {!d.records.length ? <EmptyState title="No eligible students" description="Students appear here when their enrollment in this batch is valid on the class date." /> : (
        <ul className="divide-y divide-slate-100">
          {d.records.map((r: any) => (
            <li key={r.student_id} className="flex flex-col gap-2 px-4 py-2.5 md:flex-row md:items-center">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-800">{r.full_name} {r.not_currently_eligible && <Badge>historical</Badge>}</p>
                <p className="text-xs text-slate-500">{r.student_code}{r.marked_at && ` · marked ${fmtDateTime(r.marked_at)}`}</p>
              </div>
              <div className="flex flex-wrap gap-1">
                {STATUSES.map((st) => (
                  <button
                    key={st}
                    disabled={!editable}
                    title={st.replace("_", " ")}
                    onClick={() => setMark(r.student_id, { status: st })}
                    className={cn("h-8 min-w-[36px] rounded-md border px-2 text-xs font-semibold transition-colors disabled:cursor-default",
                      marks[r.student_id]?.status === st ? TONE[st] : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50")}
                  >
                    {SHORT[st]}
                  </button>
                ))}
              </div>
              <Input className="md:w-56" placeholder="Remarks" disabled={!editable} value={marks[r.student_id]?.remarks ?? ""} onChange={(e) => setMark(r.student_id, { remarks: e.target.value })} />
              {locked && r.attendance_id && d.can_mark && (
                <Button size="sm" variant="ghost" onClick={() => { setCorrection(r); setCorr({ requested_status: r.status === "present" ? "absent" : "present", reason: "" }); }}>Correction</Button>
              )}
            </li>
          ))}
        </ul>
      )}
      <ConfirmDialog open={reopen} onOpenChange={setReopen} title="Reopen attendance" requireReason confirmLabel="Reopen"
        message="Reopening unlocks the register. Every subsequent change is recorded with original and corrected status."
        onConfirm={async (reason) => { try { await api(`/class-sessions/${sessionId}/attendance/reopen`, { method: "POST", body: { reason } }); toast.success("Reopened"); q.refetch(); onChanged(); } catch (e) { toast.error(errorMessage(e)); } }} />
      <Modal open={!!correction} onOpenChange={() => setCorrection(null)} title={`Correction request: ${correction?.full_name ?? ""}`}
        footer={<Button disabled={corr.reason.length < 3} onClick={async () => { try { await api("/attendance/corrections", { method: "POST", body: { attendance_id: correction.attendance_id, ...corr } }); toast.success("Correction requested"); setCorrection(null); } catch (e) { toast.error(errorMessage(e)); } }}>Request</Button>}>
        <div className="space-y-3">
          <p className="text-sm text-slate-600">Current status: <StatusBadge value={correction?.status} /></p>
          <Field label="Corrected status"><Select value={corr.requested_status} onChange={(e) => setCorr({ ...corr, requested_status: e.target.value })}>{STATUSES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}</Select></Field>
          <Field label="Reason" required><Textarea value={corr.reason} onChange={(e) => setCorr({ ...corr, reason: e.target.value })} /></Field>
          {can("attendance.correct_approve") && <p className="text-xs text-slate-500">You can approve it in Attendance corrections.</p>}
        </div>
      </Modal>
    </Card>
  );
}

function TeacherAttendancePanel({ sessionId, isAdmin }: { sessionId: string; isAdmin: boolean }) {
  const { me } = useSession();
  const q = useQuery({ queryKey: ["t-att", sessionId], queryFn: () => api<any[]>(`/class-sessions/${sessionId}/teacher-attendance`) });
  const [rows, setRows] = useState<Record<string, any>>({});
  useEffect(() => {
    const m: Record<string, any> = {};
    (q.data ?? []).forEach((r) => (m[r.teacher_id] = {
      status: r.status ?? "present",
      arrival_at: r.arrival_at ? r.arrival_at.slice(0, 16) : "",
      departure_at: r.departure_at ? r.departure_at.slice(0, 16) : "",
      absence_reason: r.absence_reason ?? "",
    }));
    setRows(m);
  }, [q.data]);
  if (q.isError) return null;
  const save = async () => {
    const payload = Object.entries(rows)
      .filter(([tid]) => isAdmin || tid === me?.teacher_id)
      .map(([teacher_id, r]) => ({
        teacher_id, status: r.status, absence_reason: r.absence_reason || null,
        arrival_at: r.arrival_at ? new Date(r.arrival_at).toISOString() : null,
        departure_at: r.departure_at ? new Date(r.departure_at).toISOString() : null,
      }));
    try {
      await api(`/class-sessions/${sessionId}/teacher-attendance`, { method: "PUT", body: payload });
      toast.success("Teacher attendance saved");
      q.refetch();
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };
  return (
    <Card title="Teacher attendance" actions={<>
      <Button size="sm" variant="outline" onClick={save}>Save</Button>
      {isAdmin && <Button size="sm" onClick={async () => { try { await api(`/class-sessions/${sessionId}/teacher-attendance/verify`, { method: "POST" }); toast.success("Verified for payroll"); q.refetch(); } catch (e) { toast.error(errorMessage(e)); } }}>Verify</Button>}
    </>} bodyClass="p-0">
      <SimpleTable headers={["Teacher", "Role", "Status", "Arrival", "Departure", "Minutes", "Verified"]}
        rows={(q.data ?? []).map((r) => {
          const canEdit = isAdmin || r.teacher_id === me?.teacher_id;
          const v = rows[r.teacher_id] ?? {};
          const set = (k: string, val: string) => setRows({ ...rows, [r.teacher_id]: { ...v, [k]: val } });
          return [
            r.name, <Badge key="r">{r.role}</Badge>,
            <Select key="s" disabled={!canEdit} className="h-8 w-32" value={v.status} onChange={(e) => set("status", e.target.value)}>{["present", "late", "absent", "on_leave", "excused"].map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}</Select>,
            <Input key="a" disabled={!canEdit} type="datetime-local" className="h-8 w-48" value={v.arrival_at ?? ""} onChange={(e) => set("arrival_at", e.target.value)} />,
            <Input key="d" disabled={!canEdit} type="datetime-local" className="h-8 w-48" value={v.departure_at ?? ""} onChange={(e) => set("departure_at", e.target.value)} />,
            r.teaching_minutes ?? "—", r.is_verified ? <Badge key="v" tone="green">verified</Badge> : <Badge key="v">no</Badge>,
          ];
        })} />
    </Card>
  );
}

export default function SessionPage() {
  const { id } = useParams<{ id: string }>();
  const { me, can } = useSession();
  const tz = me?.institute?.timezone;
  const q = useQuery({ queryKey: ["session", id], queryFn: () => api<any>(`/class-sessions/${id}/detail`) });
  const [dialog, setDialog] = useState<null | "complete" | "cancel" | "reschedule" | "substitute" | "absent" | "meeting">(null);
  const [f, setF] = useState<Record<string, any>>({});
  const [conflicts, setConflicts] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const s = q.data;
  const active = useMemo(() => s && !["completed", "cancelled", "postponed"].includes(s.status), [s]);

  if (q.isLoading) return <Skeleton className="h-96" />;
  if (q.isError || !s) return <ErrorState error={q.error} />;

  const post = async (path: string, body: unknown, msg: string) => {
    setBusy(true);
    try {
      await api(path, { method: "POST", body });
      toast.success(msg);
      setDialog(null);
      setConflicts([]);
      q.refetch();
    } catch (e) {
      if (e instanceof ApiError && e.code === "schedule_conflict") setConflicts((e.details as string[]) ?? []);
      toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={<Link href="/timetable" className="hover:underline">Timetable</Link>}
        title={<span className="flex items-center gap-2">{s.subject} · {s.batch} <StatusBadge value={s.status} /></span>}
        description={`${fmtDate(s.session_date)} · ${fmtTime(s.start, tz)}–${fmtTime(s.end, tz)} · ${s.teacher}${s.substitutes.length ? ` → ${s.substitutes.map((x: any) => x.name).join(", ")}` : ""}${s.classroom ? ` · ${s.classroom}` : ""}`}
        actions={s.can_manage && (
          <>
            {s.status === "scheduled" && <Button size="sm" variant="outline" onClick={() => post(`/class-sessions/${id}/start`, {}, "Class started")}>Start</Button>}
            {["scheduled", "in_progress", "pending_verification"].includes(s.status) && <Button size="sm" onClick={() => { setF({}); setDialog("complete"); }}>Complete</Button>}
            {s.is_admin && active && <Button size="sm" variant="outline" onClick={() => { setF({}); setDialog("substitute"); }}>Substitute</Button>}
            {s.is_admin && s.status === "scheduled" && <Button size="sm" variant="outline" onClick={() => { setF({ new_date: s.session_date, start_time: fmtTime(s.start, tz), end_time: fmtTime(s.end, tz) }); setDialog("reschedule"); }}>Reschedule</Button>}
            {s.is_admin && active && <Button size="sm" variant="outline" onClick={() => { setF({}); setDialog("absent"); }}>Teacher absent</Button>}
            {s.is_admin && active && <Button size="sm" variant="danger" onClick={() => { setF({}); setDialog("cancel"); }}>Cancel</Button>}
            {can("lms.write", "lms.write_own") && <Button size="sm" variant="ghost" onClick={() => { setF({ provider: "manual", title: `${s.subject} – ${s.batch}`, start_at: s.start, duration_minutes: 60 }); setDialog("meeting"); }}>Online link</Button>}
          </>
        )}
      />
      {(s.cancellation_reason || s.remarks || s.topic_covered || s.online_meeting_url) && (
        <Card>
          <div className="grid gap-3 text-sm sm:grid-cols-2">
            {s.topic_covered && <p><span className="text-slate-500">Topic covered:</span> {s.topic_covered}</p>}
            {s.remarks && <p><span className="text-slate-500">Remarks:</span> {s.remarks}</p>}
            {s.cancellation_reason && <p className="text-red-700"><span className="text-slate-500">Cancellation:</span> {s.cancellation_reason}</p>}
            {s.online_meeting_url && <p><span className="text-slate-500">Online class:</span> <a className="text-brand-800 underline" href={s.online_meeting_url} target="_blank" rel="noopener noreferrer">Join link</a></p>}
          </div>
        </Card>
      )}
      <AttendancePanel sessionId={id} onChanged={() => q.refetch()} />
      {(s.can_manage || can("teacher_attendance.read")) && <TeacherAttendancePanel sessionId={id} isAdmin={can("teacher_attendance.write")} />}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Materials for this class" actions={s.can_manage && <Link href={`/materials?session=${id}&batch=${s.batch_id}&subject=${s.subject_id}`} className="text-xs font-medium text-brand-800">Upload</Link>}>
          {s.materials.length ? s.materials.map((m: any) => <p key={m.id} className="text-sm">{m.title} <Badge>{m.category}</Badge></p>) : <EmptyState title="No materials linked" />}
        </Card>
        <Card title="Homework from this class">
          {s.assignments.length ? s.assignments.map((a: any) => <Link key={a.id} href={`/assignments/${a.id}`} className="flex justify-between text-sm hover:underline"><span>{a.title}</span><StatusBadge value={a.status} /></Link>) : <EmptyState title="No homework linked" />}
        </Card>
      </div>

      <Modal open={dialog === "complete"} onOpenChange={() => setDialog(null)} title="Complete class"
        description="Status becomes 'completed' once attendance is submitted; otherwise 'pending verification'."
        footer={<Button loading={busy} onClick={() => post(`/class-sessions/${id}/complete`, { topic_covered: f.topic_covered || null, syllabus_chapter_id: f.chapter || null, chapter_completed: !!f.chapter_completed, remarks: f.remarks || null }, "Class completed")}>Complete</Button>}>
        <div className="space-y-3">
          <Field label="Topic covered"><Textarea value={f.topic_covered ?? ""} onChange={(e) => setF({ ...f, topic_covered: e.target.value })} /></Field>
          <Field label="Syllabus chapter / topic"><RefSelect resource="syllabus-chapters" filters={{ subject_id: s.subject_id }} value={f.chapter ?? null} onChange={(v) => setF({ ...f, chapter: v })} /></Field>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!!f.chapter_completed} onChange={(e) => setF({ ...f, chapter_completed: e.target.checked })} /> Chapter completed</label>
          <Field label="Remarks"><Input value={f.remarks ?? ""} onChange={(e) => setF({ ...f, remarks: e.target.value })} /></Field>
        </div>
      </Modal>
      <Modal open={dialog === "cancel"} onOpenChange={() => setDialog(null)} title="Cancel class" description="Students, parents and teachers are notified."
        footer={<Button variant="danger" loading={busy} disabled={(f.reason ?? "").length < 3} onClick={() => post(`/class-sessions/${id}/cancel`, { reason: f.reason }, "Class cancelled")}>Cancel class</Button>}>
        <Field label="Reason" required><Textarea value={f.reason ?? ""} onChange={(e) => setF({ ...f, reason: e.target.value })} /></Field>
      </Modal>
      <Modal open={dialog === "absent"} onOpenChange={() => setDialog(null)} title="Mark scheduled teacher absent"
        footer={<Button variant="danger" loading={busy} disabled={(f.reason ?? "").length < 3} onClick={() => post(`/class-sessions/${id}/teacher-absent`, { reason: f.reason }, "Recorded")}>Confirm</Button>}>
        <Field label="Reason" required><Textarea value={f.reason ?? ""} onChange={(e) => setF({ ...f, reason: e.target.value })} /></Field>
      </Modal>
      <Modal open={dialog === "substitute"} onOpenChange={() => setDialog(null)} title="Assign substitute teacher"
        footer={<Button loading={busy} disabled={!f.teacher_id || (f.reason ?? "").length < 3} onClick={() => post(`/class-sessions/${id}/substitute`, { teacher_id: f.teacher_id, reason: f.reason, override_reason: f.override_reason || undefined }, "Substitute assigned")}>Assign</Button>}>
        <div className="space-y-3">
          <Field label="Teacher" required><RefSelect resource="teachers" value={f.teacher_id ?? null} onChange={(v) => setF({ ...f, teacher_id: v })} /></Field>
          <Field label="Reason" required><Input value={f.reason ?? ""} onChange={(e) => setF({ ...f, reason: e.target.value })} /></Field>
          {conflicts.length > 0 && <ConflictBox conflicts={conflicts} value={f.override_reason} onChange={(v) => setF({ ...f, override_reason: v })} />}
        </div>
      </Modal>
      <Modal open={dialog === "reschedule"} onOpenChange={() => setDialog(null)} title="Reschedule class" description="The original session is kept as 'postponed' and a linked makeup session is created."
        footer={<Button loading={busy} disabled={(f.reason ?? "").length < 3} onClick={() => post(`/class-sessions/${id}/reschedule`, { new_date: f.new_date, start_time: f.start_time, end_time: f.end_time, classroom_id: f.classroom_id || undefined, reason: f.reason, override_reason: f.override_reason || undefined }, "Rescheduled")}>Reschedule</Button>}>
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="New date"><Input type="date" min={todayISO()} value={f.new_date ?? ""} onChange={(e) => setF({ ...f, new_date: e.target.value })} /></Field>
          <Field label="Start"><Input type="time" value={f.start_time ?? ""} onChange={(e) => setF({ ...f, start_time: e.target.value })} /></Field>
          <Field label="End"><Input type="time" value={f.end_time ?? ""} onChange={(e) => setF({ ...f, end_time: e.target.value })} /></Field>
          <Field label="Classroom" className="sm:col-span-3"><RefSelect resource="classrooms" value={f.classroom_id ?? null} onChange={(v) => setF({ ...f, classroom_id: v })} /></Field>
          <Field label="Reason" required className="sm:col-span-3"><Input value={f.reason ?? ""} onChange={(e) => setF({ ...f, reason: e.target.value })} /></Field>
          {conflicts.length > 0 && <div className="sm:col-span-3"><ConflictBox conflicts={conflicts} value={f.override_reason} onChange={(v) => setF({ ...f, override_reason: v })} /></div>}
        </div>
      </Modal>
      <Modal open={dialog === "meeting"} onOpenChange={() => setDialog(null)} title="Online class link"
        description="Zoom / Google Meet creation works only when the integration is configured; otherwise paste a link."
        footer={<Button loading={busy} onClick={() => post("/online-meetings", { ...f, session_id: id, join_url: f.join_url || undefined, duration_minutes: Number(f.duration_minutes) }, "Meeting saved")}>Save</Button>}>
        <div className="space-y-3">
          <Field label="Provider"><Select value={f.provider} onChange={(e) => setF({ ...f, provider: e.target.value })}><option value="manual">Manual link</option><option value="zoom">Zoom</option><option value="google_meet">Google Meet</option></Select></Field>
          {f.provider === "manual" && <Field label="Meeting link (https)"><Input value={f.join_url ?? ""} onChange={(e) => setF({ ...f, join_url: e.target.value })} /></Field>}
          <Field label="Duration (minutes)"><Input type="number" value={f.duration_minutes ?? 60} onChange={(e) => setF({ ...f, duration_minutes: e.target.value })} /></Field>
        </div>
      </Modal>
    </div>
  );
}

function ConflictBox({ conflicts, value, onChange }: { conflicts: string[]; value?: string; onChange: (v: string) => void }) {
  const { can } = useSession();
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
      <p className="font-medium">Conflicts</p>
      <ul className="ml-4 list-disc">{conflicts.map((c) => <li key={c}>{c}</li>)}</ul>
      {can("schedules.override_conflict") && <Field label="Override reason (audited)" className="mt-2"><Input value={value ?? ""} onChange={(e) => onChange(e.target.value)} /></Field>}
    </div>
  );
}
