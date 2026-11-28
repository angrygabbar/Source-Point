"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, Paperclip, Send } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, EmptyState, ErrorState, Field, Input, Modal, PageHeader, SimpleTable, Skeleton, StatCard, StatusBadge, Textarea } from "@/components/ui";
import { RefSelect } from "@/components/data/ref-select";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage, openSignedLink } from "@/lib/api";
import { fmtDateTime } from "@/lib/utils";

/* eslint-disable @typescript-eslint/no-explicit-any */

function Comments({ id, submissionId }: { id: string; submissionId?: string }) {
  const q = useQuery({ queryKey: ["comments", id, submissionId], queryFn: () => api<any[]>(`/assignments/${id}/comments`, { query: { submission_id: submissionId } }) });
  const [body, setBody] = useState("");
  return (
    <Card title="Comments">
      <div className="space-y-2">
        {(q.data ?? []).map((c) => <div key={c.id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm"><p className="text-xs text-slate-500">{c.author ?? "—"} · {fmtDateTime(c.created_at)}</p><p className="whitespace-pre-wrap">{c.body}</p></div>)}
        {!q.data?.length && <p className="text-sm text-slate-500">No comments yet.</p>}
        <form className="flex gap-2" onSubmit={async (e) => {
          e.preventDefault();
          if (!body.trim()) return;
          try { await api(`/assignments/${id}/comments`, { method: "POST", body: { body, submission_id: submissionId } }); setBody(""); q.refetch(); }
          catch (err) { toast.error(errorMessage(err)); }
        }}>
          <Input value={body} onChange={(e) => setBody(e.target.value)} placeholder="Write a comment…" />
          <Button type="submit" size="sm"><Send className="h-3.5 w-3.5" /></Button>
        </form>
      </div>
    </Card>
  );
}

function StudentSubmission({ a, sub, onDone }: { a: any; sub: any; onDone: () => void }) {
  const [text, setText] = useState(sub?.versions?.find((v: any) => !v.is_final)?.text_content ?? "");
  const [remarks, setRemarks] = useState("");
  const files = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const canSubmit = ["submission_open", "published", "under_evaluation", "evaluated"].includes(a.status) && a.submission_type !== "offline"
    && (!sub || ["draft", "resubmission_requested", "not_submitted"].includes(sub.status) || (a.allow_resubmission && sub.status !== "evaluated"));
  const save = async (submit: boolean) => {
    const form = new FormData();
    form.append("submit", String(submit));
    if (text) form.append("text_content", text);
    if (remarks) form.append("remarks", remarks);
    Array.from(files.current?.files ?? []).forEach((f) => form.append("files", f));
    setBusy(true);
    try {
      await api(`/assignments/${a.id}/my-submission`, { method: "POST", form });
      toast.success(submit ? "Submitted" : "Draft saved");
      if (files.current) files.current.value = "";
      onDone();
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Card title={<span className="flex items-center gap-2">My submission <StatusBadge value={sub?.status ?? "not_submitted"} /></span>}>
      {sub?.grade && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm">
          <p className="font-semibold text-emerald-800">Marks: {sub.grade.marks} / {a.max_marks} {Number(sub.grade.penalty_applied) > 0 && <span className="text-xs text-amber-700">(late penalty −{sub.grade.penalty_applied})</span>}</p>
          {sub.grade.feedback && <p className="mt-1 whitespace-pre-wrap text-emerald-900">{sub.grade.feedback}</p>}
        </div>
      )}
      {canSubmit ? (
        <div className="space-y-3">
          {a.submission_type !== "file" && <Field label="Answer"><Textarea rows={6} value={text} onChange={(e) => setText(e.target.value)} /></Field>}
          {a.submission_type !== "text" && <Field label="Attach files" hint="You can also take a photo on mobile."><input ref={files} type="file" multiple accept="image/*,.pdf,.doc,.docx,.txt" className="text-sm" /></Field>}
          <Field label="Remarks for teacher"><Input value={remarks} onChange={(e) => setRemarks(e.target.value)} /></Field>
          <div className="flex gap-2">
            <Button variant="outline" loading={busy} onClick={() => save(false)}>Save draft</Button>
            <Button loading={busy} onClick={() => save(true)}>Submit</Button>
          </div>
        </div>
      ) : <p className="text-sm text-slate-500">{a.submission_type === "offline" ? "This homework is submitted in class." : "Submissions are closed or already submitted."}</p>}
      {sub?.versions?.length > 0 && (
        <div className="mt-4 border-t border-slate-100 pt-3">
          <p className="mb-2 text-xs font-semibold uppercase text-slate-500">Submission history</p>
          {sub.versions.map((v: any) => (
            <div key={v.id} className="mb-2 rounded-lg bg-slate-50 p-2 text-sm">
              <p className="text-xs text-slate-500">v{v.version_number} · {v.is_final ? `submitted ${fmtDateTime(v.submitted_at)}` : "draft"} {v.is_late && <Badge tone="amber">late</Badge>}</p>
              {v.text_content && <p className="mt-1 line-clamp-3 whitespace-pre-wrap">{v.text_content}</p>}
              {v.files.map((f: any) => <button key={f.id} className="mr-2 text-xs text-brand-800 underline" onClick={() => openSignedLink(`/submission-files/${f.id}/download-link`)}>{f.original_filename}</button>)}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function TeacherSubmissions({ a }: { a: any }) {
  const q = useQuery({ queryKey: ["subs", a.id], queryFn: () => api<any>(`/assignments/${a.id}/submissions`) });
  const [grading, setGrading] = useState<any>(null);
  const [g, setG] = useState({ marks: "", feedback: "", modification_reason: "" });
  const [view, setView] = useState<any>(null);
  const subQ = useQuery({ queryKey: ["sub", view?.submission_id], queryFn: () => api<any>(`/submissions/${view.submission_id}`), enabled: !!view?.submission_id });
  if (!q.data) return <Skeleton className="h-40" />;
  const m = q.data.metrics;
  return (
    <>
      <div className="grid grid-cols-3 gap-3 md:grid-cols-6">
        {Object.entries(m).map(([k, v]) => <StatCard key={k} label={k.replace(/_/g, " ")} value={String(v)} />)}
      </div>
      <Card title="Submissions" bodyClass="p-0">
        <SimpleTable headers={["Student", "Status", "Submitted", "Version", "Marks", ""]}
          rows={q.data.rows.map((r: any) => [
            `${r.full_name} (${r.student_code})`,
            <span key="s" className="flex gap-1"><StatusBadge value={r.status} />{r.is_late && <Badge tone="amber">late</Badge>}</span>,
            fmtDateTime(r.submitted_at), r.version || "—", r.marks !== null ? `${r.marks}/${q.data.max_marks}` : "—",
            r.submission_id && r.status !== "draft" ? (
              <span key="a" className="flex gap-1">
                <Button size="sm" variant="ghost" onClick={() => setView(r)}>View</Button>
                <Button size="sm" variant="outline" onClick={() => { setGrading(r); setG({ marks: r.marks ?? "", feedback: r.feedback ?? "", modification_reason: "" }); }}>Grade</Button>
              </span>
            ) : null,
          ])} />
      </Card>
      <Modal open={!!grading} onOpenChange={() => setGrading(null)} title={`Grade: ${grading?.full_name ?? ""}`}
        footer={<>
          <Button variant="outline" onClick={async () => {
            if (g.feedback.length < 3) return toast.error("Add feedback explaining what to fix");
            try { await api(`/submissions/${grading.submission_id}/request-resubmission`, { method: "POST", body: { feedback: g.feedback } }); toast.success("Resubmission requested"); setGrading(null); q.refetch(); } catch (e) { toast.error(errorMessage(e)); }
          }}>Request resubmission</Button>
          <Button onClick={async () => {
            try { await api(`/submissions/${grading.submission_id}/grade`, { method: "POST", body: { marks: g.marks, feedback: g.feedback || null, modification_reason: g.modification_reason || null } }); toast.success("Graded"); setGrading(null); q.refetch(); } catch (e) { toast.error(errorMessage(e)); }
          }}>Save grade</Button>
        </>}>
        <div className="space-y-3">
          <Field label={`Marks (max ${a.max_marks})`} hint={grading?.is_late && Number(a.late_penalty_percent) > 0 ? `Late penalty of ${a.late_penalty_percent}% is applied automatically` : undefined}><Input type="number" step="0.5" value={g.marks} onChange={(e) => setG({ ...g, marks: e.target.value })} /></Field>
          <Field label="Feedback"><Textarea rows={4} value={g.feedback} onChange={(e) => setG({ ...g, feedback: e.target.value })} /></Field>
          {grading?.marks !== null && grading?.marks !== undefined && <Field label="Reason for changing existing grade" required><Input value={g.modification_reason} onChange={(e) => setG({ ...g, modification_reason: e.target.value })} /></Field>}
        </div>
      </Modal>
      <Modal open={!!view} onOpenChange={() => setView(null)} title={`Submission: ${view?.full_name ?? ""}`} wide>
        {subQ.data ? subQ.data.versions.map((v: any) => (
          <div key={v.id} className="mb-3 rounded-lg border border-slate-200 p-3 text-sm">
            <p className="text-xs text-slate-500">v{v.version_number} · {v.is_final ? fmtDateTime(v.submitted_at) : "draft"} {v.is_late && <Badge tone="amber">late</Badge>}</p>
            {v.text_content && <p className="mt-2 whitespace-pre-wrap">{v.text_content}</p>}
            {v.remarks && <p className="mt-1 text-xs italic text-slate-500">Remarks: {v.remarks}</p>}
            <div className="mt-2 flex flex-wrap gap-2">{v.files.map((f: any) => <Button key={f.id} size="sm" variant="outline" onClick={() => openSignedLink(`/submission-files/${f.id}/download-link`)}><Download className="h-3.5 w-3.5" /> {f.original_filename}</Button>)}</div>
          </div>
        )) : <Skeleton className="h-24" />}
        {view?.submission_id && <Comments id={a.id} submissionId={view.submission_id} />}
      </Modal>
    </>
  );
}

export default function AssignmentPage() {
  const { id } = useParams<{ id: string }>();
  const { me } = useSession();
  const tz = me?.institute?.timezone;
  const q = useQuery({ queryKey: ["assignment", id], queryFn: () => api<any>(`/assignments/${id}/detail`) });
  const [targets, setTargets] = useState(false);
  const [tg, setTg] = useState<{ batch: string | null; batches: string[]; student: string | null; students: string[] }>({ batch: null, batches: [], student: null, students: [] });
  const attach = useRef<HTMLInputElement>(null);
  if (q.isLoading) return <Skeleton className="h-96" />;
  if (q.isError || !q.data) return <ErrorState error={q.error} />;
  const a = q.data;
  const act = async (path: string, body?: unknown, msg = "Updated") => {
    try { await api(path, { method: "POST", body }); toast.success(msg); q.refetch(); } catch (e) { toast.error(errorMessage(e)); }
  };
  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={<Link href="/r/assignments" className="hover:underline">Homework</Link>}
        title={<span className="flex items-center gap-2">{a.title} <StatusBadge value={a.status} /></span>}
        description={`${a.subject} · ${a.batch} · ${a.teacher} · due ${fmtDateTime(a.due_at, tz)} · max ${a.max_marks} marks`}
        actions={a.can_manage && (
          <>
            {a.status === "draft" && <Button size="sm" variant="outline" onClick={() => setTargets(true)}>Targets</Button>}
            {a.status !== "closed" && (
              <label className="inline-flex h-8 cursor-pointer items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 text-xs font-medium text-slate-700 hover:bg-slate-50">
                <Paperclip className="h-3.5 w-3.5" /> Attach
                <input ref={attach} type="file" multiple className="hidden" onChange={async (e) => {
                  const form = new FormData();
                  Array.from(e.target.files ?? []).forEach((f) => form.append("files", f));
                  try { await api(`/assignments/${id}/attachments`, { method: "POST", form }); toast.success("Attached"); q.refetch(); } catch (err) { toast.error(errorMessage(err)); }
                }} />
              </label>
            )}
            {a.status === "draft" && <Button size="sm" onClick={() => act(`/assignments/${id}/publish`, undefined, "Published")}>Publish</Button>}
            {a.status === "submission_open" && <Button size="sm" variant="outline" onClick={() => act(`/assignments/${id}/status`, { status: "under_evaluation" })}>Start evaluation</Button>}
            {["under_evaluation", "evaluated"].includes(a.status) && <Button size="sm" variant="outline" onClick={() => act(`/assignments/${id}/status`, { status: "submission_open" })}>Reopen submissions</Button>}
            {["under_evaluation", "evaluated"].includes(a.status) && <Button size="sm" variant="danger" onClick={() => act(`/assignments/${id}/status`, { status: "closed" })}>Close</Button>}
          </>
        )}
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Instructions" className="lg:col-span-2">
          {a.description && <p className="mb-2 whitespace-pre-wrap text-sm text-slate-700">{a.description}</p>}
          <p className="whitespace-pre-wrap text-sm text-slate-700">{a.instructions || "—"}</p>
          {a.attachments.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{a.attachments.map((f: any) => <Button key={f.id} size="sm" variant="outline" onClick={() => openSignedLink(`/assignment-attachments/${f.id}/download-link`)}><Download className="h-3.5 w-3.5" /> {f.original_filename}</Button>)}</div>}
        </Card>
        <Card title="Rules">
          <ul className="space-y-1 text-sm text-slate-600">
            <li>Submission: {a.submission_type.replace(/_/g, " ")}</li>
            <li>Late submissions: {a.allow_late ? `allowed${a.late_until ? ` until ${fmtDateTime(a.late_until, tz)}` : ""}` : "not allowed"}</li>
            {Number(a.late_penalty_percent) > 0 && <li>Late penalty: {a.late_penalty_percent}%</li>}
            <li>Resubmission: {a.allow_resubmission ? "allowed" : "only when requested"}</li>
            <li>Targets: {a.targets.length ? `${a.targets.filter((t: any) => t.batch_id).length} batch(es), ${a.targets.filter((t: any) => t.student_id).length} student(s)` : "whole batch"}</li>
          </ul>
        </Card>
      </div>
      {a.can_manage && a.status !== "draft" && <TeacherSubmissions a={a} />}
      {a.my_submissions?.map((s: any) => (
        me?.student_id === s.student_id ? <StudentSubmission key={s.student_id} a={a} sub={s.id ? s : null} onDone={() => q.refetch()} /> : (
          <Card key={s.student_id} title={<span className="flex items-center gap-2">Child&apos;s submission <StatusBadge value={s.status} /></span>}>
            {s.grade ? <p className="text-sm">Marks {s.grade.marks}/{a.max_marks}{s.grade.feedback && ` — ${s.grade.feedback}`}</p> : <EmptyState title="Not graded yet" />}
          </Card>
        )
      ))}
      {(a.can_manage || me?.student_id) && <Comments id={id} submissionId={a.my_submissions?.[0]?.id} />}
      <Modal open={targets} onOpenChange={setTargets} title="Assignment targets" description="Choose whole batches and/or specific students."
        footer={<Button onClick={async () => { try { await api(`/assignments/${id}/targets`, { method: "PUT", body: { batch_ids: tg.batches, student_ids: tg.students } }); toast.success("Targets saved"); setTargets(false); q.refetch(); } catch (e) { toast.error(errorMessage(e)); } }}>Save</Button>}>
        <div className="space-y-3">
          <Field label="Add batch"><div className="flex gap-2"><div className="flex-1"><RefSelect resource="batches" value={tg.batch} onChange={(v) => setTg({ ...tg, batch: v })} /></div><Button size="sm" variant="outline" onClick={() => tg.batch && setTg({ ...tg, batches: Array.from(new Set([...tg.batches, tg.batch])), batch: null })}>Add</Button></div></Field>
          <Field label="Add student"><div className="flex gap-2"><div className="flex-1"><RefSelect resource="students" value={tg.student} onChange={(v) => setTg({ ...tg, student: v })} /></div><Button size="sm" variant="outline" onClick={() => tg.student && setTg({ ...tg, students: Array.from(new Set([...tg.students, tg.student])), student: null })}>Add</Button></div></Field>
          <p className="text-sm text-slate-600">{tg.batches.length} batch(es), {tg.students.length} student(s) selected</p>
        </div>
      </Modal>
    </div>
  );
}
