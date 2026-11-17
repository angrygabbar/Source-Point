import { Badge, type Tone } from "@/components/ui/badge";
import {
  NOTIFICATION_STATUS_LABEL,
  OFFER_STATUS_LABEL,
  SCAN_STATUS_LABEL,
  SOURCE_TYPE_LABEL,
} from "@/services/format";
import type { AccessStatus, NotificationStatus, OfferStatus, ScanStatus, SourceType } from "@/services/types";
import { cn } from "@/services/cn";

const OFFER_TONE: Record<OfferStatus, Tone> = {
  DETECTED: "muted",
  UNVERIFIED: "neutral",
  ACCOUNT_CHECK_REQUIRED: "warning",
  VERIFIED: "positive",
  REJECTED: "negative",
  EXPIRED: "muted",
  SOURCE_UNAVAILABLE: "negative",
};
const OFFER_HINT: Record<OfferStatus, string> = {
  DETECTED: "Seen in discovery evidence only (e.g. search snippet). Not proof of the offer.",
  UNVERIFIED: "Detected on a primary source; not confirmed in your account.",
  ACCOUNT_CHECK_REQUIRED: "Conditional or restricted offer. Confirm eligibility in your own account.",
  VERIFIED: "Confirmed by manual verification.",
  REJECTED: "Rejected during manual review.",
  EXPIRED: "Validity ended or no longer displayed.",
  SOURCE_UNAVAILABLE: "Source could not be accessed repeatedly.",
};

export function OfferStatusBadge({ status }: { status: OfferStatus }) {
  return (
    <Badge tone={OFFER_TONE[status]} dot title={OFFER_HINT[status]}>
      {OFFER_STATUS_LABEL[status]}
    </Badge>
  );
}

const SCAN_TONE: Record<ScanStatus, Tone> = {
  QUEUED: "accent",
  RUNNING: "accent",
  SUCCEEDED: "positive",
  PARTIAL: "warning",
  FAILED: "negative",
  SKIPPED: "muted",
  INTERRUPTED: "warning",
};
export function ScanStatusBadge({ status }: { status: ScanStatus }) {
  return (
    <Badge tone={SCAN_TONE[status]} dot>
      {SCAN_STATUS_LABEL[status]}
    </Badge>
  );
}

const NOTIF_TONE: Record<NotificationStatus, Tone> = {
  PENDING: "accent",
  SENT: "positive",
  FAILED: "negative",
  SUPPRESSED: "muted",
  DRY_RUN: "neutral",
};
export function NotificationStatusBadge({ status }: { status: NotificationStatus }) {
  return (
    <Badge tone={NOTIF_TONE[status]} dot>
      {NOTIFICATION_STATUS_LABEL[status]}
    </Badge>
  );
}

const ACCESS: Record<AccessStatus, { tone: Tone; label: string }> = {
  PENDING: { tone: "muted", label: "Pending" },
  OK: { tone: "positive", label: "Accessible" },
  UNAVAILABLE: { tone: "warning", label: "Unavailable" },
  BLOCKED: { tone: "negative", label: "Access refused" },
  NOT_PERMITTED: { tone: "muted", label: "Manual only" },
};
export function AccessBadge({ status, title }: { status: AccessStatus; title?: string | null }) {
  const a = ACCESS[status] ?? ACCESS.PENDING;
  return (
    <Badge tone={a.tone} title={title ?? undefined}>
      {a.label}
    </Badge>
  );
}

export function SourceLabel({ type, className }: { type: SourceType; className?: string }) {
  return <span className={cn("text-xs text-muted", className)}>{SOURCE_TYPE_LABEL[type] ?? type}</span>;
}

export function Confidence({ value }: { value: number | null }) {
  if (value === null || value === undefined) return <span className="text-xs text-faint">Not available</span>;
  const pct = Math.round(value * 100);
  const tone = pct >= 70 ? "bg-positive" : pct >= 45 ? "bg-warning" : "bg-negative/80";
  return (
    <span className="inline-flex items-center gap-1.5" title="Classifier confidence in the detected wording. Not proof of eligibility.">
      <span className="h-1 w-10 overflow-hidden rounded-full bg-subtle">
        <span className={cn("block h-full", tone)} style={{ width: `${pct}%` }} />
      </span>
      <span className="num text-xs text-muted">{pct}%</span>
    </span>
  );
}
