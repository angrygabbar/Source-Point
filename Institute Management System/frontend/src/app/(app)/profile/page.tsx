"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, ConfirmDialog, Field, Input, PageHeader, SimpleTable } from "@/components/ui";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage } from "@/lib/api";
import { fmtDateTime } from "@/lib/utils";

/* eslint-disable @typescript-eslint/no-explicit-any */
function Profile() {
  const { me, reload, signOut } = useSession();
  const router = useRouter();
  const mustChangePassword = Boolean(me?.user.must_change_password);
  const force = useSearchParams().get("force") === "1" || mustChangePassword;
  const [name, setName] = useState(me?.user.full_name ?? "");
  const [phone, setPhone] = useState(me?.user.phone ?? "");
  const [pw, setPw] = useState({ current_password: "", new_password: "", confirm: "" });
  const [closing, setClosing] = useState(false);
  const sessions = useQuery({ queryKey: ["my-sessions"], queryFn: () => api<any[]>("/auth/sessions") });
  const history = useQuery({ queryKey: ["my-logins"], queryFn: () => api<any[]>("/auth/login-history") });

  return (
    <>
      <PageHeader title="My profile & security" />
      {force && <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">Please set a new password to continue.</div>}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Profile">
          <div className="space-y-3">
            <Field label="Email"><Input value={me?.user.email ?? ""} disabled /></Field>
            <Field label="Full name"><Input value={name} onChange={(e) => setName(e.target.value)} /></Field>
            <Field label="Phone"><Input value={phone} onChange={(e) => setPhone(e.target.value)} /></Field>
            <Button onClick={async () => { try { await api("/auth/me", { method: "PATCH", body: { full_name: name, phone } }); toast.success("Saved"); reload(); } catch (e) { toast.error(errorMessage(e)); } }}>Save</Button>
          </div>
        </Card>
        <Card title="Change password">
          <div className="space-y-3">
            {!mustChangePassword && <Field label="Current password"><Input type="password" autoComplete="current-password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} /></Field>}
            <Field label="New password" hint="≥10 characters with 3 of: upper, lower, digit, symbol"><Input type="password" autoComplete="new-password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></Field>
            <Field label="Confirm new password"><Input type="password" autoComplete="new-password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} /></Field>
            <Button disabled={(!mustChangePassword && !pw.current_password) || pw.new_password.length < 10 || pw.new_password !== pw.confirm} onClick={async () => {
              try { await api("/auth/change-password", { method: "POST", body: { current_password: mustChangePassword ? null : pw.current_password, new_password: pw.new_password } }); toast.success("Password changed. Other sessions were signed out."); setPw({ current_password: "", new_password: "", confirm: "" }); await reload(); router.replace("/dashboard"); }
              catch (e) { toast.error(errorMessage(e)); }
            }}>Change password</Button>
          </div>
        </Card>
        <Card title="Active sessions" actions={<Button size="sm" variant="danger" onClick={async () => { await api("/auth/logout-all", { method: "POST" }); await signOut(); router.replace("/login"); }}>Sign out everywhere</Button>} bodyClass="p-0">
          <SimpleTable headers={["Started", "IP", "Device", ""]} rows={(sessions.data ?? []).map((s) => [fmtDateTime(s.created_at), s.ip_address, <span key="u" className="block max-w-xs truncate text-xs">{s.user_agent}</span>,
            <Button key="r" size="sm" variant="ghost" onClick={async () => { await api(`/auth/sessions/${s.id}`, { method: "DELETE" }); sessions.refetch(); }}>Revoke</Button>])} />
        </Card>
        <Card title="Recent sign-ins" bodyClass="p-0">
          <SimpleTable headers={["When", "Result", "IP"]} rows={(history.data ?? []).map((h) => [fmtDateTime(h.created_at), h.success ? <Badge key="s" tone="green">success</Badge> : <Badge key="f" tone="red">{h.reason}</Badge>, h.ip_address])} />
        </Card>
        <Card title="Privacy & data">
          <p className="mb-3 text-sm text-slate-600">Download the personal data held in your account, or request account closure. Statutory academic and financial records are retained as required.</p>
          <div className="flex gap-2">
            <Button variant="outline" onClick={async () => {
              const data = await api("/auth/my-data");
              const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
              const a = document.createElement("a");
              a.href = URL.createObjectURL(blob);
              a.download = "my-classflow-data.json";
              a.click();
            }}>Export my data</Button>
            <Button variant="danger" onClick={() => setClosing(true)}>Request account closure</Button>
          </div>
        </Card>
      </div>
      <ConfirmDialog open={closing} onOpenChange={setClosing} title="Request account closure" danger confirmLabel="Submit request"
        message="An administrator will review your request." onConfirm={async () => { const r = await api<{ message: string }>("/auth/request-account-closure", { method: "POST" }); toast.success(r.message); }} />
    </>
  );
}

export default function ProfilePage() {
  return <Suspense><Profile /></Suspense>;
}
