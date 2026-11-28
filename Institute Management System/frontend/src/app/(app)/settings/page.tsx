"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, ErrorState, Field, Input, Modal, PageHeader, SimpleTable, Skeleton, StatusBadge, Tabs } from "@/components/ui";
import { ResourceList } from "@/components/data/resource-list";
import { useSession } from "@/hooks/use-session";
import { API_BASE, api, errorMessage } from "@/lib/api";
import { fmtDateTime } from "@/lib/utils";

/* eslint-disable @typescript-eslint/no-explicit-any */

function InstituteTab() {
  const { reload } = useSession();
  const q = useQuery({ queryKey: ["institute"], queryFn: () => api<any>("/institutes/current") });
  const [f, setF] = useState<Record<string, any>>({});
  const logo = useRef<HTMLInputElement>(null);
  useEffect(() => { if (q.data) setF(q.data); }, [q.data]);
  if (q.isLoading) return <Skeleton className="h-64" />;
  if (q.isError) return <ErrorState error={q.error} />;
  const fields: [string, string, string?][] = [
    ["name", "Institute name"], ["legal_name", "Legal name"], ["phone", "Phone"], ["email", "Email", "email"], ["website", "Website"],
    ["address", "Address"], ["city", "City"], ["state", "State"], ["postal_code", "PIN code"], ["timezone", "Timezone"], ["currency", "Currency (ISO)"],
    ["locale", "Locale"], ["date_format", "Date format"], ["invoice_prefix", "Invoice prefix"], ["receipt_prefix", "Receipt prefix"],
    ["financial_year_start_month", "FY start month (1-12)", "number"], ["primary_color", "Primary colour", "color"], ["secondary_color", "Secondary colour", "color"],
    ["accent_color", "Accent colour", "color"], ["tax_label", "Tax label"], ["tax_rate", "Default tax rate %", "number"], ["tax_registration_number", "GSTIN / tax registration"],
  ];
  const save = async () => {
    const body: Record<string, any> = {};
    fields.forEach(([k]) => { if (f[k] !== q.data[k]) body[k] = f[k] === "" ? null : f[k]; });
    if (f.tax_enabled !== q.data.tax_enabled) body.tax_enabled = f.tax_enabled;
    if (body.tax_rate !== undefined && body.tax_rate !== null) body.tax_rate = Number(body.tax_rate);
    if (body.financial_year_start_month) body.financial_year_start_month = Number(body.financial_year_start_month);
    try { await api("/institutes/current", { method: "PATCH", body }); toast.success("Saved"); q.refetch(); reload(); } catch (e) { toast.error(errorMessage(e)); }
  };
  return (
    <Card title="Institute profile, branding & tax" actions={<Button size="sm" onClick={save}>Save</Button>}>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {fields.map(([k, label, type]) => (
          <Field key={k} label={label}><Input type={type ?? "text"} value={f[k] ?? ""} onChange={(e) => setF({ ...f, [k]: e.target.value })} className={type === "color" ? "h-9 p-1" : undefined} /></Field>
        ))}
        <Field label="Tax (GST) applicable"><label className="flex h-9 items-center gap-2 text-sm"><input type="checkbox" checked={!!f.tax_enabled} onChange={(e) => setF({ ...f, tax_enabled: e.target.checked })} /> Charge tax on applicable fee plans</label></Field>
        <Field label="Logo (PNG/JPG/WebP)">
          <input ref={logo} type="file" accept="image/png,image/jpeg,image/webp" className="text-sm" onChange={async () => {
            const file = logo.current?.files?.[0];
            if (!file) return;
            const form = new FormData();
            form.append("file", file);
            try { await api("/institutes/current/logo", { method: "POST", form }); toast.success("Logo updated"); reload(); } catch (e) { toast.error(errorMessage(e)); }
          }} />
        </Field>
      </div>
      <p className="mt-3 text-xs text-slate-500">Tax rules are configurable and not assumed — enable GST only if your institute is registered and fees are taxable.</p>
    </Card>
  );
}

