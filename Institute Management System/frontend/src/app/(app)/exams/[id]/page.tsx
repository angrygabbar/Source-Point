"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, EmptyState, ErrorState, Input, Modal, PageHeader, SimpleTable, Skeleton, StatusBadge, Tabs } from "@/components/ui";
import { RefSelect } from "@/components/data/ref-select";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage } from "@/lib/api";
import { fmtDateTime } from "@/lib/utils";
import type { Row } from "@/types";

/* eslint-disable @typescript-eslint/no-explicit-any */

function ResultsTab({ id, exam }: { id: string; exam: Row }) {
  const { can } = useSession();
  const q = useQuery({ queryKey: ["exam-results", id], queryFn: () => api<any>(`/examinations/${id}/results`) });
  const [rows, setRows] = useState<Record<string, any>>({});
  const [reason, setReason] = useState("");
  useEffect(() => {
    const m: Record<string, any> = {};
    (q.data?.rows ?? []).forEach((r: any) => (m[r.student_id] = { marks_obtained: r.marks_obtained ?? "", is_absent: !!r.is_absent, remarks: r.remarks ?? "", remedial_recommendation: r.remedial_recommendation ?? "" }));
    setRows(m);
  }, [q.data]);
  if (!q.data) return <Skeleton className="h-40" />;
  const editable = q.data.can_edit && !["draft", "cancelled"].includes(String(exam.status));
  const anyApproved = q.data.rows.some((r: any) => r.status && r.status !== "draft");
  const post = async (path: string, msg: string) => {
    try { await api(path, { method: "POST" }); toast.success(msg); q.refetch(); } catch (e) { toast.error(errorMessage(e)); }
  };
  return (
    <Card
      title="Results"
      actions={editable && (
        <>
          <Button size="sm" variant="outline" onClick={async () => {
            try {
              await api(`/examinations/${id}/marks`, { method: "PUT", body: { reason: reason || null, rows: Object.entries(rows).map(([student_id, r]) => ({ student_id, marks_obtained: r.is_absent || r.marks_obtained === "" ? null : String(r.marks_obtained), is_absent: r.is_absent, remarks: r.remarks || null, remedial_recommendation: r.remedial_recommendation || null })) } });
              toast.success("Marks saved"); q.refetch();
            } catch (e) { toast.error(errorMessage(e)); }
          }}>Save marks</Button>
          <Button size="sm" variant="outline" onClick={() => post(`/examinations/${id}/compute`, "Percentages, grades and ranks computed")}>Compute ranks</Button>
          {can("results.approve") && <Button size="sm" onClick={() => post(`/examinations/${id}/approve`, "Results approved")}>Approve</Button>}
          {can("results.approve") && <Button size="sm" variant="accent" onClick={() => post(`/examinations/${id}/publish`, "Results published to students & parents")}>Publish</Button>}
        </>
      )}
      bodyClass="p-0"
    >
      {anyApproved && editable && (
        <div className="border-b border-amber-100 bg-amber-50 px-4 py-2 text-xs text-amber-800">
          Some results are approved/published. Changing them requires grade-modification permission and a reason:
          <Input className="mt-1 h-8" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason for modification" />
        </div>
      )}
      <SimpleTable headers={["Student", "Marks", "Absent", "%", "Grade", "Rank", "Status", "Remarks / remedial (teacher-reviewed)"]}
        rows={q.data.rows.map((r: any) => {
          const v = rows[r.student_id] ?? {};
          const set = (k: string, val: unknown) => setRows({ ...rows, [r.student_id]: { ...v, [k]: val } });
          return [
            `${r.full_name} (${r.student_code})`,
            editable ? <Input key="m" type="number" step="0.5" className="h-8 w-24" disabled={v.is_absent} value={v.marks_obtained} onChange={(e) => set("marks_obtained", e.target.value)} /> : (r.marks_obtained ?? "—"),
            editable ? <input key="a" type="checkbox" checked={!!v.is_absent} onChange={(e) => set("is_absent", e.target.checked)} /> : r.is_absent ? "AB" : "",
            r.percentage ?? "—", r.grade ?? "—", r.rank ?? "—", <StatusBadge key="s" value={r.status} />,
            editable ? <Input key="r" className="h-8 w-64" value={v.remedial_recommendation} onChange={(e) => set("remedial_recommendation", e.target.value)} /> : (r.remedial_recommendation ?? r.remarks ?? ""),
          ];
        })} />
    </Card>
  );
}

