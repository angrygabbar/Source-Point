"use client";

import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Badge, Button, Card, EmptyState, PageHeader, Skeleton } from "@/components/ui";
import { ResourceList } from "@/components/data/resource-list";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage } from "@/lib/api";
import { fmtDateTime } from "@/lib/utils";

interface A { id: string; title: string; body: string; priority: string; published_at: string; requires_acknowledgement: boolean; acknowledged: boolean }

export default function AnnouncementsPage() {
  const { me, can } = useSession();
  const feed = useQuery({ queryKey: ["ann-feed-full"], queryFn: () => api<A[]>("/announcements/feed/mine") });
  const manage = can("announcements.write", "announcements.write_own");
  return (
    <>
      <PageHeader title="Announcements" />
      <div className="space-y-4">
        <Card title="Published for you">
          {feed.isLoading ? <Skeleton className="h-32" /> : !feed.data?.length ? <EmptyState title="No announcements" /> : (
            <ul className="space-y-3">
              {feed.data.map((a) => (
                <li key={a.id} className="rounded-lg border border-slate-200 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-medium text-slate-800">{a.title} {a.priority !== "normal" && <Badge tone={a.priority === "urgent" ? "red" : "amber"}>{a.priority}</Badge>}</p>
                    <span className="text-xs text-slate-400">{fmtDateTime(a.published_at, me?.institute?.timezone)}</span>
                  </div>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-slate-600">{a.body}</p>
                  {a.requires_acknowledgement && (a.acknowledged ? <Badge tone="green" className="mt-2">Acknowledged</Badge> : (
                    <Button size="sm" className="mt-2" onClick={async () => { try { await api(`/announcements/${a.id}/acknowledge`, { method: "POST" }); feed.refetch(); } catch (e) { toast.error(errorMessage(e)); } }}>Acknowledge</Button>
                  ))}
                </li>
              ))}
            </ul>
          )}
        </Card>
        {manage && <ResourceList resource="announcements" title="Manage announcements" />}
      </div>
    </>
  );
}
