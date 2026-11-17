"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { Notice } from "@/components/ui/states";
import { useApiMutation } from "@/hooks/use-api";
import { api } from "@/services/api";
import { formatINR, formatNumber, formatPct } from "@/services/format";
import type { Offer, ProductMini } from "@/services/types";

const num = (v: string) => (v.trim() === "" ? null : Number(v));
const INVALIDATE = ["/offers", "/products", "/dashboard", "/watchlist"];

export function VerifyDialog({
  offer,
  product,
  mode,
  onClose,
}: {
  offer: Offer | null;
  product?: ProductMini | null;
  mode: "verify" | "reject";
  onClose: () => void;
}) {
  const [form, setForm] = useState({
    status: "VERIFIED",
    actual_reward_coins: "",
    eligible_purchase_amount: "",
    reward_cap_coins: "",
    actual_redemption_value: "",
    restrictions: "",
    expiry: "",
    eligibility_notes: "",
    notes: "",
    observed_at: "",
  });
  useEffect(() => {
    if (offer) {
      setForm((f) => ({
        ...f,
        eligible_purchase_amount: offer.eligible_purchase_amount?.toString() ?? product?.current_price?.toString() ?? "",
        reward_cap_coins: offer.reward_cap_coins?.toString() ?? "",
      }));
    }
  }, [offer, product]);

  const verify = useApiMutation((body: Record<string, unknown>) => api.post(`/offers/${offer?.id}/verify`, body), {
    invalidate: INVALIDATE,
    success: "Verification recorded",
    onSuccess: onClose,
  });
  const reject = useApiMutation((body: Record<string, unknown>) => api.post(`/offers/${offer?.id}/reject`, body), {
    invalidate: INVALIDATE,
    success: "Offer rejected",
    onSuccess: onClose,
  });

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const coins = num(form.actual_reward_coins);
  const amount = num(form.eligible_purchase_amount);
  const actualPct = coins !== null && amount ? (coins / amount) * 100 : null;

  const submit = () => {
    if (mode === "reject") {
      reject.mutate({ notes: form.notes || null });
      return;
    }
    verify.mutate({
      status: form.status,
      actual_reward_coins: coins,
      eligible_purchase_amount: amount,
      reward_cap_coins: num(form.reward_cap_coins),
      actual_redemption_value: num(form.actual_redemption_value),
      restrictions: form.restrictions || null,
      expiry: form.expiry ? `${form.expiry}T23:59:59+05:30` : null,
      eligibility_notes: form.eligibility_notes || null,
      notes: form.notes || null,
      observed_at: form.observed_at ? `${form.observed_at}:00+05:30` : null,
    });
  };

  const title = product?.title ?? offer?.product?.title ?? "Product";
  return (
    <Dialog
      open={Boolean(offer)}
      onClose={onClose}
      width="lg"
      title={mode === "verify" ? "Record manual verification" : "Reject offer"}
      description={title}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant={mode === "reject" ? "danger" : "primary"} loading={verify.isPending || reject.isPending} onClick={submit}>
            {mode === "verify" ? "Save verification" : "Reject offer"}
          </Button>
        </>
      }
    >
      {offer ? (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3 rounded border border-line bg-subtle/60 px-3 py-2 text-xs">
            <div>
              <p className="eyebrow">Advertised</p>
              <p className="num mt-0.5 font-medium">{formatPct(offer.advertised_percentage) ?? "Not calculated"}{offer.is_up_to ? " (up to)" : ""}</p>
            </div>
            <div>
              <p className="eyebrow">Coins</p>
              <p className="num mt-0.5 font-medium">{formatNumber(offer.advertised_coins ?? offer.estimated_coins) ?? "Not available"}</p>
            </div>
            <div>
              <p className="eyebrow">Listed price</p>
              <p className="num mt-0.5 font-medium">{formatINR(product?.current_price ?? offer.product?.current_price) ?? "Not available"}</p>
            </div>
          </div>
          <p className="text-xs text-muted">“{offer.title}”</p>

          {mode === "verify" ? (
            <>
              <Notice tone="accent">
                Enter only what your own Flipkart account displays. Never enter passwords, OTPs or session cookies.
              </Notice>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Verification result" htmlFor="v-status">
                  <Select id="v-status" value={form.status} onChange={set("status")}>
                    <option value="VERIFIED">Verified – shown in my account</option>
                    <option value="ACCOUNT_CHECK_REQUIRED">Still requires account check</option>
                  </Select>
                </Field>
                <Field label="Observed at (IST)" htmlFor="v-observed" hint="Defaults to now">
                  <Input id="v-observed" type="datetime-local" value={form.observed_at} onChange={set("observed_at")} />
                </Field>
                <Field label="Reward shown in account (coins)" htmlFor="v-coins">
                  <Input id="v-coins" type="number" min={0} inputMode="numeric" value={form.actual_reward_coins} onChange={set("actual_reward_coins")} />
                </Field>
                <Field
                  label="Eligible purchase amount (₹)"
                  htmlFor="v-amount"
                  hint={actualPct !== null ? `Actual ratio: ${formatPct(actualPct)}` : "Used to calculate the confirmed percentage"}
                >
                  <Input id="v-amount" type="number" min={0} step="0.01" value={form.eligible_purchase_amount} onChange={set("eligible_purchase_amount")} />
                </Field>
                <Field label="Maximum reward cap (coins)" htmlFor="v-cap">
                  <Input id="v-cap" type="number" min={0} value={form.reward_cap_coins} onChange={set("reward_cap_coins")} />
                </Field>
                <Field label="Actual redemption value (₹)" htmlFor="v-value" hint="Only if you confirmed the rupee value">
                  <Input id="v-value" type="number" min={0} step="0.01" value={form.actual_redemption_value} onChange={set("actual_redemption_value")} />
                </Field>
                <Field label="Offer expiry" htmlFor="v-expiry">
                  <Input id="v-expiry" type="date" value={form.expiry} onChange={set("expiry")} />
                </Field>
                <Field label="Restrictions" htmlFor="v-restrictions" hint="Payment method, membership, seller…">
                  <Input id="v-restrictions" maxLength={1000} value={form.restrictions} onChange={set("restrictions")} />
                </Field>
              </div>
              <Field label="Eligibility notes" htmlFor="v-elig">
                <Textarea id="v-elig" maxLength={2000} value={form.eligibility_notes} onChange={set("eligibility_notes")} />
              </Field>
            </>
          ) : (
            <Notice tone="warning">Rejected offers are excluded from active deals and alerts. History is preserved.</Notice>
          )}
          <Field label="Notes" htmlFor="v-notes">
            <Textarea id="v-notes" maxLength={2000} value={form.notes} onChange={set("notes")} />
          </Field>
        </div>
      ) : null}
    </Dialog>
  );
}
