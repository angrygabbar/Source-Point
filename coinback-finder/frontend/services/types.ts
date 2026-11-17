export type OfferStatus =
  | "DETECTED"
  | "UNVERIFIED"
  | "ACCOUNT_CHECK_REQUIRED"
  | "VERIFIED"
  | "REJECTED"
  | "EXPIRED"
  | "SOURCE_UNAVAILABLE";
export type RewardType = "PERCENTAGE" | "FIXED_COINS" | "PER_SPEND_RATE" | "CONDITIONAL_UP_TO" | "NOT_COINBACK";
export type SourceType = "PUBLIC_SEARCH" | "USER_SUBMITTED" | "THIRD_PARTY" | "PRODUCT_PAGE" | "MANUAL";
export type AccessStatus = "PENDING" | "OK" | "UNAVAILABLE" | "BLOCKED" | "NOT_PERMITTED";
export type ScanStatus = "QUEUED" | "RUNNING" | "SUCCEEDED" | "PARTIAL" | "FAILED" | "SKIPPED" | "INTERRUPTED";
export type NotificationStatus = "PENDING" | "SENT" | "FAILED" | "SUPPRESSED" | "DRY_RUN";

export interface Envelope<T> {
  data: T;
}
export interface PageMeta {
  page: number;
  page_size: number;
  total: number;
  pages: number;
}
export interface Paged<T> {
  data: T[];
  meta: PageMeta;
}

export interface OfferBrief {
  id: string;
  title: string;
  reward_type: RewardType;
  is_up_to: boolean;
  advertised_coins: number | null;
  advertised_percentage: number | null;
  estimated_coins: number | null;
  reward_cap_coins: number | null;
  per_spend_coins: number | null;
  per_spend_amount: number | null;
  status: OfferStatus;
  confidence: number | null;
  source_type: SourceType;
  valid_until: string | null;
  last_seen_at: string;
}

export interface ProductMini {
  id: string;
  title: string | null;
  brand: string | null;
  category: string | null;
  image_url: string | null;
  current_price: number | null;
  mrp: number | null;
  discount_percent: number | null;
  seller: string | null;
  product_url: string;
  flipkart_pid: string | null;
  in_stock: boolean | null;
  access_status: AccessStatus;
}

export interface ProductRow extends ProductMini {
  shipping_charge: number | null;
  variant: string | null;
  original_url: string | null;
  last_access_error: string | null;
  first_seen_at: string;
  last_seen_at: string | null;
  last_checked_at: string | null;
  archived_at: string | null;
  source_name: string | null;
  is_monitored: boolean;
  best_offer: OfferBrief | null;
}

export interface Offer extends OfferBrief {
  product_id: string;
  description: string | null;
  min_eligible_purchase: number | null;
  max_eligible_purchase: number | null;
  eligible_purchase_amount: number | null;
  estimated_redemption_value: number | null;
  actual_redemption_value: number | null;
  effective_cost_estimate: number | null;
  classification_reason: string | null;
  restrictions: Record<string, string[]>;
  terms: string | null;
  valid_from: string | null;
  source_url: string | null;
  source_name: string | null;
  evidence_excerpt: string | null;
  first_detected_at: string;
  last_changed_at: string | null;
  verified_at: string | null;
  expired_at: string | null;
  product?: ProductMini;
}

export interface OfferSnapshot {
  id: string;
  offer_id: string;
  reward_coins: number | null;
  estimated_coins: number | null;
  percentage: number | null;
  cap: number | null;
  selling_price: number | null;
  status: OfferStatus;
  confidence: number | null;
  change_type: string;
  evidence: Record<string, unknown>;
  captured_at: string;
}

export interface PricePoint {
  captured_at: string;
  selling_price: number | null;
  mrp: number | null;
  shipping_charge: number | null;
  seller: string | null;
  in_stock: boolean | null;
  source_type: SourceType;
}

