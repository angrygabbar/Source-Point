"use client";

import type { DatesSetArg, EventClickArg } from "@fullcalendar/core";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button, Card, Field, Input, Modal, PageHeader, Select } from "@/components/ui";
import { RefSelect } from "@/components/data/ref-select";
import type { SessionItem } from "@/features/sessions/session-row";
import { useSession } from "@/hooks/use-session";
import { api, ApiError, errorMessage } from "@/lib/api";
import { todayISO } from "@/lib/utils";

const COLORS: Record<string, string> = {
  scheduled: "#2563eb", in_progress: "#4f46e5", completed: "#059669", cancelled: "#dc2626", postponed: "#d97706",
  teacher_absent: "#b91c1c", pending_verification: "#d97706",
};

export default function TimetablePage() {
  const { me, can } = useSession();
  const router = useRouter();
  const [range, setRange] = useState<{ start: string; end: string } | null>(null);
  const [filter, setFilter] = useState<{ kind: string; id: string | null }>({ kind: "batch_id", id: null });
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({ session_type: "extra", session_date: todayISO(), start_time: "16:00", end_time: "17:00" });
  const [conflicts, setConflicts] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const q = useQuery({
    queryKey: ["calendar", range, filter],
    queryFn: () => api<SessionItem[]>("/class-sessions/calendar", { query: { ...range!, [filter.kind]: filter.id ?? undefined } }),
    enabled: !!range,
  });
  const canCreate = can("sessions.write", "sessions.write_own");

  const events = (q.data ?? []).map((s) => ({
    id: s.id,
    title: `${s.subject ?? ""} · ${s.batch ?? ""}${s.substitutes.length ? " (sub)" : ""}`,
    start: s.start,
    end: s.end,
    backgroundColor: COLORS[s.status] ?? "#64748b",
    borderColor: COLORS[s.status] ?? "#64748b",
    extendedProps: s,
  }));

  const create = async () => {
    setBusy(true);
    try {
      await api("/class-sessions", { method: "POST", body: { ...form, classroom_id: form.classroom_id || undefined, makeup_for_session_id: form.makeup_for_session_id || undefined, override_reason: form.override_reason || undefined } });
      toast.success("Class scheduled");
      setCreating(false);
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
    <>
      <PageHeader
        title="Timetable"
        description="Daily, weekly and monthly class calendar. Click a class to open attendance and actions."
        actions={
          <>
            <Select className="w-36" value={filter.kind} onChange={(e) => setFilter({ kind: e.target.value, id: null })}>
              <option value="batch_id">By batch</option>
              <option value="teacher_id">By teacher</option>
              <option value="subject_id">By subject</option>
              <option value="classroom_id">By classroom</option>
            </Select>
            <div className="w-56">
              <RefSelect
                resource={{ batch_id: "batches", teacher_id: "teachers", subject_id: "subjects", classroom_id: "classrooms" }[filter.kind]!}
                value={filter.id}
                placeholder="All"
                onChange={(v) => setFilter({ ...filter, id: v })}
              />
            </div>
            {canCreate && <Button onClick={() => setCreating(true)}><Plus className="h-4 w-4" /> One-time / makeup class</Button>}
          </>
        }
      />
      <Card>
        <div className="mb-3 flex flex-wrap gap-3 text-xs">
          {Object.entries(COLORS).map(([k, c]) => <span key={k} className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: c }} />{k.replace(/_/g, " ")}</span>)}
        </div>
        <FullCalendar
          plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
          initialView="timeGridWeek"
          headerToolbar={{ left: "prev,next today", center: "title", right: "timeGridDay,timeGridWeek,dayGridMonth" }}
          timeZone="local"
          firstDay={1}
          slotMinTime="06:00:00"
          slotMaxTime="22:00:00"
          allDaySlot={false}
          height="auto"
          nowIndicator
          events={events}
          datesSet={(arg: DatesSetArg) => setRange({ start: arg.startStr.slice(0, 10), end: arg.endStr.slice(0, 10) })}
          eventClick={(arg: EventClickArg) => router.push(`/sessions/${arg.event.id}`)}
          dayHeaderFormat={{ weekday: "short", day: "2-digit", month: "2-digit" }}
          eventTimeFormat={{ hour: "2-digit", minute: "2-digit", hour12: false }}
        />
        {q.isFetching && <p className="mt-2 text-xs text-slate-400">Refreshing…</p>}
      </Card>
      <Modal open={creating} onOpenChange={setCreating} title="Schedule a class" description="Conflicts with teacher, batch and classroom bookings are checked automatically." wide
        footer={<><Button variant="outline" onClick={() => setCreating(false)}>Cancel</Button><Button loading={busy} disabled={!form.batch_id || !form.subject_id || !form.teacher_id} onClick={create}>Schedule</Button></>}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Batch" required><RefSelect resource="batches" value={form.batch_id ?? null} onChange={(v) => setForm({ ...form, batch_id: v ?? "" })} /></Field>
          <Field label="Subject" required><RefSelect resource="subjects" value={form.subject_id ?? null} onChange={(v) => setForm({ ...form, subject_id: v ?? "" })} /></Field>
          <Field label="Teacher" required><RefSelect resource="teachers" value={form.teacher_id ?? null} onChange={(v) => setForm({ ...form, teacher_id: v ?? "" })} /></Field>
          <Field label="Classroom"><RefSelect resource="classrooms" value={form.classroom_id ?? null} onChange={(v) => setForm({ ...form, classroom_id: v ?? "" })} /></Field>
          <Field label="Date" required><Input type="date" value={form.session_date} onChange={(e) => setForm({ ...form, session_date: e.target.value })} /></Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Start" required><Input type="time" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} /></Field>
            <Field label="End" required><Input type="time" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} /></Field>
          </div>
          <Field label="Type"><Select value={form.session_type} onChange={(e) => setForm({ ...form, session_type: e.target.value })}>{["extra", "makeup", "demo", "exam", "doubt_solving"].map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}</Select></Field>
          {form.session_type === "makeup" && <Field label="Replaces session"><RefSelect resource="class-sessions" filters={{ status__in: "cancelled,postponed,teacher_absent" }} value={form.makeup_for_session_id ?? null} onChange={(v) => setForm({ ...form, makeup_for_session_id: v ?? "" })} /></Field>}
          <Field label="Online meeting link" className="sm:col-span-2"><Input value={form.online_meeting_url ?? ""} onChange={(e) => setForm({ ...form, online_meeting_url: e.target.value })} placeholder="https://…" /></Field>
          {conflicts.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 sm:col-span-2">
              <p className="font-medium">Conflicts detected</p>
              <ul className="ml-4 list-disc">{conflicts.map((c) => <li key={c}>{c}</li>)}</ul>
              {can("schedules.override_conflict") && (
                <Field label="Override reason (audited)" className="mt-2"><Input value={form.override_reason ?? ""} onChange={(e) => setForm({ ...form, override_reason: e.target.value })} /></Field>
              )}
            </div>
          )}
        </div>
      </Modal>
    </>
  );
}