function PaperTab({ id, exam }: { id: string; exam: Row }) {
  const q = useQuery({ queryKey: ["paper", id], queryFn: () => api<any>(`/examinations/${id}/paper`) });
  const [qid, setQid] = useState<string | null>(null);
  const editable = ["draft", "scheduled"].includes(String(exam.status));
  if (q.isError) return <ErrorState error={q.error} />;
  return (
    <Card title={`Question paper${q.data ? ` · ${q.data.questions.length} questions · ${q.data.total_marks} marks` : ""}`}
      actions={editable && (
        <div className="flex items-center gap-2">
          <div className="w-72"><RefSelect resource="questions" filters={{ subject_id: String(exam.subject_id), is_approved: "true" }} value={qid} onChange={setQid} placeholder="Add from question bank…" /></div>
          <Button size="sm" disabled={!qid} onClick={async () => { try { await api(`/examinations/${id}/questions`, { method: "POST", body: { question_ids: [qid] } }); setQid(null); q.refetch(); } catch (e) { toast.error(errorMessage(e)); } }}>Add</Button>
        </div>
      )}>
      {!q.data?.questions.length ? <EmptyState title="No questions added" description="Offline exams can skip this; online exams need questions." /> : (
        <ol className="space-y-3">
          {q.data.questions.map((x: any) => (
            <li key={x.question_id} className="rounded-lg border border-slate-200 p-3 text-sm">
              <div className="flex justify-between gap-2">
                <p className="font-medium">{x.sequence}. {x.question_text}</p>
                <span className="flex shrink-0 gap-1"><Badge>{x.question_type.replace("_", " ")}</Badge><Badge tone="indigo">{x.marks} m</Badge>
                  {editable && <Button size="sm" variant="ghost" onClick={async () => { await api(`/examinations/${id}/questions/${x.question_id}`, { method: "DELETE" }); q.refetch(); }}>Remove</Button>}</span>
              </div>
              {x.options?.length > 0 && <ul className="ml-4 mt-1 list-disc text-slate-600">{x.options.map((o: any) => <li key={o.key}>{o.key}. {o.text}</li>)}</ul>}
              <p className="mt-1 text-xs text-emerald-700">Answer: {JSON.stringify(x.correct_answer)}</p>
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}

function ManualGrading({ id }: { id: string }) {
  const q = useQuery({ queryKey: ["manual", id], queryFn: () => api<any[]>(`/examinations/${id}/manual-grading`) });
  const [vals, setVals] = useState<Record<string, { marks: string; feedback: string }>>({});
  if (!q.data) return <Skeleton className="h-32" />;
  if (!q.data.length) return <EmptyState title="No descriptive answers awaiting grading" />;
  return (
    <div className="space-y-3">
      {q.data.map((r) => (
        <Card key={r.response_id} title={`${r.student} · max ${r.max_marks}`}>
          <p className="text-sm font-medium">{r.question_text}</p>
          <p className="mt-2 whitespace-pre-wrap rounded bg-slate-50 p-2 text-sm">{(r.answer ?? []).join("\n") || "—"}</p>
          <div className="mt-2 flex gap-2">
            <Input type="number" step="0.5" className="w-24" placeholder="Marks" value={vals[r.response_id]?.marks ?? r.marks_awarded ?? ""} onChange={(e) => setVals({ ...vals, [r.response_id]: { ...vals[r.response_id], marks: e.target.value } })} />
            <Input placeholder="Feedback" value={vals[r.response_id]?.feedback ?? r.feedback ?? ""} onChange={(e) => setVals({ ...vals, [r.response_id]: { ...vals[r.response_id], feedback: e.target.value } })} />
            <Button onClick={async () => { try { await api(`/exam-responses/${r.response_id}/grade`, { method: "POST", body: { marks: vals[r.response_id]?.marks ?? r.marks_awarded, feedback: vals[r.response_id]?.feedback ?? null } }); toast.success("Saved"); q.refetch(); } catch (e) { toast.error(errorMessage(e)); } }}>Save</Button>
          </div>
        </Card>
      ))}
    </div>
  );
}

export default function ExamPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { me, can } = useSession();
  const q = useQuery({ queryKey: ["row", "examinations", id], queryFn: () => api<Row>(`/examinations/${id}`) });
  const [confirm, setConfirm] = useState(false);
  if (q.isLoading) return <Skeleton className="h-96" />;
  if (q.isError || !q.data) return <ErrorState error={q.error} />;
  const e = q.data;
  const staff = can("exams.write", "exams.write_own");
  const tz = me?.institute?.timezone;
  const setStatus = async (status: string) => {
    try { await api(`/examinations/${id}/status`, { method: "POST", body: { status } }); toast.success(`Exam ${status}`); q.refetch(); } catch (err) { toast.error(errorMessage(err)); }
  };
  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={<Link href="/r/examinations" className="hover:underline">Examinations</Link>}
        title={<span className="flex items-center gap-2">{String(e.name)} <StatusBadge value={String(e.status)} /></span>}
        description={`${e.display?.subject_id ?? ""} · ${e.display?.batch_id ?? ""} · ${String(e.mode)} · ${fmtDateTime(e.scheduled_start as string, tz)} · max ${e.max_marks}`}
        actions={
          <>
            {staff && e.status === "draft" && <Button size="sm" onClick={() => setStatus("scheduled")}>Schedule</Button>}
            {staff && e.status === "scheduled" && e.mode === "online" && <Button size="sm" variant="outline" onClick={() => setStatus("live")}>Go live</Button>}
            {staff && ["scheduled", "live"].includes(String(e.status)) && <Button size="sm" variant="outline" onClick={() => setStatus("completed")}>Mark completed</Button>}
            {me?.student_id && e.mode === "online" && ["scheduled", "live"].includes(String(e.status)) && <Button size="sm" onClick={() => setConfirm(true)}>Start / resume attempt</Button>}
          </>
        }
      />
      {e.instructions ? <Card title="Instructions"><p className="whitespace-pre-wrap text-sm">{String(e.instructions)}</p></Card> : null}
      {staff ? (
        <Tabs tabs={[
          { value: "results", label: "Marks & results", content: <ResultsTab id={id} exam={e} /> },
          { value: "paper", label: "Question paper", content: <PaperTab id={id} exam={e} /> },
          { value: "manual", label: "Manual grading", hidden: e.mode !== "online", content: <ManualGrading id={id} /> },
        ]} />
      ) : <ResultsTab id={id} exam={e} />}
      <Modal open={confirm} onOpenChange={setConfirm} title="Start online exam" description="The timer starts immediately and the attempt auto-submits at the deadline."
        footer={<Button onClick={() => router.push(`/exams/${id}/attempt`)}>Start</Button>}>
        <p className="text-sm text-slate-600">Duration: {String(e.duration_minutes ?? "—")} minutes. {e.negative_marking ? "Negative marking applies." : ""}</p>
      </Modal>
    </div>
  );
}
