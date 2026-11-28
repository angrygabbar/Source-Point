"use client";

import { useQuery } from "@tanstack/react-query";
import { MoreHorizontal, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, ConfirmDialog, Field, Input, Menu, Modal, PageHeader, Select, SimpleTable, Skeleton, StatusBadge, Tabs } from "@/components/ui";
import { RefSelect } from "@/components/data/ref-select";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage, type Page } from "@/lib/api";
import { fmtDateTime } from "@/lib/utils";

/* eslint-disable @typescript-eslint/no-explicit-any */
interface Role { id: string; code: string; name: string; description: string | null; is_system: boolean; portal: string; permissions: string[] }
interface Perm { code: string; module: string; description: string; is_sensitive: boolean }

function RoleAssignments({ roles, value, onChange }: { roles: Role[]; value: { role_id: string; branch_id: string | null }[]; onChange: (v: { role_id: string; branch_id: string | null }[]) => void }) {
  const [role, setRole] = useState("");
  const [branch, setBranch] = useState<string | null>(null);
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1">{value.map((v, i) => <Badge key={i} tone="indigo">{roles.find((r) => r.id === v.role_id)?.name}{v.branch_id ? " (branch)" : ""} <button className="ml-1" onClick={() => onChange(value.filter((_, j) => j !== i))}>×</button></Badge>)}</div>
      <div className="flex gap-2">
        <Select value={role} onChange={(e) => setRole(e.target.value)}><option value="">Add role…</option>{roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}</Select>
        <div className="w-48"><RefSelect resource="branches" value={branch} onChange={setBranch} placeholder="All branches" /></div>
        <Button size="sm" variant="outline" disabled={!role} onClick={() => { onChange([...value, { role_id: role, branch_id: branch }]); setRole(""); setBranch(null); }}>Add</Button>
      </div>
    </div>
  );
}

