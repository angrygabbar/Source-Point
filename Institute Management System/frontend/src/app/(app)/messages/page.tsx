"use client";

import { useQuery } from "@tanstack/react-query";
import { Flag, Plus, Send } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, EmptyState, Field, Input, Modal, PageHeader, Select, Skeleton, Textarea } from "@/components/ui";
import { RefSelect } from "@/components/data/ref-select";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage } from "@/lib/api";
import { cn, fmtDateTime } from "@/lib/utils";

/* eslint-disable @typescript-eslint/no-explicit-any */
function Messages() {
  const params = useSearchParams();
  const { me } = useSession();
  const [active, setActive] = useState<string | null>(params.get("thread"));
  const threads = useQuery({ queryKey: ["threads"], queryFn: () => api<any[]>("/messages/threads"), refetchInterval: 30_000 });
  const thread = useQuery({ queryKey: ["thread", active], queryFn: () => api<any>(`/messages/threads/${active}`), enabled: !!active, refetchInterval: 15_000 });
  const [body, setBody] = useState("");
  const [compose, setCompose] = useState(false);
  const [contactQ, setContactQ] = useState("");
  const contacts = useQuery({ queryKey: ["contacts", contactQ], queryFn: () => api<any[]>("/messages/contacts", { query: { q: contactQ || undefined } }), enabled: compose });
  const [form, setForm] = useState<{ subject: string; body: string; participant_ids: string[]; related_student_id: string | null }>({ subject: "", body: "", participant_ids: [], related_student_id: null });
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => end.current?.scrollIntoView({ behavior: "smooth" }), [thread.data]);

  return (
    <>
      <PageHeader title="Messages" description="Teacher contact details are never shared; conversations follow the institute's communication rules." actions={<Button onClick={() => setCompose(true)}><Plus className="h-4 w-4" /> New conversation</Button>} />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card bodyClass="p-0" className="lg:col-span-1">
          {threads.isLoading ? <Skeleton className="m-4 h-40" /> : !threads.data?.length ? <EmptyState title="No conversations" /> : (
            <ul className="divide-y divide-slate-100">
              {threads.data.map((t) => (
                <li key={t.id}>
                  <button className={cn("w-full px-4 py-3 text-left hover:bg-slate-50", active === t.id && "bg-indigo-50")} onClick={() => setActive(t.id)}>
                    <p className="flex justify-between text-sm font-medium"><span className="truncate">{t.subject}</span>{t.unread > 0 && <Badge tone="indigo">{t.unread}</Badge>}</p>
                    <p className="truncate text-xs text-slate-500">{t.participants.join(", ")}</p>
                    <p className="truncate text-xs text-slate-400">{t.last_message}</p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card className="lg:col-span-2" title={thread.data?.subject ?? "Select a conversation"} bodyClass="flex h-[60vh] flex-col p-0">
          {!active ? <EmptyState title="Select a conversation" /> : !thread.data ? <Skeleton className="m-4 h-40" /> : (
            <>
              <div className="flex-1 space-y-2 overflow-y-auto p-4">
                {thread.data.messages.map((m: any) => (
                  <div key={m.id} className={cn("max-w-[80%] rounded-xl px-3 py-2 text-sm", m.mine ? "ml-auto bg-brand-800 text-white" : "bg-slate-100 text-slate-800", m.is_hidden && "opacity-50")}>
                    {!m.mine && <p className="text-xs font-semibold opacity-80">{m.sender}</p>}
                    <p className="whitespace-pre-wrap">{m.body}</p>
                    <p className="mt-1 flex items-center justify-between gap-2 text-[10px] opacity-70">
                      {fmtDateTime(m.created_at, me?.institute?.timezone)}
                      {!m.mine && <button title="Report" onClick={async () => { const reason = window.prompt("Why are you reporting this message?"); if (reason && reason.length >= 3) { try { await api(`/messages/${m.id}/report`, { method: "POST", body: { reason } }); toast.success("Reported to moderators"); } catch (e) { toast.error(errorMessage(e)); } } }}><Flag className="h-3 w-3" /></button>}
                      {thread.data.can_moderate && <button className="underline" onClick={async () => { await api(`/messages/${m.id}/moderate`, { method: "POST", body: { hidden: !m.is_hidden } }); thread.refetch(); }}>{m.is_hidden ? "unhide" : "hide"}</button>}
                    </p>
                  </div>
                ))}
                <div ref={end} />
              </div>
              {thread.data.is_locked ? <p className="border-t p-3 text-center text-xs text-slate-500">This conversation is locked.</p> : (
                <form className="flex gap-2 border-t border-slate-100 p-3" onSubmit={async (e) => {
                  e.preventDefault();
                  if (!body.trim()) return;
                  try { await api(`/messages/threads/${active}`, { method: "POST", body: { body } }); setBody(""); thread.refetch(); threads.refetch(); } catch (err) { toast.error(errorMessage(err)); }
                }}>
                  <Input value={body} onChange={(e) => setBody(e.target.value)} placeholder="Type a message…" />
                  <Button type="submit"><Send className="h-4 w-4" /></Button>
                </form>
              )}
            </>
          )}
        </Card>
      </div>
      <Modal open={compose} onOpenChange={setCompose} title="New conversation"
        footer={<Button disabled={!form.subject || !form.body || !form.participant_ids.length} onClick={async () => {
          try { const r = await api<{ id: string }>("/messages/threads", { method: "POST", body: { ...form, related_student_id: form.related_student_id || undefined } }); setCompose(false); setActive(r.id); threads.refetch(); setForm({ subject: "", body: "", participant_ids: [], related_student_id: null }); } catch (e) { toast.error(errorMessage(e)); }
        }}>Send</Button>}>
        <div className="space-y-3">
          <Field label="To">
            <Input placeholder="Search people you may contact…" value={contactQ} onChange={(e) => setContactQ(e.target.value)} />
            <div className="mt-2 max-h-40 space-y-1 overflow-y-auto">
              {(contacts.data ?? []).map((c) => (
                <label key={c.user_id} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={form.participant_ids.includes(c.user_id)} onChange={(e) => setForm({ ...form, participant_ids: e.target.checked ? [...form.participant_ids, c.user_id] : form.participant_ids.filter((x) => x !== c.user_id) })} />
                  {c.name} <span className="text-xs text-slate-400">{c.roles.join(", ")}</span>
                </label>
              ))}
              {contacts.data?.length === 0 && <p className="text-xs text-slate-500">No permitted contacts match.</p>}
            </div>
          </Field>
          {me?.linked_students && me.linked_students.length > 0 && (
            <Field label="About student"><Select value={form.related_student_id ?? ""} onChange={(e) => setForm({ ...form, related_student_id: e.target.value || null })}><option value="">—</option>{me.linked_students.map((s) => <option key={s.id} value={s.id}>{s.full_name}</option>)}</Select></Field>
          )}
          {me?.portal === "admin" && <Field label="About student (optional)"><RefSelect resource="students" value={form.related_student_id} onChange={(v) => setForm({ ...form, related_student_id: v })} /></Field>}
          <Field label="Subject" required><Input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} /></Field>
          <Field label="Message" required><Textarea value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} /></Field>
        </div>
      </Modal>
    </>
  );
}

export default function MessagesPage() {
  return <Suspense><Messages /></Suspense>;
}
