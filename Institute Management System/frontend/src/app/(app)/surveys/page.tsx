"use client";

import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { toast } from "sonner";
import { Button, Card, EmptyState, Field, Input, Modal, PageHeader, Select, SimpleTable, Textarea } from "@/components/ui";
import { ResourceList } from "@/components/data/resource-list";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage, type Page } from "@/lib/api";
import type { Row } from "@/types";

/* eslint-disable @typescript-eslint/no-explicit-any */
function Surveys() {
  const params = useSearchParams();
  const { can, me } = useSession();
  const open = useQuery({ queryKey: ["surveys-open"], queryFn: () => api<Page<Row>>("/surveys", { query: { status: "open", page_size: 50 } }) });
  const [active, setActive] = useState<Row | null>(null);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [summaryId, setSummaryId] = useState<string | null>(null);
  const summary = useQuery({ queryKey: ["survey-summary", summaryId], queryFn: () => api<any>(`/surveys/${summaryId}/summary`), enabled: !!summaryId });
  const manage = can("surveys.write", "surveys.write_own");
  useEffect(() => {
    const id = params.get("open");
    if (id && open.data) setActive(open.data.items.find((s) => s.id === id) ?? null);
  }, [params, open.data]);
  const questions = (active?.questions as any[]) ?? [];
  return (
    <>
      <PageHeader title="Feedback & surveys" />
      <div className="space-y-4">
        <Card title="Open surveys">
          {!open.data?.items.length ? <EmptyState title="No open surveys" /> : (
            <ul className="space-y-2">{open.data.items.map((s) => (
              <li key={s.id} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <span><b>{String(s.title)}</b> <span className="text-slate-500">· {String(s.survey_type)}{s.is_anonymous ? " · anonymous" : ""}</span></span>
                <span className="flex gap-2">
                  <Button size="sm" onClick={() => { setAnswers({}); setActive(s); }}>Respond</Button>
                  {(can("surveys.read") || s.created_by_id === me?.user.id) && <Button size="sm" variant="outline" onClick={() => setSummaryId(s.id)}>Results</Button>}
                </span>
              </li>))}</ul>
          )}
        </Card>
        {manage && <ResourceList resource="surveys" title="Manage surveys" />}
      </div>
      <Modal open={!!active} onOpenChange={() => setActive(null)} title={String(active?.title ?? "")} description={String(active?.description ?? "")}
        footer={<Button onClick={async () => { try { await api(`/surveys/${active!.id}/respond`, { method: "POST", body: { answers } }); toast.success("Thank you for your response"); setActive(null); } catch (e) { toast.error(errorMessage(e)); } }}>Submit</Button>}>
        <div className="space-y-3">
          {questions.length === 0 && <p className="text-sm text-slate-500">This survey has no questions.</p>}
          {questions.map((q: any) => (
            <Field key={q.key} label={q.label}>
              {q.type === "rating" ? (
                <Select value={answers[q.key] ?? ""} onChange={(e) => setAnswers({ ...answers, [q.key]: Number(e.target.value) })}><option value="">—</option>{[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}</Select>
              ) : q.type === "choice" ? (
                <Select value={answers[q.key] ?? ""} onChange={(e) => setAnswers({ ...answers, [q.key]: e.target.value })}><option value="">—</option>{(q.options ?? []).map((o: string) => <option key={o}>{o}</option>)}</Select>
              ) : q.type === "text" && q.long ? <Textarea value={answers[q.key] ?? ""} onChange={(e) => setAnswers({ ...answers, [q.key]: e.target.value })} />
                : <Input value={answers[q.key] ?? ""} onChange={(e) => setAnswers({ ...answers, [q.key]: e.target.value })} />}
            </Field>
          ))}
        </div>
      </Modal>
      <Modal open={!!summaryId} onOpenChange={() => setSummaryId(null)} title={summary.data?.survey ?? "Results"} wide>
        {summary.data && (
          <>
            <p className="mb-3 text-sm text-slate-600">{summary.data.total_responses} responses{summary.data.anonymous ? " (anonymous)" : ""}</p>
            <SimpleTable headers={["Question", "Responses", "Result"]} rows={summary.data.questions.map((q: any) => [q.label, q.responses,
              q.average !== undefined ? `Average ${q.average ?? "—"}` : q.counts ? Object.entries(q.counts).map(([k, v]) => `${k}: ${v}`).join(", ") : (q.samples ?? []).slice(0, 3).join(" | ")])} />
          </>
        )}
      </Modal>
    </>
  );
}

export default function SurveysPage() {
  return <Suspense><Surveys /></Suspense>;
}
