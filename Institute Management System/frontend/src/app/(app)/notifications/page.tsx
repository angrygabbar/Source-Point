"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, EmptyState, PageHeader, SimpleTable, Skeleton, Tabs } from "@/components/ui";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage, type Page } from "@/lib/api";
import { cn, fmtDateTime } from "@/lib/utils";

interface N { id: string; event_type: string; title: string; body: string | null; link: string | null; is_read: boolean; created_at: string }

function Inbox() {
  const { me } = useSession();
  const [unread, setUnread] = useState(false);
  const [page, setPage] = useState(1);
  const q = useQuery({ queryKey: ["notifications", unread, page], queryFn: () => api<Page<N>>("/notifications", { query: { unread_only: unread || undefined, page } }) });
  return (
    <Card title="Inbox" actions={<>
      <label className="flex items-center gap-1.5 text-xs"><input type="checkbox" checked={unread} onChange={(e) => setUnread(e.target.checked)} /> Unread only</label>
      <Button size="sm" variant="outline" onClick={async () => { await api("/notifications/read-all", { method: "POST" }); q.refetch(); }}>Mark all read</Button>
    </>} bodyClass="p-0">
      {q.isLoading ? <Skeleton className="m-4 h-40" /> : !q.data?.items.length ? <EmptyState title="No notifications" /> : (
        <ul className="divide-y divide-slate-100">
          {q.data.items.map((n) => (
            <li key={n.id} className={cn("flex items-start gap-3 px-4 py-3", !n.is_read && "bg-indigo-50/50")}>
              <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", n.is_read ? "bg-slate-300" : "bg-brand-800")} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-800">{n.title} <Badge className="ml-1">{n.event_type.replace(/_/g, " ")}</Badge></p>
                {n.body && <p className="text-sm text-slate-600">{n.body}</p>}
                <p className="text-xs text-slate-400">{fmtDateTime(n.created_at, me?.institute?.timezone)}</p>
              </div>
              <div className="flex gap-1">
                {n.link && <Link href={n.link} onClick={() => api(`/notifications/${n.id}/read`, { method: "POST" })}><Button size="sm" variant="ghost">Open</Button></Link>}
                {!n.is_read && <Button size="sm" variant="ghost" onClick={async () => { await api(`/notifications/${n.id}/read`, { method: "POST" }); q.refetch(); }}>Read</Button>}
              </div>
            </li>
          ))}
        </ul>
      )}
      {q.data && q.data.total > q.data.page_size && <div className="flex justify-end gap-2 p-2"><Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button><Button size="sm" variant="outline" disabled={page * q.data.page_size >= q.data.total} onClick={() => setPage(page + 1)}>Next</Button></div>}
    </Card>
  );
}

function urlB64ToUint8Array(base64: string) {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const raw = atob((base64 + padding).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(Array.from(raw).map((c) => c.charCodeAt(0)));
}

function Preferences() {
  const q = useQuery({ queryKey: ["prefs"], queryFn: () => api<{ channels: { channel: string; available: boolean }[]; preferences: { event_type: string; channel: string; enabled: boolean }[] }>("/notifications/preferences") });
  const key = useQuery({ queryKey: ["push-key"], queryFn: () => api<{ public_key: string | null }>("/notifications/push-public-key") });
  if (!q.data) return <Skeleton className="h-40" />;
  const events = Array.from(new Set(q.data.preferences.map((p) => p.event_type)));
  const map = new Map(q.data.preferences.map((p) => [`${p.event_type}:${p.channel}`, p.enabled]));
  const toggle = async (event_type: string, channel: string, enabled: boolean) => {
    try { await api("/notifications/preferences", { method: "PUT", body: [{ event_type, channel, enabled }] }); q.refetch(); } catch (e) { toast.error(errorMessage(e)); }
  };
  const enablePush = async () => {
    try {
      if (!key.data?.public_key) throw new Error("Push notifications are not configured by the institute");
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlB64ToUint8Array(key.data.public_key) });
      const j = sub.toJSON();
      await api("/notifications/push-subscription", { method: "POST", body: { endpoint: j.endpoint, p256dh: j.keys?.p256dh, auth: j.keys?.auth } });
      toast.success("Push notifications enabled on this device");
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };
  return (
    <Card title="Notification preferences" actions={key.data?.public_key && "serviceWorker" in navigator && <Button size="sm" variant="outline" onClick={enablePush}>Enable push on this device</Button>} bodyClass="p-0">
      <p className="px-4 pt-3 text-xs text-slate-500">Greyed channels are not configured by your institute. In-app notifications are always recorded.</p>
      <SimpleTable headers={["Event", ...q.data.channels.map((c) => c.channel.replace("_", "-"))]}
        rows={events.map((ev) => [ev.replace(/_/g, " "), ...q.data!.channels.map((c) => (
          <input key={c.channel} type="checkbox" disabled={!c.available} checked={map.get(`${ev}:${c.channel}`) ?? true} onChange={(e) => toggle(ev, c.channel, e.target.checked)} />
        ))])} />
    </Card>
  );
}

export default function NotificationsPage() {
  return (
    <>
      <PageHeader title="Notifications" />
      <Tabs tabs={[{ value: "inbox", label: "Inbox", content: <Inbox /> }, { value: "prefs", label: "Preferences", content: <Preferences /> }]} />
    </>
  );
}