export interface Verification {
  id: string;
  offer_id: string;
  status: "VERIFIED" | "REJECTED" | "ACCOUNT_CHECK_REQUIRED";
  advertised_reward_coins: number | null;
  advertised_percentage: number | null;
  actual_reward_coins: number | null;
  actual_percentage: number | null;
  eligible_purchase_amount: number | null;
  reward_cap_coins: number | null;
  actual_redemption_value: number | null;
  restrictions: string | null;
  expiry: string | null;
  eligibility_notes: string | null;
  notes: string | null;
  verified_by: string | null;
  verified_at: string;
}

export interface ProductDetail {
  product: ProductRow;
  offers: Offer[];
  price_stats: {
    lowest: number | null;
    highest: number | null;
    average: number | null;
    observations: number;
    first_recorded: string | null;
    last_recorded: string | null;
  };
  sellers: { seller: string; first_seen: string; last_seen: string; observations: number }[];
  verifications: Verification[];
  monitoring: { enabled: boolean; frequency_minutes: number | null; last_processed_at: string | null; next_due_at: string | null };
  watchlist: { saved: boolean; note: string | null; target_price: number | null; target_percentage: number | null };
  assumptions: { supercoin_value_inr: number | null };
}

export interface IntelligenceRow extends ProductRow {
  price_stats: {
    lowest_price?: number | null;
    highest_price?: number | null;
    average_price?: number | null;
    observations?: number;
    distinct_sellers?: number;
    price_7d_ago?: number | null;
    change_7d_pct: number | null;
  };
  offer_count: number;
}

export interface CompareRow extends ProductRow {
  historical_low: number | null;
  best_offer_detail: Offer | null;
}

export interface Facets {
  categories: { value: string; count: number }[];
  brands: { value: string; count: number }[];
  sellers: { value: string; count: number }[];
  price_range: { min: number | null; max: number | null };
}

export interface DiscoverySource {
  id: string;
  name: string;
  source_type: SourceType;
  connector_key: string;
  enabled: boolean;
  config: Record<string, unknown>;
  auth_method: string;
  rate_limit_per_minute: number;
  permitted_use_notes: string | null;
  last_success_at: string | null;
  last_error: string | null;
  last_error_at: string | null;
  consecutive_failures: number;
  backoff_until: string | null;
  supports_discovery: boolean;
  supports_product_fetch: boolean;
  offers_in_range?: number;
}

export interface ScanLogEntry {
  ts: string;
  level: "info" | "warning" | "error" | "debug";
  source: string | null;
  message: string;
}

export interface ScanRun {
  id: string;
  trigger: "SCHEDULED" | "MANUAL";
  status: ScanStatus;
  source_id: string | null;
  queued_at: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  products_discovered: number;
  products_processed: number;
  offers_detected: number;
  offers_new: number;
  offers_expired: number;
  notifications_queued: number;
  errors_count: number;
  progress: { phase?: string; done?: number; total?: number; updated_at?: string };
  details?: {
    log?: ScanLogEntry[];
    sources?: Record<string, unknown>[];
    summary?: Record<string, number>;
    recovery?: string;
  };
  already_queued?: boolean;
}