function FlagsTab() {
  const { can, reload } = useSession();
  const q = useQuery({ queryKey: ["flags"], queryFn: () => api<{ key: string; enabled: boolean; description: string }[]>("/settings/feature-flags") });
  if (!q.data) return <Skeleton className="h-64" />;
  return (
    <Card title="Modules & feature flags">
      <p className="mb-3 text-sm text-slate-500">Disabled modules disappear from navigation and their APIs return a clear "module disabled" response. Authentication, authorisation, audit and integrity safeguards cannot be disabled.</p>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {q.data.map((f) => (
          <label key={f.key} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm">
            <span><span className="font-medium">{f.description}</span><span className="block text-xs text-slate-400">{f.key}</span></span>
            <input type="checkbox" disabled={!can("settings.write")} checked={f.enabled} onChange={async (e) => {
              try { await api("/settings/feature-flags", { method: "PUT", body: { [f.key]: e.target.checked } }); q.refetch(); reload(); } catch (err) { toast.error(errorMessage(err)); }
            }} />
          </label>
        ))}
      </div>
    </Card>
  );
}

function AppSettingsTab() {
  const q = useQuery({ queryKey: ["app-settings"], queryFn: () => api<Record<string, any>>("/settings/app") });
  const [v, setV] = useState<Record<string, any>>({});
  useEffect(() => { if (q.data) setV(q.data); }, [q.data]);
  if (!q.data) return <Skeleton className="h-64" />;
  const save = async () => {
    const body: Record<string, any> = {};
    Object.keys(v).forEach((k) => { if (JSON.stringify(v[k]) !== JSON.stringify(q.data![k])) body[k] = v[k]; });
    try { await api("/settings/app", { method: "PUT", body }); toast.success("Saved"); q.refetch(); } catch (e) { toast.error(errorMessage(e)); }
  };
  return (
    <Card title="Operational settings" actions={<Button size="sm" onClick={save}>Save</Button>}>
      <div className="grid gap-3 sm:grid-cols-2">
        {Object.entries(v).map(([k, val]) => (
          <Field key={k} label={k.replace(/[._]/g, " ")}>
            {typeof val === "boolean" ? <label className="flex h-9 items-center gap-2 text-sm"><input type="checkbox" checked={val} onChange={(e) => setV({ ...v, [k]: e.target.checked })} /> Enabled</label>
              : Array.isArray(val) ? <Input value={val.join(",")} onChange={(e) => setV({ ...v, [k]: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })} />
              : <Input type="number" value={val} onChange={(e) => setV({ ...v, [k]: Number(e.target.value) })} />}
          </Field>
        ))}
      </div>
    </Card>
  );
}

function IntegrationsTab() {
  const { can } = useSession();
  const q = useQuery({ queryKey: ["integrations"], queryFn: () => api<any[]>("/integrations") });
  const [edit, setEdit] = useState<any>(null);
  const [form, setForm] = useState<{ is_enabled: boolean; config: Record<string, string>; secrets: Record<string, string> }>({ is_enabled: false, config: {}, secrets: {} });
  if (!q.data) return <Skeleton className="h-64" />;
  return (
    <Card title="External integrations" bodyClass="p-0">
      <p className="px-4 pt-3 text-sm text-slate-500">All providers are disabled until credentials are entered. Secrets are encrypted at rest and never displayed again. ClassFlow never simulates deliveries or payments.</p>
      <SimpleTable headers={["Type", "Provider", "Status", "Secrets", ""]}
        rows={q.data.map((i) => [i.provider_type, i.label, i.is_enabled ? <Badge key="e" tone="green">enabled</Badge> : <Badge key="d">disabled</Badge>,
          Object.entries(i.secrets_set).map(([k, set]) => `${k}: ${set ? "set" : "missing"}`).join(", "),
          can("integrations.write") ? <Button key="c" size="sm" variant="outline" onClick={() => { setEdit(i); setForm({ is_enabled: i.is_enabled, config: { ...i.config }, secrets: {} }); }}>Configure</Button> : null])} />
      <Modal open={!!edit} onOpenChange={() => setEdit(null)} title={`Configure ${edit?.label ?? ""}`}
        footer={<Button onClick={async () => {
          try { await api(`/integrations/${edit.provider_type}/${edit.provider}`, { method: "PUT", body: form }); toast.success("Saved"); setEdit(null); q.refetch(); } catch (e) { toast.error(errorMessage(e)); }
        }}>Save</Button>}>
        {edit && (
          <div className="space-y-3">
            {edit.config_fields.map((k: string) => <Field key={k} label={k.replace(/_/g, " ")}><Input value={form.config[k] ?? ""} onChange={(e) => setForm({ ...form, config: { ...form.config, [k]: e.target.value } })} /></Field>)}
            {edit.secret_fields.map((k: string) => <Field key={k} label={`${k.replace(/_/g, " ")} (secret)`} hint={edit.secrets_set[k] ? "Stored — leave blank to keep" : "Not set"}><Input type="password" autoComplete="new-password" value={form.secrets[k] ?? ""} onChange={(e) => setForm({ ...form, secrets: { ...form.secrets, [k]: e.target.value } })} /></Field>)}
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.is_enabled} onChange={(e) => setForm({ ...form, is_enabled: e.target.checked })} /> Enable this provider (disables other providers of the same type)</label>
            {edit.provider_type === "payment" && <p className="text-xs text-slate-500">Webhook URL: <code>{typeof window !== "undefined" ? window.location.origin : ""}{API_BASE}/webhooks/razorpay/&lt;institute-id&gt;</code></p>}
            <p className="text-xs text-slate-500">Also enable the matching module under Feature flags (email, sms, whatsapp, push, online payments, AI, video meetings).</p>
          </div>
        )}
      </Modal>
    </Card>
  );
}

