import type { NotificationStatus, OfferStatus, RewardType, ScanStatus, SourceType } from "./types";

const TZ = "Asia/Kolkata";

const inr0 = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const inr2 = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2, maximumFractionDigits: 2 });
const int = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const compact = new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 });

export const isNil = (v: unknown): v is null | undefined => v === null || v === undefined;

export function formatINR(value: number | null | undefined, precise = false): string | null {
  if (isNil(value)) return null;
  return (precise || !Number.isInteger(value) ? inr2 : inr0).format(value);
}

export function formatNumber(value: number | null | undefined): string | null {
  return isNil(value) ? null : int.format(value);
}

export function formatCompact(value: number | null | undefined): string | null {
  return isNil(value) ? null : compact.format(value);
}

export function formatPct(value: number | null | undefined, digits = 2): string | null {
  if (isNil(value)) return null;
  const fixed = Number(value.toFixed(digits));
  return `${fixed.toLocaleString("en-IN", { maximumFractionDigits: digits })}%`;
}

const dtFull = new Intl.DateTimeFormat("en-IN", { timeZone: TZ, day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: true });
const dtShort = new Intl.DateTimeFormat("en-IN", { timeZone: TZ, day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: true });
const dOnly = new Intl.DateTimeFormat("en-IN", { timeZone: TZ, day: "2-digit", month: "short", year: "numeric" });
const tOnly = new Intl.DateTimeFormat("en-IN", { timeZone: TZ, hour: "2-digit", minute: "2-digit", hour12: true });
const dAxis = new Intl.DateTimeFormat("en-IN", { timeZone: TZ, day: "2-digit", month: "short" });

export const formatDateTime = (iso?: string | null) => (iso ? dtFull.format(new Date(iso)) : null);
export const formatDateTimeShort = (iso?: string | null) => (iso ? dtShort.format(new Date(iso)) : null);
export const formatDate = (iso?: string | null) => (iso ? dOnly.format(new Date(iso)) : null);
export const formatTime = (iso?: string | null) => (iso ? tOnly.format(new Date(iso)) : null);
export const formatAxisDate = (isoDate: string) => dAxis.format(new Date(`${isoDate}T00:00:00+05:30`));

export function formatRelative(iso?: string | null, now = Date.now()): string | null {
  if (!iso) return null;
  const diff = new Date(iso).getTime() - now;
  const abs = Math.abs(diff);
  const units: [number, Intl.RelativeTimeFormatUnit][] = [
    [60_000, "second"],
    [3_600_000, "minute"],
    [86_400_000, "hour"],
    [Infinity, "day"],
  ];
  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  const divisors: Record<string, number> = { second: 1000, minute: 60_000, hour: 3_600_000, day: 86_400_000 };
  for (const [limit, unit] of units) {
    if (abs < limit) return rtf.format(Math.round(diff / divisors[unit]), unit);
  }
  return null;
}

export function formatDuration(ms?: number | null): string | null {
  if (isNil(ms)) return null;
  if (ms < 1000) return `${ms} ms`;
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s`;
}

export const OFFER_STATUS_LABEL: Record<OfferStatus, string> = {
  DETECTED: "Detected",
  UNVERIFIED: "Unverified",
  ACCOUNT_CHECK_REQUIRED: "Account check",
  VERIFIED: "Verified",
  REJECTED: "Rejected",
  EXPIRED: "Expired",
  SOURCE_UNAVAILABLE: "Source unavailable",
};

export const REWARD_TYPE_LABEL: Record<RewardType, string> = {
  PERCENTAGE: "Percentage",
  FIXED_COINS: "Fixed coins",
  PER_SPEND_RATE: "Per-spend rate",
  CONDITIONAL_UP_TO: "Up to (conditional)",
  NOT_COINBACK: "Not CoinBack",
};

export const SOURCE_TYPE_LABEL: Record<SourceType, string> = {
  PUBLIC_SEARCH: "Search snippet",
  USER_SUBMITTED: "User submitted",
  THIRD_PARTY: "Provider feed",
  PRODUCT_PAGE: "Product page",
  MANUAL: "Manual entry",
};

export const SCAN_STATUS_LABEL: Record<ScanStatus, string> = {
  QUEUED: "Queued",
  RUNNING: "Running",
  SUCCEEDED: "Succeeded",
  PARTIAL: "Partial",
  FAILED: "Failed",
  SKIPPED: "Skipped",
  INTERRUPTED: "Interrupted",
};

export const NOTIFICATION_STATUS_LABEL: Record<NotificationStatus, string> = {
  PENDING: "Pending",
  SENT: "Sent",
  FAILED: "Failed",
  SUPPRESSED: "Suppressed",
  DRY_RUN: "Dry run",
};

export const WEEKDAY_LABEL = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
