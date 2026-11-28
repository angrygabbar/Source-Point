"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Card, ErrorState, PageHeader, SimpleTable, Skeleton, Tabs } from "@/components/ui";
import { RefSelect } from "@/components/data/ref-select";
import { ResourceList } from "@/components/data/resource-list";
import { useSession } from "@/hooks/use-session";
import { api } from "@/lib/api";

interface P { batch: string; subject: string; total_chapters: number; completed: number; in_progress: number; delayed: number; coverage_percent: number | null }

export default function SyllabusPage() {
  const { can } = useSession();
  const [f, setF] = useState<Record<string, string | null>>({});
  const q = useQuery({ queryKey: ["syllabus-progress", f], queryFn: () => api<P[]>("/syllabus/progress", { query: f as Record<string, string> }) });
  return (
    <>
      <PageHeader title="Syllabus & lesson planning" description="Course → subject → chapters/topics, with batch-wise coverage and delay tracking." />
      <Tabs tabs={[
        { value: "progress", label: "Coverage", content: (
          <Card title="Coverage by batch & subject" actions={<div className="flex gap-2">
            <div className="w-48"><RefSelect resource="courses" value={f.course_id ?? null} onChange={(v) => setF({ ...f, course_id: v })} placeholder="All courses" /></div>
            <div className="w-48"><RefSelect resource="batches" value={f.batch_id ?? null} onChange={(v) => setF({ ...f, batch_id: v })} placeholder="All batches" /></div>
            <div className="w-48"><RefSelect resource="subjects" value={f.subject_id ?? null} onChange={(v) => setF({ ...f, subject_id: v })} placeholder="All subjects" /></div>
            {can("teachers.read") && <div className="w-48"><RefSelect resource="teachers" value={f.teacher_id ?? null} onChange={(v) => setF({ ...f, teacher_id: v })} placeholder="All teachers" /></div>}
          </div>} bodyClass="p-0">
            {q.isLoading ? <Skeleton className="m-4 h-40" /> : q.isError ? <ErrorState error={q.error} /> : (
              <SimpleTable headers={["Batch", "Subject", "Chapters", "Completed", "In progress", "Delayed", "Coverage"]} empty="Map subjects to batches and add chapters to see coverage"
                rows={(q.data ?? []).map((r) => [r.batch, r.subject, r.total_chapters, r.completed, r.in_progress, r.delayed ? <span key="d" className="font-medium text-red-600">{r.delayed}</span> : 0,
                  <div key="c" className="flex items-center gap-2"><div className="h-2 w-24 rounded bg-slate-200"><div className="h-2 rounded bg-accent-500" style={{ width: `${r.coverage_percent ?? 0}%` }} /></div><span className="text-xs">{r.coverage_percent ?? "—"}%</span></div>])} />
            )}
          </Card>
        ) },
        { value: "chapters", label: "Chapters & topics", content: <ResourceList resource="syllabus-chapters" /> },
        { value: "batch", label: "Batch progress records", content: <ResourceList resource="syllabus-progress" /> },
        { value: "plans", label: "Lesson plans", content: <ResourceList resource="lesson-plans" /> },
      ]} />
    </>
  );
}
