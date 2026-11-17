"use client";

import { useState } from "react";
import { AlertTriangle, Play, Settings2 } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { SourceLabel } from "@/components/offers/status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Switch, Textarea } from "@/components/ui/field";
import { KeyValue, Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { ErrorState, Notice, Skeleton } from "@/components/ui/states";
import { useApi, useApiMutation } from "@/hooks/use-api";
import { api } from "@/services/api";
import { formatDateTimeShort, formatRelative } from "@/services/format";
import type { AppSettings, DiscoverySource, Envelope } from "@/services/types";

const INVALIDATE = ["/discovery", "/dashboard"];

function EditSourceDialog({ source, onClose }: { source: DiscoverySource; onClose: () => void }) {
  const cfg = source.config as Record<string, unknown>;
  const isSearch = source.source_type === "PUBLIC_SEARCH";
  const isFeed = source.connector_key === "json_feed";
  const [form, setForm] = useState({
    rate_limit_per_minute: String(source.rate_limit_per_minute),
    phrases: ((cfg.phrases as string[]) ?? []).join("\n"),
    categories: ((cfg.categories as string[]) ?? []).join("\n"),
    max_queries_per_run: String(cfg.max_queries_per_run ?? 4),
    results_per_query: String(cfg.results_per_query ?? 10),
    feed_url: String(cfg.url ?? ""),
    api_key_env: String(cfg.api_key_env ?? ""),
    provider_name: String(cfg.provider_name ?? ""),
  });
  const save = useApiMutation((body: Record<string, unknown>) => api.patch(`/discovery/sources/${source.id}`, body), {
    invalidate: INVALIDATE,
    success: "Source updated",
    onSuccess: onClose,
  });
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const lines = (v: string) => v.split("\n").map((s) => s.trim()).filter(Boolean);

  const submit = () => {
    const body: Record<string, unknown> = { rate_limit_per_minute: Number(form.rate_limit_per_minute) };
    if (isSearch) {
      body.phrases = lines(form.phrases);
      body.categories = lines(form.categories);
      body.max_queries_per_run = Number(form.max_queries_per_run);
      body.results_per_query = Number(form.results_per_query);
    }
    if (isFeed) {
      body.feed_url = form.feed_url.trim() || null;
      body.api_key_env = form.api_key_env.trim() || null;
      body.provider_name = form.provider_name.trim() || null;
    }
    save.mutate(body);
  };

  return (
    <Dialog
      open
      onClose={onClose}
      width="lg"
      title={`Configure ${source.name}`}
      description="Only non-secret settings are stored here. Credentials are read from environment variables."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" loading={save.isPending} onClick={submit}>
            Save
          </Button>
        </>
      }
    >
      <div className="grid grid-cols-2 gap-3">
        <Field label="Rate limit (requests / minute)" htmlFor="s-rate">
          <Input id="s-rate" type="number" min={1} max={120} value={form.rate_limit_per_minute} onChange={set("rate_limit_per_minute")} />
        </Field>
        {isSearch ? (
          <>
            <Field label="Queries per scan" htmlFor="s-q" hint="Phrases rotate across scans to respect quota">
              <Input id="s-q" type="number" min={1} max={20} value={form.max_queries_per_run} onChange={set("max_queries_per_run")} />
            </Field>
            <Field label="Search phrases (one per line)" htmlFor="s-phrases" className="col-span-2">
              <Textarea id="s-phrases" rows={8} value={form.phrases} onChange={set("phrases")} />
            </Field>
            <Field label="Categories (optional, one per line)" htmlFor="s-cats" hint="Each phrase is combined with each category">
              <Textarea id="s-cats" rows={4} value={form.categories} onChange={set("categories")} />
            </Field>
            <Field label="Results per query" htmlFor="s-r">
              <Input id="s-r" type="number" min={1} max={20} value={form.results_per_query} onChange={set("results_per_query")} />
            </Field>
          </>
        ) : null}
        {isFeed ? (
          <>
            <Field label="Feed URL (https)" htmlFor="s-url" className="col-span-2" hint="Host must be listed in THIRD_PARTY_ALLOWED_HOSTS">
              <Input id="s-url" value={form.feed_url} maxLength={2048} onChange={set("feed_url")} />
            </Field>
            <Field label="API key environment variable" htmlFor="s-env" hint="Name only, e.g. THIRD_PARTY_FEED_API_KEY">
              <Input id="s-env" value={form.api_key_env} maxLength={64} onChange={set("api_key_env")} />
            </Field>
            <Field label="Provider name" htmlFor="s-prov">
              <Input id="s-prov" value={form.provider_name} maxLength={120} onChange={set("provider_name")} />
            </Field>
          </>
        ) : null}
      </div>
    </Dialog>
  );
}

