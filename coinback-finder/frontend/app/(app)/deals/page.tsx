"use client";

import { FilterSelect, NumberFilter } from "@/components/offers/filters";
import { OFFER_FILTER_DEFAULTS, OffersTable } from "@/components/offers/offers-table";
import { PageHeader } from "@/components/layout/page-header";
import { Switch } from "@/components/ui/field";
import { useApi } from "@/hooks/use-api";
import { useUrlState } from "@/hooks/use-url-state";
import { OFFER_STATUS_LABEL, REWARD_TYPE_LABEL, SOURCE_TYPE_LABEL } from "@/services/format";
import type { Envelope, Facets, OfferStatus, RewardType, SourceType } from "@/services/types";

const statusOptions = [
  { value: "VERIFIED", label: "Verified" },
  { value: "DETECTED,UNVERIFIED,ACCOUNT_CHECK_REQUIRED", label: "Awaiting verification" },
  ...(["DETECTED", "UNVERIFIED", "ACCOUNT_CHECK_REQUIRED", "REJECTED", "EXPIRED", "SOURCE_UNAVAILABLE"] as OfferStatus[]).map((s) => ({
    value: s,
    label: OFFER_STATUS_LABEL[s],
  })),
];

export default function AllDealsPage() {
  const url = useUrlState(OFFER_FILTER_DEFAULTS);
  const { state, update } = url;
  const facets = useApi<Envelope<Facets>>("/products/facets");

  return (
    <>
      <PageHeader
        title="All Deals"
        description="Every detected SuperCoin / CoinBack offer. Search snippets are discovery evidence only; percentages are advertised, not guaranteed."
      />
      <OffersTable
        endpoint="/offers"
        savedPage="deals"
        storageKey="deals"
        {...url}
        filters={
          <>
            <FilterSelect label="Status" value={state.status} onChange={(status) => update({ status })} options={statusOptions} />
            <FilterSelect
              label="Type"
              value={state.reward_type}
              onChange={(reward_type) => update({ reward_type })}
              options={(["PERCENTAGE", "CONDITIONAL_UP_TO", "FIXED_COINS", "PER_SPEND_RATE"] as RewardType[]).map((r) => ({ value: r, label: REWARD_TYPE_LABEL[r] }))}
            />
            <FilterSelect
              label="Source"
              value={state.source_type}
              onChange={(source_type) => update({ source_type })}
              options={(["PRODUCT_PAGE", "THIRD_PARTY", "PUBLIC_SEARCH", "MANUAL"] as SourceType[]).map((s) => ({ value: s, label: SOURCE_TYPE_LABEL[s] }))}
            />
            <FilterSelect
              label="Category"
              value={state.category}
              onChange={(category) => update({ category })}
              options={(facets.data?.data.categories ?? []).map((c) => ({ value: c.value, label: `${c.value} (${c.count})` }))}
            />
            <FilterSelect
              label="Detected"
              value={state.detected}
              onChange={(detected) => update({ detected })}
              allLabel="Any time"
              options={[
                { value: "today", label: "Today" },
                { value: "7d", label: "Last 7 days" },
                { value: "30d", label: "Last 30 days" },
                { value: "90d", label: "Last 90 days" },
              ]}
            />
            <NumberFilter label="Min %" value={state.min_pct} onChange={(min_pct) => update({ min_pct })} width={64} />
            <NumberFilter label="Price ₹" value={state.min_price} onChange={(min_price) => update({ min_price })} placeholder="min" />
            <NumberFilter label="–" value={state.max_price} onChange={(max_price) => update({ max_price })} placeholder="max" />
            <label className="flex items-center gap-1.5 text-xs text-muted">
              <Switch checked={state.include_inactive === "true"} onChange={(v) => update({ include_inactive: v ? "true" : "" })} label="Include expired and rejected" />
              Include expired / rejected
            </label>
          </>
        }
        emptyHint="Adjust filters, or add product URLs and enable a permitted discovery source to collect offers."
      />
    </>
  );
}
