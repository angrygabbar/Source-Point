"use client";

import { useEffect, useState, type ReactNode } from "react";

import { useTheme } from "@/app/providers";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, Input, Select, Switch } from "@/components/ui/field";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { Segmented } from "@/components/ui/segmented";
import { ErrorState, Notice, Skeleton } from "@/components/ui/states";
import { useApi, useApiMutation } from "@/hooks/use-api";
import { api } from "@/services/api";
import type { AppSettings, Envelope } from "@/services/types";

function Row({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <div className="grid gap-2 py-3 sm:grid-cols-[260px_1fr] sm:items-center">
      <div>
        <p className="text-sm font-medium">{label}</p>
        {hint ? <p className="text-2xs leading-4 text-faint">{hint}</p> : null}
      </div>
      <div>{children}</div>
    </div>
  );
}

function Flag({ ok, yes = "Yes", no = "No" }: { ok: boolean; yes?: string; no?: string }) {
  return ok ? <Badge tone="positive">{yes}</Badge> : <Badge tone="muted">{no}</Badge>;
}

export default function SettingsPage() {
  const q = useApi<Envelope<AppSettings>>("/settings");
  const { theme, setTheme } = useTheme();
  const [form, setForm] = useState({
    scan_interval_minutes: "15",
    supercoin_value_inr: "",
    retention_days_scan_runs: "90",
    retention_days_notifications: "180",
    price_snapshot_min_interval_minutes: "60",
    default_theme: "light",
    monitor_new_submissions: true,
  });
  useEffect(() => {
    const s = q.data?.data;
    if (!s) return;
    setForm({
      scan_interval_minutes: String(s.scan_interval_minutes),
      supercoin_value_inr: s.supercoin_value_inr === null ? "" : String(s.supercoin_value_inr),
      retention_days_scan_runs: String(s.retention_days_scan_runs),
      retention_days_notifications: String(s.retention_days_notifications),
      price_snapshot_min_interval_minutes: String(s.price_snapshot_min_interval_minutes),
      default_theme: s.default_theme,
      monitor_new_submissions: s.monitor_new_submissions,
    });
  }, [q.data]);

  const save = useApiMutation((body: Record<string, unknown>) => api.put("/settings", body), { invalidate: ["/settings", "/products", "/offers", "/dashboard"], success: "Settings saved" });
  const submit = () =>
    save.mutate({
      scan_interval_minutes: Number(form.scan_interval_minutes),
      ...(form.supercoin_value_inr === "" ? { clear_supercoin_value: true } : { supercoin_value_inr: Number(form.supercoin_value_inr) }),
      retention_days_scan_runs: Number(form.retention_days_scan_runs),
      retention_days_notifications: Number(form.retention_days_notifications),
      price_snapshot_min_interval_minutes: Number(form.price_snapshot_min_interval_minutes),
      default_theme: form.default_theme,
      monitor_new_submissions: form.monitor_new_submissions,
    });
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }));

  if (q.isLoading) return <Skeleton className="h-96" />;
  if (q.error || !q.data) return <ErrorState message={q.error?.message} onRetry={() => q.refetch()} />;
  const env = q.data.data.environment;

  return (
    <>
      <PageHeader
        title="Settings"
        description="Operator-editable settings are stored in the database. Credentials and access permissions are read from the environment and shown read-only."
        actions={
          <Button size="sm" variant="primary" loading={save.isPending} onClick={submit}>
            Save settings
          </Button>
        }
      />
      <div className="space-y-3">
        <Panel>
          <PanelHeader title="Scanner" />
          <PanelBody className="divide-y divide-line py-0">
            <Row label="Scan interval" hint="Minutes between scheduled scans. A running scan is never duplicated.">
              <Select className="w-48" value={form.scan_interval_minutes} onChange={set("scan_interval_minutes")}>
                {[5, 10, 15, 30, 60, 120, 360, 720, 1440].map((m) => (
                  <option key={m} value={m}>
                    Every {m < 60 ? `${m} minutes` : `${m / 60} hour${m === 60 ? "" : "s"}`}
                  </option>
                ))}
              </Select>
            </Row>
            <Row label="Price snapshot interval" hint="Minimum minutes between identical price observations. Changes are always recorded.">
              <Input className="w-32" type="number" min={5} max={1440} value={form.price_snapshot_min_interval_minutes} onChange={set("price_snapshot_min_interval_minutes")} />
            </Row>
            <Row label="Monitor new submissions" hint="Default for newly submitted URLs.">
              <Switch checked={form.monitor_new_submissions} onChange={(v) => setForm((f) => ({ ...f, monitor_new_submissions: v }))} label="Monitor new submissions" />
            </Row>
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader title="Valuation assumption" />
          <PanelBody className="divide-y divide-line py-0">
            <Row
              label="SuperCoin value (₹ per coin)"
              hint="Used only for labelled estimates of redemption value and effective cost. Leave blank to show no rupee estimates. One SuperCoin is never assumed to equal ₹1."
            >
              <div className="flex items-center gap-2">
                <Input className="w-32" type="number" min={0} max={10} step="0.01" placeholder="Not set" value={form.supercoin_value_inr} onChange={set("supercoin_value_inr")} />
                {form.supercoin_value_inr !== "" ? (
                  <Button size="sm" variant="ghost" onClick={() => setForm((f) => ({ ...f, supercoin_value_inr: "" }))}>
                    Clear
                  </Button>
                ) : null}
              </div>
            </Row>
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader title="Retention" />
          <PanelBody className="divide-y divide-line py-0">
            <Row label="Scan run logs" hint="Days to keep completed scan runs. Price and offer history are never deleted.">
              <Input className="w-32" type="number" min={7} max={3650} value={form.retention_days_scan_runs} onChange={set("retention_days_scan_runs")} />
            </Row>
            <Row label="Notification history" hint="Days to keep delivered, suppressed or failed notifications.">
              <Input className="w-32" type="number" min={7} max={3650} value={form.retention_days_notifications} onChange={set("retention_days_notifications")} />
            </Row>
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader title="Appearance & locale" />
          <PanelBody className="divide-y divide-line py-0">
            <Row label="Theme (this browser)">
              <Segmented value={theme} onChange={setTheme} options={[{ value: "light", label: "Light" }, { value: "dark", label: "Dark" }]} />
            </Row>
            <Row label="Default theme" hint="Stored preference for new browsers.">
              <Select className="w-32" value={form.default_theme} onChange={set("default_theme")}>
                <option value="light">Light</option>
                <option value="dark">Dark</option>
              </Select>
            </Row>
            <Row label="Timezone / currency" hint="Timestamps are stored in UTC and displayed in this timezone.">
              <span className="text-sm">
                {q.data.data.display_timezone} · {q.data.data.currency}
              </span>
            </Row>
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader title="Environment (read-only)" description="Change these in the .env file and restart the services" />
          <PanelBody className="divide-y divide-line py-0">
            <Row label="Product-page access" hint="Requires both flags; set only after confirming automated access is permitted.">
              <div className="flex flex-wrap gap-1.5">
                <Flag ok={env.product_page_fetch_enabled} yes="Fetch enabled" no="Fetch disabled" />
                <Flag ok={env.product_page_permission_confirmed} yes="Permission confirmed" no="Permission not confirmed" />
              </div>
            </Row>
            <Row label="Search APIs">
              <div className="flex flex-wrap gap-1.5">
                <Flag ok={env.google_cse_configured} yes="Google CSE ready" no="Google CSE not configured" />
                <Flag ok={env.brave_search_configured} yes="Brave ready" no="Brave not configured" />
              </div>
            </Row>
            <Row label="Telegram">
              <div className="flex flex-wrap gap-1.5">
                <Flag ok={env.telegram_configured} yes="Configured" no="Not configured" />
                <Flag ok={!env.telegram_dry_run} yes="Live delivery" no="Dry run" />
                <Flag ok={env.telegram_commands_enabled} yes="Commands on" no="Commands off" />
              </div>
            </Row>
            <Row label="Allowed Flipkart hosts">
              <span className="font-mono text-xs">{env.flipkart_allowed_hosts.join(", ")}</span>
            </Row>
            <Row label="Third-party feed hosts">
              <span className="font-mono text-xs">{env.third_party_allowed_hosts.join(", ") || "None"}</span>
            </Row>
            <Row label="Module access">
              <Badge tone="positive">SourcePoint administrators only</Badge>
            </Row>
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader title="Backup & recovery" />
          <PanelBody className="space-y-2 text-xs text-muted">
            <p>CoinBack data lives in the SourcePoint database schema named <code>coinback</code>. From the SourcePoint repository root:</p>
            <pre className="overflow-x-auto rounded border border-line bg-subtle/60 p-2.5 font-mono text-[11px] text-fg">
{`./coinback-finder/scripts/backup.sh
./coinback-finder/scripts/restore.sh coinback-finder/backups/<file>.sql.gz
./coinback-finder/scripts/health-check.sh`}
            </pre>
            <Notice>Restore replaces the CoinBack schema only. Keep backups off the machine as well.</Notice>
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader title="Account" />
          <PanelBody className="space-y-2 text-sm text-muted">
            <p>CoinBack uses your SourcePoint administrator account.</p>
            <a className="inline-flex text-positive underline underline-offset-2" href="/profile" target="_blank" rel="noopener noreferrer">
              Manage your SourcePoint password
            </a>
          </PanelBody>
        </Panel>
      </div>
    </>
  );
}
