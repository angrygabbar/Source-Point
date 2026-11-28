"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, ExternalLink, FileText, PlayCircle } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, EmptyState, Field, PageHeader, Skeleton, Tabs } from "@/components/ui";
import { RefSelect } from "@/components/data/ref-select";
import { ResourceList } from "@/components/data/resource-list";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage, openSignedLink } from "@/lib/api";

/* eslint-disable @typescript-eslint/no-explicit-any */
function Outline({ courseId }: { courseId: string }) {
  const { me } = useSession();
  const q = useQuery({ queryKey: ["outline", courseId], queryFn: () => api<any>(`/lms/courses/${courseId}/outline`) });
  const [openLesson, setOpenLesson] = useState<any>(null);
  if (q.isLoading) return <Skeleton className="h-40" />;
  if (!q.data?.modules.length) return <EmptyState title="No published modules for this course" />;
  const progress = async (lid: string, pct: number) => {
    if (!me?.student_id) return;
    try { await api(`/lms/lessons/${lid}/progress`, { method: "POST", body: { progress_percent: pct } }); q.refetch(); } catch (e) { toast.error(errorMessage(e)); }
  };
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="space-y-3">
        {q.data.completion_percent !== null && me?.student_id && <Card><p className="text-sm">Course progress: <b>{q.data.completion_percent}%</b> ({q.data.completed_lessons}/{q.data.total_lessons} lessons)</p></Card>}
        {q.data.modules.map((m: any) => (
          <Card key={m.id} title={m.title} bodyClass="p-2">
            {m.lessons.map((l: any) => (
              <button key={l.id} onClick={() => { setOpenLesson(l); void progress(l.id, Math.max(l.progress, 10)); }} className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-slate-50">
                {l.status === "completed" ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : l.lesson_type === "video" ? <PlayCircle className="h-4 w-4 text-slate-400" /> : <FileText className="h-4 w-4 text-slate-400" />}
                <span className="flex-1">{l.title}</span>{!l.is_published && <Badge>draft</Badge>}
              </button>
            ))}
          </Card>
        ))}
      </div>
      <Card className="lg:col-span-2" title={openLesson?.title ?? "Select a lesson"}>
        {!openLesson ? <EmptyState title="Select a lesson from the outline" /> : (
          <div className="space-y-3">
            {openLesson.content && <div className="whitespace-pre-wrap text-sm text-slate-700">{openLesson.content}</div>}
            {openLesson.video_url && (
              /\.(mp4|webm)$/i.test(openLesson.video_url)
                ? <video src={openLesson.video_url} controls className="w-full rounded" onEnded={() => progress(openLesson.id, 100)} />
                : <a href={openLesson.video_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sm text-brand-800 underline">Open recorded lecture <ExternalLink className="h-3.5 w-3.5" /></a>
            )}
            {openLesson.resource_url && <a href={openLesson.resource_url} target="_blank" rel="noopener noreferrer" className="block text-sm text-brand-800 underline">Learning resource</a>}
            {openLesson.material_id && <Button size="sm" variant="outline" onClick={() => openSignedLink(`/materials/${openLesson.material_id}/download-link`)}>Download material</Button>}
            {openLesson.examination_id && <Link href={`/exams/${openLesson.examination_id}`}><Button size="sm" variant="outline">Practice quiz</Button></Link>}
            <p className="text-xs text-slate-500">Video completion is recorded when the player reports the end of playback or when you mark it complete; external providers do not report watch time.</p>
            {me?.student_id && <Button size="sm" onClick={() => progress(openLesson.id, 100)}>Mark as complete</Button>}
          </div>
        )}
      </Card>
    </div>
  );
}

export default function LmsPage() {
  const { can } = useSession();
  const [course, setCourse] = useState<string | null>(null);
  const manage = can("lms.write", "lms.write_own");
  return (
    <>
      <PageHeader title="Online learning" description="Course modules, lessons, recorded lectures, practice quizzes and progress tracking." />
      <Tabs tabs={[
        { value: "learn", label: "Courses", content: (
          <>
            <Field label="Course" className="mb-4 w-72"><RefSelect resource="courses" value={course} onChange={setCourse} /></Field>
            {course ? <Outline courseId={course} /> : <EmptyState title="Choose a course" />}
          </>
        ) },
        { value: "modules", label: "Modules", hidden: !manage, content: <ResourceList resource="lms-modules" /> },
        { value: "lessons", label: "Lessons", hidden: !manage, content: <ResourceList resource="lms-lessons" /> },
        { value: "meetings", label: "Live classes", content: <ResourceList resource="online-meetings" hideCreate /> },
        { value: "completions", label: "Completions", hidden: !manage, content: <ResourceList resource="course-completions" /> },
      ]} />
    </>
  );
}
