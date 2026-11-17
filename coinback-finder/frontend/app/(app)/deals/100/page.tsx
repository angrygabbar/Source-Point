"use client";

import { useMemo } from "react";

import { FilterSelect, NumberFilter } from "@/components/offers/filters";
import { OFFER_FILTER_DEFAULTS, OffersTable, toParams } from "@/components/offers/offers-table";
import { PageHeader } from "@/components/layout/page-header";
import { Segmented } from "@/components/ui/segmented";
import { Notice } from "@/components/ui/states";
import { useApi } from "@/hooks/use-api";
import { useUrlState } from "@/hooks/use-url-state";
import type { Envelope, Facets, Offer, Paged } from "@/services/types";

const DEFAULTS = { ...OFFER_FILTER_DEFAULTS, pct_mode: "gte_100", sort: "pct" };

function Count({ params }: { params: Record<string, string> }) {
  const { data } = useApi<Paged<Offer>>("/offers/100-percent", { ...params, page_size: 1, page: 1 });
  return <span className="num">{data ? data.meta.total.toLocaleString("en-IN") : "…"}</span>;
}

export default function HundredPercentPage() {
  const url = useUrlState(DEFAULTS);
  const { state, update } = url;
  const facets = useApi<Envelope<Facets>>("/products/facets");
  const base = useMemo(() => toParams({ ...state, page: "", sort: "", order: "" }) as Record<string, string>, [state]);

  return (
    <>
      <PageHeader
        title="100%+ CoinBack"
        description="Offers advertising a SuperCoin reward equal to or above the purchase value. Capped and 'up to' offers are labelled; neither is a guarantee."
        meta={
          <>
            <span>
              Exactly 100%: <Count params={{ ...base, pct_mode: "exact_100" }} />
            </span>
            <span className="text-faint">·</span>
            <span>
              Above 100%: <Count params={{ ...base, pct_mode: "above_100" }} />
            </span>
            <span className="text-faint">·</span>
            <span>
              Verified: <Count params={{ ...base, verified: "true" }} />
            </span>
          </>
        }
      />
      <Notice className="mb-3">
        A 100% CoinBack is advertised in SuperCoins, not rupees. The rupee value depends on how SuperCoins can be redeemed and on any cap. Confirm in your own account before purchase.
      </Notice>
      <OffersTable
        endpoint="/offers/100-percent"
        savedPage="deals-100"
        storageKey="deals-100"
        defaultSort="pct"
        {...url}
        filters={
          <>
            <Segmented
              label="Percentage"
              value={state.pct_mode as "gte_100" | "exact_100" | "above_100"}
              onChange={(pct_mode) => update({ pct_mode })}
              options={[
                { value: "gte_100", label: "≥ 100%" },
                { value: "exact_100", label: "Exactly 100%" },
                { value: "above_100", label: "Above 100%" },
              ]}
            />
            <Segmented
              label="Cap"
              value={(state.capped || "all") as "all" | "true" | "false"}
              onChange={(v) => update({ capped: v === "all" ? "" : v })}
              options={[
                { value: "all", label: "Any cap" },
                { value: "true", label: "Capped" },
                { value: "false", label: "No cap stated" },
              ]}
            />
            <Segmented
              label="Verification"
              value={(state.verified || "all") as "all" | "true" | "false"}
              onChange={(v) => update({ verified: v === "all" ? "" : v })}
              options={[
                { value: "all", label: "All" },
                { value: "true", label: "Verified" },
                { value: "false", label: "Unverified" },
              ]}
            />
            <Segmented
              label="Conditional"
              value={(state.up_to || "all") as "all" | "false" | "true"}
              onChange={(v) => update({ up_to: v === "all" ? "" : v })}
              options={[
                { value: "all", label: "Incl. 'up to'" },
                { value: "false", label: "Firm only" },
                { value: "true", label: "'Up to' only" },
              ]}
            />
            <NumberFilter label="Min coins" value={state.min_coins} onChange={(min_coins) => update({ min_coins })} />
            <NumberFilter label="Price ₹" value={state.min_price} onChange={(min_price) => update({ min_price })} placeholder="min" />
            <NumberFilter label="–" value={state.max_price} onChange={(max_price) => update({ max_price })} placeholder="max" />
            <FilterSelect
              label="Category"
              value={state.category}
              onChange={(category) => update({ category })}
              options={(facets.data?.data.categories ?? []).map((c) => ({ value: c.value, label: `${c.value} (${c.count})` }))}
            />
          </>
        }
        emptyHint="No active offers at 100% or above match these filters."
      />
    </>
  );
}