function SourceCard({ source, env }: { source: DiscoverySource; env?: AppSettings["environment"] }) {
  const [editing, setEditing] = useState(false);
  const toggle = useApiMutation((enabled: boolean) => api.patch(`/discovery/sources/${source.id}`, { enabled }), { invalidate: INVALIDATE, success: "Source updated" });
  const run = useApiMutation(() => api.post("/discovery/run", { source_id: source.id }), { invalidate: INVALIDATE, success: "Run queued for this source" });

  const credentialState = (() => {
    if (!env) return null;
    if (source.connector_key === "google_cse") return env.google_cse_configured;
    if (source.connector_key === "brave_search") return env.brave_search_configured;
    if (source.connector_key === "flipkart_product_page") return env.product_page_fetch_enabled && env.product_page_permission_confirmed;
    return null;
  })();
  const backingOff = source.backoff_until && new Date(source.backoff_until).getTime() > Date.now();
  const health = !source.enabled ? { tone: "muted" as const, label: "Disabled" } : backingOff ? { tone: "warning" as const, label: "Backing off" } : source.last_error ? { tone: "negative" as const, label: "Error" } : source.last_success_at ? { tone: "positive" as const, label: "Healthy" } : { tone: "neutral" as const, label: "No runs yet" };

  return (
    <Panel>
      <PanelHeader
        title={
          <span className="flex items-center gap-2">
            {source.name}
            <Badge tone={health.tone} dot>
              {health.label}
            </Badge>
          </span>
        }
        description={<SourceLabel type={source.source_type} />}
        actions={
          <>
            {source.supports_discovery || source.supports_product_fetch ? (
              <Button size="sm" disabled={!source.enabled} loading={run.isPending} onClick={() => run.mutate(undefined)}>
                <Play className="h-3.5 w-3.5" />
                Run
              </Button>
            ) : null}
            <Button size="sm" onClick={() => setEditing(true)}>
              <Settings2 className="h-3.5 w-3.5" />
              Configure
            </Button>
            <Switch checked={source.enabled} onChange={(v) => toggle.mutate(v)} label={`Enable ${source.name}`} disabled={toggle.isPending} />
          </>
        }
      />
      <PanelBody className="space-y-2 pt-1">
        <KeyValue
          items={[
            { label: "Connector", value: <span className="font-mono text-xs">{source.connector_key}</span> },
            { label: "Authentication", value: source.auth_method === "none" ? "None" : "Environment variable" },
            ...(credentialState === null ? [] : [{ label: "Environment", value: credentialState ? <Badge tone="positive">Ready</Badge> : <Badge tone="warning">Not configured</Badge> }]),
            { label: "Rate limit", value: `${source.rate_limit_per_minute} / min` },
            { label: "Last success", value: source.last_success_at ? `${formatRelative(source.last_success_at)} (${formatDateTimeShort(source.last_success_at)})` : "Never" },
            { label: "Consecutive failures", value: source.consecutive_failures },
            ...(backingOff ? [{ label: "Backoff until", value: formatDateTimeShort(source.backoff_until) }] : []),
          ]}
        />
        {source.last_error ? (
          <p className="flex items-start gap-1.5 rounded border border-negative/25 bg-negative-soft px-2 py-1.5 text-xs text-negative">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              {source.last_error}
              {source.last_error_at ? <span className="ml-1 text-faint">({formatRelative(source.last_error_at)})</span> : null}
            </span>
          </p>
        ) : null}
        {source.permitted_use_notes ? <p className="text-2xs leading-4 text-faint">{source.permitted_use_notes}</p> : null}
      </PanelBody>
      {editing ? <EditSourceDialog source={source} onClose={() => setEditing(false)} /> : null}
    </Panel>
  );
}

export default function SourcesPage() {
  const sources = useApi<Envelope<DiscoverySource[]>>("/discovery/sources", undefined, { refetchInterval: 30_000 });
  const settings = useApi<Envelope<AppSettings>>("/settings");
  const list = sources.data?.data ?? [];
  const automated = list.filter((s) => s.enabled && s.source_type !== "USER_SUBMITTED");

  return (
    <>
      <PageHeader
        title="Discovery Sources"
        description="Provider-independent connectors. Only official APIs, authorized feeds and operator-permitted product-page access are used. CAPTCHA, login and anti-bot controls are never bypassed."
      />
      {sources.isSuccess && automated.length === 0 ? (
        <Notice tone="warning" title="Coverage limited to submitted URLs" className="mb-3">
          No automated discovery source is enabled. CoinBack Finder still works with product URLs you submit and offers you record manually.
          Enable a search API with credentials, an authorized provider feed, or product-page access once you have confirmed it is permitted.
        </Notice>
      ) : null}
      {sources.isLoading ? (
        <div className="grid gap-3 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-60" />
          ))}
        </div>
      ) : sources.error ? (
        <ErrorState message={sources.error.message} onRetry={() => sources.refetch()} />
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {list.map((s) => (
            <SourceCard key={s.id} source={s} env={settings.data?.data.environment} />
          ))}
        </div>
      )}
    </>
  );
}
