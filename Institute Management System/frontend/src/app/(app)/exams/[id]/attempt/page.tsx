"use client";

import { useQuery } from "@tanstack/react-query";
import { Clock } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, ErrorState, Input, PageHeader, Skeleton, Textarea } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";

/* eslint-disable @typescript-eslint/no-explicit-any */

export default function AttemptPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const q = useQuery({ queryKey: ["attempt", id], queryFn: () => api<any>(`/examinations/${id}/attempt/start`, { method: "POST" }), refetchOnWindowFocus: false });
  const [answers, setAnswers] = useState<Record<string, string[]>>({});
  const [remaining, setRemaining] = useState(0);
  const dirty = useRef<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!q.data) return;
    const a: Record<string, string[]> = {};
    q.data.questions.forEach((x: any) => x.answer && (a[x.question_id] = x.answer));
    setAnswers(a);
    setRemaining(q.data.remaining_seconds);
  }, [q.data]);

  const flush = useCallback(async () => {
    if (!dirty.current.size) return;
    const ids = Array.from(dirty.current);
    dirty.current.clear();
    try {
      await api(`/examinations/${id}/attempt/answers`, { method: "PUT", body: { answers: ids.map((qid) => ({ question_id: qid, answer: answers[qid] ?? [] })) } });
    } catch (e) {
      ids.forEach((x) => dirty.current.add(x));
      toast.error(errorMessage(e));
    }
  }, [answers, id]);

  const submit = useCallback(async () => {
    setSubmitting(true);
    await flush();
    try {
      const r = await api<{ message: string }>(`/examinations/${id}/attempt/submit`, { method: "POST" });
      toast.success(r.message);
      router.replace(`/exams/${id}`);
    } catch (e) {
      toast.error(errorMessage(e));
      setSubmitting(false);
    }
  }, [flush, id, router]);

  useEffect(() => {
    if (!q.data || q.data.status !== "in_progress") return;
    const t = setInterval(() => setRemaining((r) => Math.max(0, r - 1)), 1000);
    const s = setInterval(() => void flush(), 15000);
    return () => { clearInterval(t); clearInterval(s); };
  }, [q.data, flush]);

  useEffect(() => {
    if (q.data?.status === "in_progress" && remaining === 0 && q.data.remaining_seconds > 0 && !submitting) void submit();
  }, [remaining, q.data, submit, submitting]);

  if (q.isLoading) return <Skeleton className="h-96" />;
  if (q.isError || !q.data) return <ErrorState error={q.error} />;
  const d = q.data;
  const set = (qid: string, v: string[]) => { setAnswers({ ...answers, [qid]: v }); dirty.current.add(qid); };
  const mm = String(Math.floor(remaining / 60)).padStart(2, "0");
  const ss = String(remaining % 60).padStart(2, "0");
  const done = d.status !== "in_progress";

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <PageHeader title={d.exam.name} description={d.exam.negative_marking ? "Negative marking applies to wrong objective answers." : undefined}
        actions={!done && <Badge tone={remaining < 300 ? "red" : "indigo"} className="px-3 py-1 text-sm"><Clock className="mr-1 h-4 w-4" />{mm}:{ss}</Badge>} />
      {done && <Card><p className="text-sm">This attempt has been submitted ({d.status.replace("_", " ")}). Results appear after teacher review and publication.</p></Card>}
      {d.questions.map((x: any, i: number) => (
        <Card key={x.question_id} title={`Q${i + 1} · ${x.marks} mark(s)`}>
          <p className="mb-3 whitespace-pre-wrap text-sm text-slate-800">{x.question_text}</p>
          {["mcq_single", "true_false"].includes(x.question_type) && x.options.map((o: any) => (
            <label key={o.key} className="flex items-center gap-2 py-1 text-sm"><input type="radio" disabled={done} name={x.question_id} checked={answers[x.question_id]?.[0] === o.key} onChange={() => set(x.question_id, [o.key])} /> {o.key}. {o.text}</label>
          ))}
          {x.question_type === "mcq_multi" && x.options.map((o: any) => (
            <label key={o.key} className="flex items-center gap-2 py-1 text-sm"><input type="checkbox" disabled={done} checked={answers[x.question_id]?.includes(o.key) ?? false}
              onChange={(e) => set(x.question_id, e.target.checked ? [...(answers[x.question_id] ?? []), o.key] : (answers[x.question_id] ?? []).filter((k) => k !== o.key))} /> {o.key}. {o.text}</label>
          ))}
          {["numerical", "fill_blank"].includes(x.question_type) && <Input disabled={done} value={answers[x.question_id]?.[0] ?? ""} onChange={(e) => set(x.question_id, [e.target.value])} />}
          {x.question_type === "descriptive" && <Textarea disabled={done} rows={6} value={answers[x.question_id]?.[0] ?? ""} onChange={(e) => set(x.question_id, [e.target.value])} />}
        </Card>
      ))}
      {!done && (
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => flush().then(() => toast.success("Answers saved"))}>Save answers</Button>
          <Button loading={submitting} onClick={submit}>Submit exam</Button>
        </div>
      )}
    </div>
  );
}