function UsersTab({ roles }: { roles: Role[] }) {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const list = useQuery({ queryKey: ["users", q, page], queryFn: () => api<Page<any>>("/users", { query: { q: q || undefined, page } }) });
  const [create, setCreate] = useState(false);
  const [f, setF] = useState<any>({ roles: [] });
  const [editRoles, setEditRoles] = useState<any>(null);
  const [temp, setTemp] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<{ user: any; action: string } | null>(null);
  const act = async (path: string, msg: string, body?: unknown) => {
    try { const r = await api<any>(path, { method: "POST", body }); toast.success(msg); list.refetch(); return r; } catch (e) { toast.error(errorMessage(e)); }
  };
  return (
    <Card title="Users" actions={<><Input className="w-56" placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} /><Button size="sm" onClick={() => { setF({ roles: [] }); setCreate(true); }}><Plus className="h-4 w-4" /> New user</Button></>} bodyClass="p-0">
      {list.isLoading ? <Skeleton className="m-4 h-40" /> : (
        <SimpleTable headers={["Name", "Email", "Roles", "Status", "Last login", ""]}
          rows={(list.data?.items ?? []).map((u) => [u.full_name, u.email, <span key="r" className="flex flex-wrap gap-1">{u.roles.map((r: any, i: number) => <Badge key={i}>{r.name}{r.branch_id ? "*" : ""}</Badge>)}</span>,
            <span key="s" className="flex gap-1"><StatusBadge value={u.is_active ? "active" : "inactive"} />{u.locked_until && new Date(u.locked_until) > new Date() && <Badge tone="red">locked</Badge>}{u.closure_requested_at && <Badge tone="amber">closure requested</Badge>}</span>,
            fmtDateTime(u.last_login_at),
            <Menu key="m" trigger={<Button size="icon" variant="ghost" aria-label="User actions"><MoreHorizontal className="h-4 w-4" /></Button>} items={[
              { label: "Edit roles", onClick: () => setEditRoles({ ...u, assignments: u.roles.map((r: any) => ({ role_id: r.role_id, branch_id: r.branch_id })) }) },
              { label: u.is_active ? "Deactivate" : "Activate", danger: u.is_active, onClick: () => setConfirm({ user: u, action: u.is_active ? "deactivate" : "activate" }) },
              { label: "Generate password reset link", onClick: async () => { const r = await act(`/users/${u.id}/reset-link`, "Reset link generated"); if (r) setTemp(`${window.location.origin}${new URL(r.reset_url).pathname}${new URL(r.reset_url).search}`); } },
              { label: "Unlock account", onClick: () => act(`/users/${u.id}/unlock`, "Unlocked") },
              { label: "Revoke all sessions", danger: true, onClick: () => act(`/users/${u.id}/revoke-sessions`, "Sessions revoked") },
            ]} />])} />
      )}
      {list.data && list.data.total > list.data.page_size && <div className="flex justify-end gap-2 p-2"><Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button><Button size="sm" variant="outline" disabled={page * list.data.page_size >= list.data.total} onClick={() => setPage(page + 1)}>Next</Button></div>}
      <Modal open={create} onOpenChange={setCreate} title="New user" description="Staff accounts. Student, teacher and parent logins are created from their records."
        footer={<Button disabled={!f.email || !f.full_name} onClick={async () => {
          try { const r = await api<any>("/users", { method: "POST", body: { ...f, password: f.password || undefined, phone: f.phone || undefined } }); setCreate(false); list.refetch(); if (r.temporary_password) setTemp(`Temporary password for ${r.email}: ${r.temporary_password}`); } catch (e) { toast.error(errorMessage(e)); }
        }}>Create</Button>}>
        <div className="space-y-3">
          <Field label="Full name" required><Input value={f.full_name ?? ""} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></Field>
          <Field label="Email" required><Input type="email" value={f.email ?? ""} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
          <Field label="Phone"><Input value={f.phone ?? ""} onChange={(e) => setF({ ...f, phone: e.target.value })} /></Field>
          <Field label="Password" hint="Leave blank to generate a one-time temporary password"><Input type="password" autoComplete="new-password" value={f.password ?? ""} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
          <Field label="Roles"><RoleAssignments roles={roles} value={f.roles} onChange={(v) => setF({ ...f, roles: v })} /></Field>
        </div>
      </Modal>
      <Modal open={!!editRoles} onOpenChange={() => setEditRoles(null)} title={`Roles · ${editRoles?.full_name ?? ""}`}
        footer={<Button onClick={async () => { try { await api(`/users/${editRoles.id}/roles`, { method: "PUT", body: editRoles.assignments }); toast.success("Roles updated"); setEditRoles(null); list.refetch(); } catch (e) { toast.error(errorMessage(e)); } }}>Save</Button>}>
        {editRoles && <RoleAssignments roles={roles} value={editRoles.assignments} onChange={(v) => setEditRoles({ ...editRoles, assignments: v })} />}
      </Modal>
      <Modal open={!!temp} onOpenChange={() => setTemp(null)} title="Share securely" description="Shown once. Share through a trusted channel; the user must change it at first login.">
        <p className="break-all rounded bg-slate-50 p-3 font-mono text-sm">{temp}</p>
      </Modal>
      <ConfirmDialog open={!!confirm} onOpenChange={() => setConfirm(null)} title={`${confirm?.action === "deactivate" ? "Deactivate" : "Activate"} ${confirm?.user.full_name ?? ""}`} danger={confirm?.action === "deactivate"}
        message={confirm?.action === "deactivate" ? "The user is signed out of all sessions immediately." : undefined}
        onConfirm={async () => { try { await api(`/users/${confirm!.user.id}`, { method: "PATCH", body: { is_active: confirm!.action === "activate" } }); toast.success("Updated"); list.refetch(); } catch (e) { toast.error(errorMessage(e)); } }} />
    </Card>
  );
}