export interface NotificationItem {
  id: string;
  product_id: string | null;
  offer_id: string | null;
  product_title: string | null;
  channel: string;
  chat_id: string | null;
  event_type: "NEW_OFFER" | "OFFER_CHANGED" | "OFFER_EXPIRING" | "TEST";
  message: string;
  status: NotificationStatus;
  retry_count: number;
  next_attempt_at: string | null;
  last_error: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface NotificationPreferences {
  enabled: boolean;
  paused: boolean;
  min_percentage: number | null;
  verified_only: boolean;
  include_unverified: boolean;
  notify_new: boolean;
  notify_changes: boolean;
  notify_expiring: boolean;
  updated_at: string;
  telegram: { configured: boolean; dry_run: boolean; commands_enabled: boolean; chat_id_hint: string | null };
}

export interface DashboardSummary {
  total_products: number;
  active_offers: number;
  offers_100_plus: number;
  verified_offers: number;
  awaiting_verification: number;
  monitored_products: number;
  today_discoveries: number;
  yesterday_discoveries: number;
  today_new_products: number;
  scanner_success_rate: number | null;
  scanner_runs_7d: number;
  scanner_runs_by_status_7d: Record<string, number>;
  generated_at: string;
}

export interface DashboardPanels {
  latest_deals: Offer[];
  highest_rewards: Offer[];
  recently_changed: Offer[];
  expiring: Offer[];
  scanner_activity: ScanRun[];
  recent_notifications: NotificationItem[];
}

export interface Analytics {
  range: { start: string; end: string };
  coinback_distribution: { bucket: string; count: number }[];
  reward_distribution: { bucket: string; count: number }[];
  expiry_distribution: { bucket: string; count: number }[];
  discovery_trend: { date: string; offers: number; products: number; avg_pct: number | null; max_pct: number | null }[];
  price_movement: { date: string; drops: number; rises: number }[];
  category_distribution: { category: string; offers: number; avg_pct: number | null }[];
  status_breakdown: { status: OfferStatus; count: number }[];
  detection_by_hour: { hour: number; count: number }[];
  detection_by_weekday: { weekday: number; count: number }[];
  source_performance: DiscoverySource[];
  scan_performance: {
    date: string;
    runs: number;
    failed: number;
    avg_duration_ms: number | null;
    products_processed: number;
    offers_detected: number;
  }[];
  highest_rewards: Offer[];
}

export interface ScannerStatus {
  state: "running" | "idle" | "offline";
  alive: boolean;
  alive_at: string | null;
  next_scan_at: string | null;
  interval_minutes: number | null;
  scanner_enabled: boolean | null;
  telegram_mode: "dry-run" | "live" | null;
  heartbeat: Record<string, unknown>;
  current_run: ScanRun | null;
  last_run: ScanRun | null;
  last_success_at: string | null;
  queued_runs: number;
  runs_30d: number;
  failed_30d: number;
  avg_duration_ms_30d: number | null;
  products_processed_24h: number;
  offers_detected_24h: number;
  sources: DiscoverySource[];
}

export interface WatchlistItem {
  id: string;
  note: string | null;
  target_price: number | null;
  target_percentage: number | null;
  created_at: string;
  target_price_met: boolean;
  target_percentage_met: boolean;
  product: ProductRow;
  best_offer: OfferBrief | null;
}

export interface PriceMovement {
  product_id: string;
  title: string | null;
  brand: string | null;
  category: string | null;
  image_url: string | null;
  captured_at: string;
  previous_price: number;
  new_price: number;
  change: number;
  change_pct: number | null;
  seller: string | null;
  seller_changed: boolean;
}

export interface AppSettings {
  scan_interval_minutes: number;
  supercoin_value_inr: number | null;
  retention_days_scan_runs: number;
  retention_days_notifications: number;
  price_snapshot_min_interval_minutes: number;
  default_theme: "light" | "dark";
  monitor_new_submissions: boolean;
  display_timezone: string;
  currency: string;
  environment: {
    product_page_fetch_enabled: boolean;
    product_page_permission_confirmed: boolean;
    google_cse_configured: boolean;
    brave_search_configured: boolean;
    telegram_configured: boolean;
    telegram_dry_run: boolean;
    telegram_commands_enabled: boolean;
    flipkart_allowed_hosts: string[];
    third_party_allowed_hosts: string[];
    cookie_secure: boolean;
  };
}

export interface SavedFilter {
  id: string;
  name: string;
  page: string;
  params: Record<string, string>;
  created_at: string;
}

export interface SearchResult {
  products: {
    id: string;
    title: string | null;
    brand: string | null;
    category: string | null;
    current_price: number | null;
    image_url: string | null;
  }[];
  categories: { value: string; count: number }[];
}

export interface CurrentUser {
  id: string;
  username: string;
  last_login_at: string | null;
}