function ApiKeysTab() {
  const q = useQuery({ queryKey: ["api-keys"], queryFn: () => api<any[]>("/api-keys") });
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState("students.read,sessions.read");
  const [created, setCreated] = useState<string | null>(null);
  return (
    <Card title="API keys (for future mobile apps & integrations)" bodyClass="p-0">
      <div className="flex flex-wrap items-end gap-2 p-4">
        <Field label="Name"><Input value={name} onChange={(e) => setName(e.target.value)} /></Field>
        <Field label="Scopes (permission codes, comma separated)" className="flex-1"><Input value={scopes} onChange={(e) => setScopes(e.target.value)} /></Field>
        <Button disabled={name.length < 2} onClick={async () => {
          try { const r = await api<{ api_key: string }>("/api-keys", { method: "POST", body: { name, scopes: scopes.split(",").map((s) => s.trim()).filter(Boolean) } }); setCreated(r.api_key); q.refetch(); } catch (e) { toast.error(errorMessage(e)); }
        }}>Create key</Button>
      </div>
      {created && <p className="mx-4 mb-3 rounded bg-amber-50 p-2 font-mono text-xs text-amber-900">Copy now — shown once: {created}</p>}
      <SimpleTable headers={["Name", "Prefix", "Scopes", "Last used", "Expires", "Status", ""]}
        rows={(q.data ?? []).map((k) => [k.name, k.key_prefix, k.scopes.join(", "), fmtDateTime(k.last_used_at), fmtDateTime(k.expires_at), k.revoked_at ? <StatusBadge key="s" value="cancelled" /> : <StatusBadge key="s" value="active" />,
          !k.revoked_at && <Button key="r" size="sm" variant="ghost" onClick={async () => { await api(`/api-keys/${k.id}`, { method: "DELETE" }); q.refetch(); }}>Revoke</Button>])} />
    </Card>
  );
}

export default function SettingsPage() {
  const { can } = useSession();
  return (
    <>
      <PageHeader title="Settings" description="Institute configuration, modules, integrations and platform controls." />
      <Tabs tabs={[
        { value: "institute", label: "Institute & branding", content: <InstituteTab />, hidden: !can("institutes.write", "tenant.admin") },
        { value: "flags", label: "Modules", content: <FlagsTab /> },
        { value: "app", label: "Operational settings", content: <AppSettingsTab />, hidden: !can("settings.read") },
        { value: "integrations", label: "Integrations", content: <IntegrationsTab />, hidden: !can("integrations.read") },
        { value: "templates", label: "Notification templates", content: <ResourceList resource="notification-templates" />, hidden: !can("notifications.read") },
        { value: "deliveries", label: "Delivery log", content: <ResourceList resource="notification-deliveries" />, hidden: !can("notifications.read") },
        { value: "custom", label: "Custom fields", content: <ResourceList resource="custom-fields" />, hidden: !can("settings.read") },
        { value: "webhooks", label: "Webhooks & API keys", content: <div className="space-y-4"><ResourceList resource="webhook-endpoints" /><ResourceList resource="webhook-deliveries" compact /><ApiKeysTab /></div>, hidden: !can("webhooks.read") },
        { value: "jobs", label: "Background jobs", content: <ResourceList resource="jobs" />, hidden: !can("imports.read") },
        { value: "usage", label: "Usage & subscription", content: <div className="space-y-4"><ResourceList resource="usage-records" /><ResourceList resource="tenant-subscriptions" compact /></div>, hidden: !can("saas.read") },
      ]} />
    </>
  );
}