function RolesTab({ roles, perms, reload }: { roles: Role[]; perms: Perm[]; reload: () => void }) {
  const { can } = useSession();
  const [edit, setEdit] = useState<(Partial<Role> & { permissions: string[] }) | null>(null);
  const modules = useMemo(() => Array.from(new Set(perms.map((p) => p.module))), [perms]);
  return (
    <Card title="Roles & permissions" actions={can("roles.write") && <Button size="sm" onClick={() => setEdit({ code: "", name: "", portal: "admin", permissions: [] })}><Plus className="h-4 w-4" /> Custom role</Button>} bodyClass="p-0">
      <SimpleTable headers={["Role", "Portal", "Permissions", "Type", ""]}
        rows={roles.map((r) => [r.name, r.portal, r.permissions.length, r.is_system ? <Badge key="s">system</Badge> : <Badge key="c" tone="indigo">custom</Badge>,
          <Button key="v" size="sm" variant="ghost" onClick={() => setEdit({ ...r })}>{r.is_system || !can("roles.write") ? "View" : "Edit"}</Button>])} />
      <Modal open={!!edit} onOpenChange={() => setEdit(null)} title={edit?.id ? edit.name ?? "Role" : "New custom role"} wide
        footer={edit && !edit.is_system && can("roles.write") ? (
          <>
            {edit.id && <Button variant="danger" onClick={async () => { try { await api(`/roles/${edit.id}`, { method: "DELETE" }); toast.success("Deleted"); setEdit(null); reload(); } catch (e) { toast.error(errorMessage(e)); } }}>Delete</Button>}
            <Button onClick={async () => {
              const body = { code: edit.code, name: edit.name, description: edit.description, portal: edit.portal, permissions: edit.permissions };
              try { await api(edit.id ? `/roles/${edit.id}` : "/roles", { method: edit.id ? "PUT" : "POST", body }); toast.success("Saved"); setEdit(null); reload(); } catch (e) { toast.error(errorMessage(e)); }
            }}>Save</Button>
          </>
        ) : undefined}>
        {edit && (
          <div className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Code"><Input disabled={!!edit.id} value={edit.code ?? ""} onChange={(e) => setEdit({ ...edit, code: e.target.value })} placeholder="e.g. front_desk" /></Field>
              <Field label="Name"><Input disabled={edit.is_system} value={edit.name ?? ""} onChange={(e) => setEdit({ ...edit, name: e.target.value })} /></Field>
              <Field label="Portal"><Select disabled={edit.is_system} value={edit.portal} onChange={(e) => setEdit({ ...edit, portal: e.target.value })}>{["admin", "teacher", "student", "parent"].map((p) => <option key={p}>{p}</option>)}</Select></Field>
            </div>
            <div className="max-h-[50vh] space-y-2 overflow-y-auto rounded-lg border border-slate-200 p-3">
              {modules.map((m) => (
                <div key={m}>
                  <p className="text-xs font-semibold uppercase text-slate-500">{m.replace(/_/g, " ")}</p>
                  <div className="flex flex-wrap gap-x-4 gap-y-1">
                    {perms.filter((p) => p.module === m).map((p) => (
                      <label key={p.code} className="flex items-center gap-1.5 text-xs" title={p.description}>
                        <input type="checkbox" disabled={edit.is_system} checked={edit.permissions.includes(p.code)}
                          onChange={(e) => setEdit({ ...edit, permissions: e.target.checked ? [...edit.permissions, p.code] : edit.permissions.filter((x) => x !== p.code) })} />
                        {p.code.split(".")[1]?.replace(/_/g, " ")}{p.is_sensitive && <span className="text-red-500">*</span>}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs text-slate-500">* sensitive permission. You cannot grant permissions you do not hold.</p>
          </div>
        )}
      </Modal>
    </Card>
  );
}

function LoginHistoryTab() {
  const q = useQuery({ queryKey: ["login-history"], queryFn: () => api<Page<any>>("/login-history") });
  return (
    <Card title="Login monitoring" bodyClass="p-0">
      <SimpleTable headers={["When", "Email", "Result", "Reason", "IP", "Device"]}
        rows={(q.data?.items ?? []).map((r) => [fmtDateTime(r.created_at), r.email, r.success ? <Badge key="s" tone="green">success</Badge> : <Badge key="f" tone="red">failed</Badge>, r.reason, r.ip_address, <span key="u" className="block max-w-xs truncate text-xs">{r.user_agent}</span>])} />
    </Card>
  );
}

export default function UsersPage() {
  const { can } = useSession();
  const roles = useQuery({ queryKey: ["roles"], queryFn: () => api<Role[]>("/roles") });
  const perms = useQuery({ queryKey: ["permissions"], queryFn: () => api<Perm[]>("/permissions"), enabled: can("roles.read") });
  return (
    <>
      <PageHeader title="Users, roles & access" description="Role-based access with optional branch scoping. All changes are audited." />
      <Tabs tabs={[
        { value: "users", label: "Users", content: <UsersTab roles={roles.data ?? []} /> },
        { value: "roles", label: "Roles", content: <RolesTab roles={roles.data ?? []} perms={perms.data ?? []} reload={() => roles.refetch()} />, hidden: !can("roles.read") },
        { value: "logins", label: "Login history", content: <LoginHistoryTab />, hidden: !can("audit.read") },
      ]} />
    </>
  );
}
