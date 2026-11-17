"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Send } from "lucide-react";

import { DataTable, type Column } from "@/components/data-table/data-table";
import { PageHeader } from "@/components/layout/page-header";
import { FilterGroup, FilterSelect } from "@/components/offers/filters";
import { toParams } from "@/components/offers/offers-table";
import { NotificationStatusBadge } from "@/components/offers/status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, Switch } from "@/components/ui/field";
import { KeyValue, Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { Pagination } from "@/components/ui/pagination";
import { EmptyState, Notice, Skeleton } from "@/components/ui/states";
import { useApi, useApiMutation } from "@/hooks/use-api";
import { useUrlState } from "@/hooks/use-url-state";
import { api } from "@/services/api";
import { formatDateTimeShort, NOTIFICATION_STATUS_LABEL } from "@/services/format";
import type { Envelope, NotificationItem, NotificationPreferences, NotificationStatus, Paged } from "@/services/types";

type PrefForm = Omit<NotificationPreferences, "updated_at" | "telegram">;

function PreferencesPanel() {
  const q = useApi<Envelope<NotificationPreferences>>("/notifications/preferences");
  const [form, setForm] = useState<PrefForm | null>(null);
  useEffect(() => {
    if (q.data) {
      const { updated_at: _u, telegram: _t, ...rest } = q.data.data;
      setForm(rest);
    }
  }, [q.data]);
  const save = useApiMutation((body: PrefForm) => api.put("/notifications/preferences", body), { invalidate: ["/notifications"], success: "Preferences saved" });
  const test = useApiMutation(() => api.post("/notifications/test"), { invalidate: ["/notifications"], success: "Test notification queued" });

  if (!form || !q.data) return <Skeleton className="h-80" />;
  const t = q.data.data.telegram;
  const set = <K extends keyof PrefForm>(k: K, v: PrefForm[K]) => setForm((f) => (f ? { ...f, [k]: v } : f));
  const toggles: { key: keyof PrefForm; label: string; hint: string }[] = [
    { key: "enabled", label: "Telegram alerts enabled", hint: "Master switch for offer alerts" },
    { key: "paused", label: "Paused", hint: "Same as /pause and /resume in Telegram" },
    { key: "verified_only", label: "Verified offers only", hint: "Only alert after manual verification" },
    { key: "include_unverified", label: "Include unverified offers", hint: "Alerts carry an explicit unverified warning" },
    { key: "notify_new", label: "New offers", hint: "First detection of a qualifying offer" },
    { key: "notify_changes", label: "Reward changes", hint: "Advertised reward or cap changed" },
    { key: "notify_expiring", label: "Expiring within 24 h", hint: "Only offers with a stated expiry" },
  ];

  return (
    <div className="space-y-3">
      <Panel>
        <PanelHeader
          title="Telegram channel"
          actions={
            <Button size="sm" loading={test.isPending} onClick={() => test.mutate(undefined)}>
              <Send className="h-3.5 w-3.5" />
              Send test
            </Button>
          }
        />
        <PanelBody className="pt-1">
          <KeyValue
            items={[
              { label: "Bot token & chat ID", value: t.configured ? <Badge tone="positive">Configured</Badge> : <Badge tone="warning">Not configured</Badge> },
              { label: "Delivery mode", value: t.dry_run ? <Badge tone="neutral">Dry run – no messages sent</Badge> : <Badge tone="positive">Live</Badge> },
              { label: "Bot commands", value: t.commands_enabled ? "Enabled" : "Disabled" },
              { label: "Chat", value: t.chat_id_hint ?? "Not set" },
            ]}
          />
          {t.dry_run ? (
            <Notice className="mt-2">
              Messages are recorded with status “Dry run”. Set TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID and TELEGRAM_DRY_RUN=false in the environment to deliver.
            </Notice>
          ) : null}
        </PanelBody>
      </Panel>
      <Panel>
        <PanelHeader title="Alert rules" description={`Last saved ${formatDateTimeShort(q.data.data.updated_at)}`} />
        <PanelBody className="space-y-3">
          <label className="flex items-center justify-between gap-3">
            <span>
              <span className="block text-sm">Minimum advertised CoinBack</span>
              <span className="block text-2xs text-faint">Offers without a calculated % are excluded when a minimum is set</span>
            </span>
            <Select compact className="w-36" value={form.min_percentage === null ? "" : String(form.min_percentage)} onChange={(e) => set("min_percentage", e.target.value === "" ? null : Number(e.target.value))}>
              <option value="">All CoinBack offers</option>
              {[10, 25, 50, 75, 100].map((v) => (
                <option key={v} value={v}>
                  {v}% and above
                </option>
              ))}
            </Select>
          </label>
          <div className="divide-y divide-line rounded border border-line">
            {toggles.map((tg) => (
              <label key={tg.key} className="flex items-center justify-between gap-3 px-3 py-2">
                <span>
                  <span className="block text-sm">{tg.label}</span>
                  <span className="block text-2xs text-faint">{tg.hint}</span>
                </span>
                <Switch checked={Boolean(form[tg.key])} onChange={(v) => set(tg.key, v as never)} label={tg.label} />
              </label>
            ))}
          </div>
          <div className="flex justify-end">
            <Button variant="primary" size="sm" loading={save.isPending} onClick={() => save.mutate(form)}>
              Save preferences
            </Button>
          </div>
        </PanelBody>
      </Panel>
    </div>
  );
}

export default function NotificationsPage() {
  const { state, update } = useUrlState({ status: "", event_type: "", page: "1", page_size: "50" });
  const params = useMemo(() => toParams(state), [state]);
  const q = useApi<Paged<NotificationItem>>("/notifications", params, { keepPrevious: true, refetchInterval: 30_000 });
  const [open, setOpen] = useState<string | null>(null);

  const columns: Column<NotificationItem>[] = [
    {
      id: "expand",
      header: "",
      width: "28px",
      cell: (n) => (open === n.id ? <ChevronDown className="h-3.5 w-3.5 text-faint" /> : <ChevronRight className="h-3.5 w-3.5 text-faint" />),
    },
    { id: "created", header: "Queued", cell: (n) => <span className="num text-xs text-muted">{formatDateTimeShort(n.created_at)}</span> },
    { id: "event", header: "Event", cell: (n) => <span className="text-xs">{n.event_type.replace(/_/g, " ").toLowerCase()}</span> },
    { id: "product", header: "Product", cell: (n) => <span className="block max-w-[320px] truncate">{n.product_title ?? "—"}</span> },
    { id: "status", header: "Status", cell: (n) => <NotificationStatusBadge status={n.status} /> },
    { id: "retries", header: "Retries", align: "right", cell: (n) => <span className="num">{n.retry_count}</span> },
    { id: "sent", header: "Sent", cell: (n) => <span className="num text-xs text-muted">{formatDateTimeShort(n.sent_at) ?? "—"}</span> },
    { id: "error", header: "Last error", cell: (n) => <span className="block max-w-[240px] truncate text-xs text-negative" title={n.last_error ?? undefined}>{n.last_error ?? ""}</span> },
  ];

  const openItem = q.data?.data.find((n) => n.id === open);
  return (
    <>
      <PageHeader title="Notifications" description="Telegram alert rules and delivery history. Each event is sent at most once (de-duplicated by event key) with automatic retries." />
      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_380px]">
        <Panel className="min-w-0">
          <div className="border-b border-line px-3 py-2.5">
            <FilterGroup>
              <FilterSelect
                label="Status"
                value={state.status}
                onChange={(status) => update({ status })}
                options={(["PENDING", "SENT", "DRY_RUN", "FAILED", "SUPPRESSED"] as NotificationStatus[]).map((s) => ({ value: s, label: NOTIFICATION_STATUS_LABEL[s] }))}
              />
              <FilterSelect
                label="Event"
                value={state.event_type}
                onChange={(event_type) => update({ event_type })}
                options={[
                  { value: "NEW_OFFER", label: "New offer" },
                  { value: "OFFER_CHANGED", label: "Offer changed" },
                  { value: "OFFER_EXPIRING", label: "Offer expiring" },
                  { value: "TEST", label: "Test" },
                ]}
              />
            </FilterGroup>
          </div>
          <DataTable
            columns={columns}
            rows={q.data?.data}
            rowKey={(n) => n.id}
            loading={q.isLoading}
            error={q.error?.message}
            onRetry={() => q.refetch()}
            onRowClick={(n) => setOpen((cur) => (cur === n.id ? null : n.id))}
            rowClassName={(n) => (n.id === open ? "bg-subtle" : undefined)}
            empty={<EmptyState title="No notifications yet" description="Notifications are queued when qualifying offers are detected." />}
            footer={
              <>
                {openItem ? (
                  <div className="border-t border-line bg-subtle/50 px-3 py-2.5">
                    <p className="eyebrow mb-1">Message preview (Telegram HTML)</p>
                    <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded border border-line bg-surface p-2.5 font-mono text-[11px] leading-5 text-muted">{openItem.message}</pre>
                  </div>
                ) : null}
                <Pagination meta={q.data?.meta} onPage={(p) => update({ page: String(p) })} onPageSize={(s) => update({ page_size: String(s) })} />
              </>
            }
          />
        </Panel>
        <PreferencesPanel />
      </div>
    </>
  );
}
