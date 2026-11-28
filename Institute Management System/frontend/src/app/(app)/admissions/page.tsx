"use client";

import { useQuery } from "@tanstack/react-query";
import { MoreHorizontal, Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, Field, Input, Menu, Modal, PageHeader, Select, SimpleTable, Skeleton, Tabs, Textarea } from "@/components/ui";
import { RefSelect } from "@/components/data/ref-select";
import { useSession } from "@/hooks/use-session";
import { api, ApiError, errorMessage } from "@/lib/api";
import { fmtDate, fmtDateTime, todayISO } from "@/lib/utils";

/* eslint-disable @typescript-eslint/no-explicit-any */
const STAGES = ["new", "contacted", "counselling", "demo_class", "admission_offered", "enrolled", "lost"];
const NEXT: Record<string, string[]> = {
  new: ["contacted", "counselling", "demo_class", "lost"], contacted: ["counselling", "demo_class", "admission_offered", "lost"],
  counselling: ["demo_class", "admission_offered", "contacted", "lost"], demo_class: ["counselling", "admission_offered", "lost"],
  admission_offered: ["counselling", "lost"], lost: ["contacted"], enrolled: [],
};
const SOURCES = ["walk_in", "website", "phone", "referral", "social_media", "advertisement", "event", "other"];

export default function AdmissionsPage() {
  const { can } = useSession();
  const [search, setSearch] = useState("");
  const q = useQuery({ queryKey: ["pipeline", search], queryFn: () => api<Record<string, { count: number; items: any[] }>>("/admissions/pipeline", { query: { q: search || undefined } }) });
  const conv = useQuery({ queryKey: ["conversion"], queryFn: () => api<any>("/admissions/conversion") });
  const [dlg, setDlg] = useState<null | { kind: string; e?: any }>(null);
  const [f, setF] = useState<Record<string, any>>({});
  const [dups, setDups] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const write = can("admissions.write");

  const post = async (path: string, body: unknown, msg: string) => {
    setBusy(true);
    try {
      await api(path, { method: "POST", body });
      toast.success(msg);
      setDlg(null);
      setDups([]);
      q.refetch();
      conv.refetch();
    } catch (e) {
      if (e instanceof ApiError && e.code === "duplicate_student") setDups(e.details as any[]);
      toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader title="Admissions CRM" description="Enquiry → contacted → counselling → demo → offer → enrolled / lost"
        actions={<>
          <Input className="w-56" placeholder="Search name…" value={search} onChange={(e) => setSearch(e.target.value)} />
          {write && <Button onClick={() => { setF({ source: "walk_in", enquiry_mode: "walk_in" }); setDlg({ kind: "new" }); }}><Plus className="h-4 w-4" /> New enquiry</Button>}
        </>} />
      <Tabs tabs={[
        { value: "pipeline", label: "Pipeline", content: q.isLoading ? <Skeleton className="h-64" /> : (
          <div className="flex gap-3 overflow-x-auto pb-3">
            {STAGES.map((st) => (
              <div key={st} className="w-64 shrink-0 rounded-xl bg-slate-100/70 p-2">
                <p className="mb-2 flex items-center justify-between px-1 text-xs font-semibold uppercase text-slate-600">{st.replace("_", " ")}<Badge>{q.data?.[st]?.count ?? 0}</Badge></p>
                <div className="space-y-2">
                  {(q.data?.[st]?.items ?? []).map((e) => (
                    <div key={e.id} className="rounded-lg border border-slate-200 bg-white p-2.5 shadow-sm">
                      <div className="flex items-start justify-between gap-1">
                        <a href={`/r/enquiries/${e.id}`} className="text-sm font-medium text-slate-800 hover:underline">{e.contact_name}</a>
                        {write && st !== "enrolled" && (
                          <Menu trigger={<button className="rounded p-0.5 text-slate-400 hover:bg-slate-100" aria-label="Actions"><MoreHorizontal className="h-4 w-4" /></button>} items={[
                            ...NEXT[st].map((n) => ({ label: `Move to ${n.replace("_", " ")}`, onClick: () => { setF({ stage: n }); setDlg({ kind: "stage", e }); } })),
                            { label: "Schedule follow-up", onClick: () => { setF({ mode: "call", due_at: "" }); setDlg({ kind: "followup", e }); } },
                            { label: "Make admission offer", onClick: () => { setF({ offer_date: todayISO() }); setDlg({ kind: "offer", e }); }, hidden: st === "lost" },
                            { label: "Convert to student", onClick: () => { setF({ admission_date: todayISO() }); setDups([]); setDlg({ kind: "convert", e }); }, hidden: st === "lost" || !can("students.write") },
                          ]} />
                        )}
                      </div>
                      <p className="text-xs text-slate-500">{e.phone ?? "—"} · {e.source?.replace("_", " ")}</p>
                      {e.next_follow_up_at && <p className="mt-1 text-xs text-amber-700">Follow-up {fmtDateTime(e.next_follow_up_at)}</p>}
                      {e.lost_reason && <p className="mt-1 text-xs text-red-600">{e.lost_reason}</p>}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) },
        { value: "conversion", label: "Conversion analytics", content: conv.data && (
          <div className="grid gap-4 lg:grid-cols-2">
            <Card title="By lead source" bodyClass="p-0"><SimpleTable headers={["Source", "Enquiries", "Enrolled", "Lost", "Conversion %"]} rows={conv.data.by_source.map((r: any) => [r.source, r.enquiries, r.enrolled, r.lost, r.conversion_percent ?? "—"])} /></Card>
            <Card title="By campaign" bodyClass="p-0"><SimpleTable headers={["Campaign", "Enquiries", "Enrolled", "Conversion %"]} rows={conv.data.by_campaign.map((r: any) => [r.campaign, r.enquiries, r.enrolled, r.conversion_percent ?? "—"])} /></Card>
            <Card title="Lost reasons" bodyClass="p-0"><SimpleTable headers={["Reason", "Count"]} rows={conv.data.lost_reasons.map((r: any) => [r.reason, r.count])} /></Card>
            <Card title="Referrals"><p className="text-2xl font-semibold">{conv.data.referral_leads}</p><p className="text-sm text-slate-500">leads from referrals</p></Card>
          </div>
        ) },
      ]} />

      <Modal open={dlg?.kind === "new"} onOpenChange={() => setDlg(null)} title="New enquiry" description="Existing leads with the same phone/email are reused to avoid duplicates." wide
        footer={<Button loading={busy} disabled={!f.full_name || (!f.phone && !f.email)} onClick={() => post("/admissions/enquiries", { ...f, next_follow_up_at: f.next_follow_up_at ? new Date(f.next_follow_up_at).toISOString() : undefined, email: f.email || undefined }, "Enquiry created")}>Create</Button>}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Student name" required><Input value={f.full_name ?? ""} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></Field>
          <Field label="Phone"><Input value={f.phone ?? ""} onChange={(e) => setF({ ...f, phone: e.target.value })} /></Field>
          <Field label="Email"><Input type="email" value={f.email ?? ""} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
          <Field label="Guardian name"><Input value={f.guardian_name ?? ""} onChange={(e) => setF({ ...f, guardian_name: e.target.value })} /></Field>
          <Field label="Guardian phone"><Input value={f.guardian_phone ?? ""} onChange={(e) => setF({ ...f, guardian_phone: e.target.value })} /></Field>
          <Field label="Source"><Select value={f.source} onChange={(e) => setF({ ...f, source: e.target.value })}>{SOURCES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}</Select></Field>
          <Field label="Mode"><Select value={f.enquiry_mode} onChange={(e) => setF({ ...f, enquiry_mode: e.target.value })}>{["walk_in", "online", "phone", "email"].map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}</Select></Field>
          <Field label="Campaign"><RefSelect resource="campaigns" value={f.campaign_id ?? null} onChange={(v) => setF({ ...f, campaign_id: v ?? undefined })} /></Field>
          {f.source === "referral" && <Field label="Referred by student"><RefSelect resource="students" value={f.referred_by_student_id ?? null} onChange={(v) => setF({ ...f, referred_by_student_id: v ?? undefined })} /></Field>}
          <Field label="Course"><RefSelect resource="courses" value={f.course_id ?? null} onChange={(v) => setF({ ...f, course_id: v ?? undefined })} /></Field>
          <Field label="Interested subjects"><Input value={f.interested_subjects ?? ""} onChange={(e) => setF({ ...f, interested_subjects: e.target.value })} /></Field>
          <Field label="Assign to"><RefSelect resource="users" value={f.assigned_to_id ?? null} onChange={(v) => setF({ ...f, assigned_to_id: v ?? undefined })} /></Field>
          <Field label="First follow-up"><Input type="datetime-local" value={f.next_follow_up_at ?? ""} onChange={(e) => setF({ ...f, next_follow_up_at: e.target.value })} /></Field>
          <Field label="Notes" className="sm:col-span-2"><Textarea value={f.notes ?? ""} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field>
        </div>
      </Modal>
      <Modal open={dlg?.kind === "stage"} onOpenChange={() => setDlg(null)} title={`Move ${dlg?.e?.contact_name ?? ""} to ${String(f.stage ?? "").replace("_", " ")}`}
        footer={<Button loading={busy} disabled={f.stage === "lost" && !f.lost_reason} onClick={() => post(`/admissions/enquiries/${dlg!.e.id}/stage`, f, "Stage updated")}>Update</Button>}>
        <div className="space-y-3">
          {f.stage === "lost" && <Field label="Lost reason" required><Input value={f.lost_reason ?? ""} onChange={(e) => setF({ ...f, lost_reason: e.target.value })} /></Field>}
          <Field label="Counselling / call notes"><Textarea value={f.notes ?? ""} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field>
        </div>
      </Modal>
      <Modal open={dlg?.kind === "followup"} onOpenChange={() => setDlg(null)} title="Schedule follow-up"
        footer={<Button loading={busy} disabled={!f.due_at} onClick={async () => {
          setBusy(true);
          try { await api("/follow-ups", { method: "POST", body: { enquiry_id: dlg!.e.id, due_at: new Date(f.due_at).toISOString(), mode: f.mode, notes: f.notes || null, assigned_to_id: f.assigned_to_id || null } }); toast.success("Follow-up scheduled"); setDlg(null); q.refetch(); }
          catch (e) { toast.error(errorMessage(e)); } finally { setBusy(false); }
        }}>Schedule</Button>}>
        <div className="space-y-3">
          <Field label="When" required><Input type="datetime-local" value={f.due_at ?? ""} onChange={(e) => setF({ ...f, due_at: e.target.value })} /></Field>
          <Field label="Mode"><Select value={f.mode} onChange={(e) => setF({ ...f, mode: e.target.value })}>{["call", "sms", "whatsapp", "email", "visit", "meeting"].map((m) => <option key={m}>{m}</option>)}</Select></Field>
          <Field label="Assign to"><RefSelect resource="users" value={f.assigned_to_id ?? null} onChange={(v) => setF({ ...f, assigned_to_id: v })} /></Field>
          <Field label="Notes"><Textarea value={f.notes ?? ""} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field>
        </div>
      </Modal>
      <Modal open={dlg?.kind === "offer"} onOpenChange={() => setDlg(null)} title="Admission offer"
        footer={<Button loading={busy} onClick={() => post(`/admissions/enquiries/${dlg!.e.id}/offer`, { ...f, offer_amount: f.offer_amount || null, admission_fee: f.admission_fee || null, offer_valid_until: f.offer_valid_until || null }, "Offer recorded")}>Save offer</Button>}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Offer date"><Input type="date" value={f.offer_date ?? ""} onChange={(e) => setF({ ...f, offer_date: e.target.value })} /></Field>
          <Field label="Valid until"><Input type="date" value={f.offer_valid_until ?? ""} onChange={(e) => setF({ ...f, offer_valid_until: e.target.value })} /></Field>
          <Field label="Batch"><RefSelect resource="batches" value={f.offered_batch_id ?? null} onChange={(v) => setF({ ...f, offered_batch_id: v })} /></Field>
          <Field label="Fee plan"><RefSelect resource="fee-plans" value={f.offered_fee_plan_id ?? null} onChange={(v) => setF({ ...f, offered_fee_plan_id: v })} /></Field>
          <Field label="Agreed fee (per period)"><Input type="number" value={f.offer_amount ?? ""} onChange={(e) => setF({ ...f, offer_amount: e.target.value })} /></Field>
          <Field label="Admission fee"><Input type="number" value={f.admission_fee ?? ""} onChange={(e) => setF({ ...f, admission_fee: e.target.value })} /></Field>
          <Field label="Remarks" className="sm:col-span-2"><Textarea value={f.remarks ?? ""} onChange={(e) => setF({ ...f, remarks: e.target.value })} /></Field>
        </div>
      </Modal>
      <Modal open={dlg?.kind === "convert"} onOpenChange={() => setDlg(null)} title={`Enroll ${dlg?.e?.contact_name ?? ""}`} description="Creates the student, enrollment, fee agreement and admission-fee invoice in one transaction." wide
        footer={<Button loading={busy} disabled={!f.batch_id} onClick={() => post(`/admissions/enquiries/${dlg!.e.id}/convert`, { ...f, agreement_amount: f.agreement_amount || undefined, admission_fee: f.admission_fee || undefined, fee_plan_id: f.fee_plan_id || undefined, link_existing_student_id: f.link_existing_student_id || undefined }, "Student admitted")}>Admit</Button>}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Batch" required><RefSelect resource="batches" value={f.batch_id ?? null} onChange={(v) => setF({ ...f, batch_id: v })} /></Field>
          <Field label="Admission date"><Input type="date" value={f.admission_date ?? ""} onChange={(e) => setF({ ...f, admission_date: e.target.value })} /></Field>
          <Field label="Date of birth"><Input type="date" value={f.date_of_birth ?? ""} onChange={(e) => setF({ ...f, date_of_birth: e.target.value || undefined })} /></Field>
          <Field label="Student code (optional)"><Input value={f.student_code ?? ""} onChange={(e) => setF({ ...f, student_code: e.target.value || undefined })} /></Field>
          <Field label="Fee plan"><RefSelect resource="fee-plans" value={f.fee_plan_id ?? null} onChange={(v) => setF({ ...f, fee_plan_id: v })} /></Field>
          <Field label="Agreed amount"><Input type="number" value={f.agreement_amount ?? ""} onChange={(e) => setF({ ...f, agreement_amount: e.target.value })} /></Field>
          <Field label="Admission fee"><Input type="number" value={f.admission_fee ?? ""} onChange={(e) => setF({ ...f, admission_fee: e.target.value })} /></Field>
          {dups.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm sm:col-span-2">
              <p className="font-medium text-amber-800">Possible duplicates — link an existing record instead of creating a new one:</p>
              {dups.map((d) => (
                <label key={d.id} className="mt-1 flex items-center gap-2"><input type="radio" name="dup" checked={f.link_existing_student_id === d.id} onChange={() => setF({ ...f, link_existing_student_id: d.id })} /> {d.full_name} · {d.student_code} · {d.phone ?? ""}</label>
              ))}
            </div>
          )}
          <p className="text-xs text-slate-500 sm:col-span-2">Created {fmtDate(todayISO())}. Guardian details are copied from the lead.</p>
        </div>
      </Modal>
    </>
  );
}
