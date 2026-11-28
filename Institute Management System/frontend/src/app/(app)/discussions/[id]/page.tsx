"use client";

import { useQuery } from "@tanstack/react-query";
import { Flag } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, ErrorState, PageHeader, Skeleton, Textarea } from "@/components/ui";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage } from "@/lib/api";
import { cn, fmtDateTime } from "@/lib/utils";

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function DiscussionPage() {
  const { id } = useParams<{ id: string }>();
  const { me } = useSession();
  const q = useQuery({ queryKey: ["thread-d", id], queryFn: () => api<any>(`/discussions/${id}`) });
  const [body, setBody] = useState("");
  if (q.isLoading) return <Skeleton className="h-64" />;
  if (q.isError || !q.data) return <ErrorState error={q.error} />;
  const t = q.data;
  const mod = async (b: Record<string, unknown>) => { try { await api(`/discussions/${id}/moderate`, { method: "POST", body: b }); q.refetch(); } catch (e) { toast.error(errorMessage(e)); } };
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <PageHeader breadcrumbs={<Link href="/r/discussion-threads" className="hover:underline">Discussions</Link>}
        title={<span className="flex items-center gap-2">{t.title} {t.is_doubt && <Badge tone="indigo">doubt</Badge>} {t.is_resolved && <Badge tone="green">resolved</Badge>} {t.is_locked && <Badge>locked</Badge>}</span>}
        description={`${t.author ?? "—"} · ${fmtDateTime(t.created_at, me?.institute?.timezone)}`}
        actions={<>
          {(t.can_moderate || t.author_id === me?.user.id) && <Button size="sm" variant="outline" onClick={() => mod({ is_resolved: !t.is_resolved })}>{t.is_resolved ? "Reopen" : "Mark resolved"}</Button>}
          {t.can_moderate && <Button size="sm" variant="outline" onClick={() => mod({ is_locked: !t.is_locked })}>{t.is_locked ? "Unlock" : "Lock"}</Button>}
        </>} />
      <Card><p className="whitespace-pre-wrap text-sm">{t.body}</p></Card>
      {t.posts.map((p: any) => (
        <Card key={p.id} className={cn(p.is_answer && "border-emerald-200", p.is_hidden && "opacity-60")}>
          <p className="mb-1 text-xs text-slate-500">{p.author ?? "—"} · {fmtDateTime(p.created_at, me?.institute?.timezone)} {p.is_answer && <Badge tone="green">teacher answer</Badge>} {p.is_hidden && <Badge tone="red">hidden</Badge>}</p>
          <p className="whitespace-pre-wrap text-sm">{p.body}</p>
          <div className="mt-2 flex gap-2">
            {!p.mine && <Button size="sm" variant="ghost" onClick={async () => { await api(`/discussion-posts/${p.id}/report`, { method: "POST" }); toast.success("Reported"); }}><Flag className="h-3.5 w-3.5" /> Report</Button>}
            {t.can_moderate && <Button size="sm" variant="ghost" onClick={() => mod(p.is_hidden ? { unhide_post_id: p.id } : { hide_post_id: p.id })}>{p.is_hidden ? "Unhide" : "Hide"}</Button>}
          </div>
        </Card>
      ))}
      {!t.is_locked && (
        <Card>
          <Textarea value={body} onChange={(e) => setBody(e.target.value)} placeholder="Write a reply…" />
          <Button className="mt-2" disabled={!body.trim()} onClick={async () => { try { await api(`/discussions/${id}/posts`, { method: "POST", body: { body } }); setBody(""); q.refetch(); } catch (e) { toast.error(errorMessage(e)); } }}>Reply</Button>
        </Card>
      )}
    </div>
  );
}
