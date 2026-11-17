"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Switch } from "@/components/ui/field";
import { Notice } from "@/components/ui/states";
import { useApi, useApiMutation } from "@/hooks/use-api";
import { api } from "@/services/api";
import type { AppSettings, Envelope, ProductRow } from "@/services/types";

export function AddProductDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [monitor, setMonitor] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const settings = useApi<Envelope<AppSettings>>(open ? "/settings" : null);
  useEffect(() => {
    if (open && settings.data) setMonitor(settings.data.data.monitor_new_submissions);
  }, [open, settings.data]);

  const submit = useApiMutation((body: { url: string; monitor: boolean }) => api.post<Envelope<ProductRow & { created: boolean }>>("/products", body), {
    invalidate: ["/products", "/dashboard", "/monitoring"],
    success: (r) => (r.data.created ? "Product added" : "Product already tracked"),
    onSuccess: (r) => {
      setUrl("");
      onClose();
      router.push(`/products/${r.data.id}`);
    },
  });

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Add Flipkart product"
      description="Paste a full product URL. It is validated against the approved Flipkart domains and de-duplicated."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            loading={submit.isPending}
            disabled={url.trim().length < 10}
            onClick={() => {
              setError(null);
              submit.mutate({ url: url.trim(), monitor }, { onError: (e) => setError(e.message) });
            }}
          >
            Add product
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <Field label="Product URL" htmlFor="add-url" error={error} hint="Example: https://www.flipkart.com/…/p/itm…?pid=…">
          <Input id="add-url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://www.flipkart.com/" maxLength={2048} autoComplete="off" />
        </Field>
        <label className="flex items-center justify-between gap-3 rounded border border-line px-3 py-2">
          <span>
            <span className="block text-sm font-medium">Monitor this product</span>
            <span className="block text-xs text-muted">Adds the product to the scan queue at the configured interval.</span>
          </span>
          <Switch checked={monitor} onChange={setMonitor} label="Monitor this product" />
        </label>
        <Notice>
          Automatic price and offer collection only happens through permitted access methods. If product-page access is not enabled,
          record prices and offers manually from the product page in this application.
        </Notice>
      </div>
    </Dialog>
  );
}
