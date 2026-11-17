"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { Notice } from "@/components/ui/states";
import { useApiMutation } from "@/hooks/use-api";
import { api } from "@/services/api";
import type { ProductRow } from "@/services/types";

const INVALIDATE = ["/products", "/offers", "/dashboard", "/price-history"];

export function EditProductDialog({ product, open, onClose }: { product: ProductRow; open: boolean; onClose: () => void }) {
  const [form, setForm] = useState(() => ({
    title: product.title ?? "",
    brand: product.brand ?? "",
    category: product.category ?? "",
    seller: product.seller ?? "",
    variant: product.variant ?? "",
    image_url: product.image_url ?? "",
    current_price: product.current_price?.toString() ?? "",
    mrp: product.mrp?.toString() ?? "",
    shipping_charge: product.shipping_charge?.toString() ?? "",
    in_stock: product.in_stock === null ? "" : String(product.in_stock),
  }));
  const save = useApiMutation((body: Record<string, unknown>) => api.patch(`/products/${product.id}`, body), {
    invalidate: INVALIDATE,
    success: "Product details saved",
    onSuccess: onClose,
  });
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = () => {
    const body: Record<string, unknown> = {};
    const text = ["title", "brand", "category", "seller", "variant", "image_url"] as const;
    for (const k of text) {
      const original = (product[k] ?? "") as string;
      if (form[k] !== original) body[k] = form[k].trim() || null;
    }
    for (const k of ["current_price", "mrp", "shipping_charge"] as const) {
      const original = product[k]?.toString() ?? "";
      if (form[k] !== original) body[k] = form[k] === "" ? null : Number(form[k]);
    }
    const stock = product.in_stock === null ? "" : String(product.in_stock);
    if (form.in_stock !== stock) body.in_stock = form.in_stock === "" ? null : form.in_stock === "true";
    if (Object.keys(body).length === 0) return onClose();
    save.mutate(body);
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      width="lg"
      title="Edit product details"
      description="Manual values are recorded as manual price observations and kept in history."
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
        <Field label="Title" htmlFor="e-title" className="col-span-2">
          <Input id="e-title" value={form.title} maxLength={1000} onChange={set("title")} />
        </Field>
        <Field label="Brand" htmlFor="e-brand">
          <Input id="e-brand" value={form.brand} maxLength={255} onChange={set("brand")} />
        </Field>
        <Field label="Category" htmlFor="e-category">
          <Input id="e-category" value={form.category} maxLength={255} onChange={set("category")} />
        </Field>
        <Field label="Seller" htmlFor="e-seller">
          <Input id="e-seller" value={form.seller} maxLength={255} onChange={set("seller")} />
        </Field>
        <Field label="Variant" htmlFor="e-variant">
          <Input id="e-variant" value={form.variant} maxLength={255} onChange={set("variant")} />
        </Field>
        <Field label="Selling price (₹)" htmlFor="e-price">
          <Input id="e-price" type="number" min={0} step="0.01" value={form.current_price} onChange={set("current_price")} />
        </Field>
        <Field label="MRP (₹)" htmlFor="e-mrp">
          <Input id="e-mrp" type="number" min={0} step="0.01" value={form.mrp} onChange={set("mrp")} />
        </Field>
        <Field label="Shipping charge (₹)" htmlFor="e-ship">
          <Input id="e-ship" type="number" min={0} step="0.01" value={form.shipping_charge} onChange={set("shipping_charge")} />
        </Field>
        <Field label="Stock" htmlFor="e-stock">
          <Select id="e-stock" value={form.in_stock} onChange={set("in_stock")}>
            <option value="">Not available</option>
            <option value="true">In stock</option>
            <option value="false">Out of stock</option>
          </Select>
        </Field>
        <Field label="Image URL (https)" htmlFor="e-image" className="col-span-2">
          <Input id="e-image" value={form.image_url} maxLength={2048} onChange={set("image_url")} />
        </Field>
      </div>
    </Dialog>
  );
}

export function ManualOfferDialog({ productId, open, onClose }: { productId: string; open: boolean; onClose: () => void }) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const save = useApiMutation((body: { text: string }) => api.post<{ data: { created: number; updated: number } }>(`/products/${productId}/offers`, body), {
    invalidate: INVALIDATE,
    success: (r) => `${r.data.created} offer(s) created, ${r.data.updated} updated`,
    onSuccess: () => {
      setText("");
      onClose();
    },
  });
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Record offer text"
      description="Paste the offer wording exactly as displayed. It is classified by the same engine and stays unverified until you verify it."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            loading={save.isPending}
            disabled={text.trim().length < 6}
            onClick={() => {
              setError(null);
              save.mutate({ text: text.trim() }, { onError: (e) => setError(e.message) });
            }}
          >
            Classify and save
          </Button>
        </>
      }
    >
      <Field label="Offer text" htmlFor="m-text" error={error} hint="Example: Get 100% SuperCoins back, up to 500 SuperCoins. Valid till 30 Nov.">
        <Textarea id="m-text" rows={5} maxLength={2000} value={text} onChange={(e) => setText(e.target.value)} />
      </Field>
    </Dialog>
  );
}

export function ArchiveDialog({ productId, open, onClose }: { productId: string; open: boolean; onClose: () => void }) {
  const router = useRouter();
  const archive = useApiMutation(() => api.del(`/products/${productId}`), {
    invalidate: ["/products", "/offers", "/dashboard", "/monitoring", "/watchlist"],
    success: "Product archived",
    onSuccess: () => router.push("/explorer"),
  });
  return (
    <Dialog
      open={open}
      onClose={onClose}
      width="sm"
      title="Archive product"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="danger" loading={archive.isPending} onClick={() => archive.mutate(undefined)}>
            Archive
          </Button>
        </>
      }
    >
      <Notice tone="warning">The product is hidden from lists and monitoring stops. Price, offer and verification history are preserved. Re-submitting the URL restores it.</Notice>
    </Dialog>
  );
}
