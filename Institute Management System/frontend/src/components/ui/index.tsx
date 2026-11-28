"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as Dropdown from "@radix-ui/react-dropdown-menu";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { Inbox, Loader2, X } from "lucide-react";
import { forwardRef, useState, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

// ----------------------------------------------------------------------------- Button

type Variant = "primary" | "secondary" | "ghost" | "danger" | "outline" | "accent";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-brand-800 text-white hover:bg-brand-700 focus-visible:ring-brand-200",
  accent: "bg-accent-500 text-white hover:bg-accent-600 focus-visible:ring-teal-200",
  secondary: "bg-slate-100 text-slate-800 hover:bg-slate-200 focus-visible:ring-slate-200",
  outline: "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 focus-visible:ring-slate-200",
  ghost: "text-slate-600 hover:bg-slate-100 focus-visible:ring-slate-200",
  danger: "bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-200",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: "sm" | "md" | "icon";
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading, className, children, disabled, type = "button", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:cursor-not-allowed disabled:opacity-60",
        size === "sm" ? "h-8 px-2.5 text-xs" : size === "icon" ? "h-8 w-8" : "h-9 px-3.5 text-sm",
        VARIANTS[variant],
        className,
      )}
      {...rest}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
});

// ----------------------------------------------------------------------------- form controls

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input({ className, ...rest }, ref) {
  return <input ref={ref} className={cn("input", className)} {...rest} />;
});

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea({ className, ...rest }, ref) {
  return <textarea ref={ref} className={cn("input h-auto min-h-[84px] py-2", className)} {...rest} />;
});

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(function Select({ className, children, ...rest }, ref) {
  return (
    <select ref={ref} className={cn("input pr-8", className)} {...rest}>
      {children}
    </select>
  );
});

export function Field({ label, error, hint, required, children, className }: { label: string; error?: string; hint?: string; required?: boolean; children: ReactNode; className?: string }) {
  return (
    <div className={className}>
      <label className="label">
        {label}
        {required && <span className="ml-0.5 text-red-500">*</span>}
      </label>
      {children}
      {error ? <p className="mt-1 text-xs text-red-600">{error}</p> : hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}

// ----------------------------------------------------------------------------- display

export function Card({ className, children, title, actions, bodyClass }: { className?: string; children: ReactNode; title?: ReactNode; actions?: ReactNode; bodyClass?: string }) {
  return (
    <section className={cn("card", className)}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={cn("p-4", bodyClass)}>{children}</div>
    </section>
  );
}

const TONES: Record<string, string> = {
  green: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  amber: "bg-amber-50 text-amber-700 ring-amber-600/20",
  red: "bg-red-50 text-red-700 ring-red-600/20",
  blue: "bg-blue-50 text-blue-700 ring-blue-600/20",
  indigo: "bg-indigo-50 text-indigo-700 ring-indigo-600/20",
  slate: "bg-slate-100 text-slate-600 ring-slate-500/20",
  teal: "bg-teal-50 text-teal-700 ring-teal-600/20",
};

const STATUS_TONE: Record<string, string> = {
  active: "green", completed: "green", paid: "green", present: "green", approved: "green", published: "green", evaluated: "green",
  submitted: "blue", sent: "green", processed: "green", delivered: "green", enrolled: "green", graded: "green", succeeded: "green",
  results_published: "green", returned: "green", open: "blue", issued: "blue", scheduled: "blue", in_progress: "indigo", live: "indigo",
  submission_open: "indigo", draft: "slate", planned: "slate", not_started: "slate", queued: "slate", new: "slate", pending: "amber",
  partially_paid: "amber", late: "amber", pending_review: "amber", under_review: "amber", pending_verification: "amber", reopened: "amber",
  postponed: "amber", resubmission_requested: "amber", excused: "teal", approved_leave: "teal", on_leave: "teal", under_evaluation: "amber",
  overdue: "red", absent: "red", cancelled: "red", rejected: "red", failed: "red", reversed: "red", bounced: "red", lost: "red",
  teacher_absent: "red", withdrawn: "red", inactive: "slate", archived: "slate", closed: "slate", void: "slate", waived: "slate",
  not_submitted: "red", invoiced: "teal",
};

export function Badge({ children, tone = "slate", className }: { children: ReactNode; tone?: string; className?: string }) {
  return <span className={cn("inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset", TONES[tone] ?? TONES.slate, className)}>{children}</span>;
}

export function StatusBadge({ value }: { value?: string | null }) {
  if (!value) return <span className="text-slate-400">—</span>;
  return <Badge tone={STATUS_TONE[value] ?? "slate"}>{value.replace(/_/g, " ")}</Badge>;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-slate-200/70", className)} />;
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-sm text-slate-500">
      <Loader2 className="h-5 w-5 animate-spin" /> {label ?? "Loading…"}
    </div>
  );
}

export function EmptyState({ title, description, action, icon }: { title: string; description?: string; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-3 rounded-full bg-slate-100 p-3 text-slate-400">{icon ?? <Inbox className="h-6 w-6" />}</div>
      <p className="text-sm font-semibold text-slate-700">{title}</p>
      {description && <p className="mt-1 max-w-md text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const msg = error instanceof Error ? error.message : "Unable to load data";
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {msg}
      {onRetry && (
        <button className="ml-3 font-medium underline" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function PageHeader({ title, description, actions, breadcrumbs }: { title: ReactNode; description?: ReactNode; actions?: ReactNode; breadcrumbs?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {breadcrumbs && <div className="mb-1 text-xs text-slate-500">{breadcrumbs}</div>}
        <h1 className="text-xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function StatCard({ label, value, icon, hint, tone = "brand" }: { label: string; value: ReactNode; icon?: ReactNode; hint?: ReactNode; tone?: "brand" | "teal" | "amber" | "red" | "green" }) {
  const ring = { brand: "bg-indigo-50 text-brand-800", teal: "bg-teal-50 text-teal-700", amber: "bg-amber-50 text-amber-700", red: "bg-red-50 text-red-700", green: "bg-emerald-50 text-emerald-700" }[tone];
  return (
    <div className="card flex items-start gap-3 p-4">
      {icon && <div className={cn("rounded-lg p-2", ring)}>{icon}</div>}
      <div className="min-w-0">
        <p className="truncate text-xs font-medium text-slate-500">{label}</p>
        <p className="mt-0.5 text-xl font-semibold text-slate-900">{value}</p>
        {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------------- dialogs

export function Modal({ open, onOpenChange, title, description, children, footer, wide }: {
  open: boolean; onOpenChange: (v: boolean) => void; title: string; description?: string; children: ReactNode; footer?: ReactNode; wide?: boolean;
}) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-slate-900/40" />
        <DialogPrimitive.Content
          className={cn(
            "fixed left-1/2 top-1/2 z-50 flex max-h-[92vh] w-[95vw] -translate-x-1/2 -translate-y-1/2 flex-col rounded-xl bg-white shadow-xl focus:outline-none",
            wide ? "max-w-3xl" : "max-w-lg",
          )}
        >
          <div className="flex items-start justify-between border-b border-slate-100 px-5 py-4">
            <div>
              <DialogPrimitive.Title className="text-base font-semibold text-slate-900">{title}</DialogPrimitive.Title>
              {description ? (
                <DialogPrimitive.Description className="mt-0.5 text-sm text-slate-500">{description}</DialogPrimitive.Description>
              ) : (
                <DialogPrimitive.Description className="sr-only">{title}</DialogPrimitive.Description>
              )}
            </div>
            <DialogPrimitive.Close className="rounded-md p-1 text-slate-400 hover:bg-slate-100" aria-label="Close">
              <X className="h-4 w-4" />
            </DialogPrimitive.Close>
          </div>
          <div className="overflow-y-auto px-5 py-4">{children}</div>
          {footer && <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-3">{footer}</div>}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

export function ConfirmDialog({ open, onOpenChange, title, message, confirmLabel = "Confirm", danger, requireReason, onConfirm }: {
  open: boolean; onOpenChange: (v: boolean) => void; title: string; message?: ReactNode; confirmLabel?: string; danger?: boolean;
  requireReason?: boolean; onConfirm: (reason?: string) => Promise<void> | void;
}) {
  const [busy, setBusy] = useState(false);
  const [reason, setReason] = useState("");
  return (
    <Modal
      open={open}
      onOpenChange={(v) => {
        if (!v) setReason("");
        onOpenChange(v);
      }}
      title={title}
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button
            variant={danger ? "danger" : "primary"}
            loading={busy}
            disabled={requireReason && reason.trim().length < 3}
            onClick={async () => {
              setBusy(true);
              try {
                await onConfirm(reason.trim() || undefined);
                setReason("");
                onOpenChange(false);
              } finally {
                setBusy(false);
              }
            }}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      {message && <div className="text-sm text-slate-600">{message}</div>}
      {requireReason && (
        <Field label="Reason" required className="mt-3">
          <Textarea value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Recorded in the audit log" />
        </Field>
      )}
    </Modal>
  );
}

// ----------------------------------------------------------------------------- menus & tabs

export function Menu({ trigger, items }: { trigger: ReactNode; items: { label: string; onClick: () => void; danger?: boolean; icon?: ReactNode; hidden?: boolean }[] }) {
  const visible = items.filter((i) => !i.hidden);
  if (!visible.length) return null;
  return (
    <Dropdown.Root>
      <Dropdown.Trigger asChild>{trigger}</Dropdown.Trigger>
      <Dropdown.Portal>
        <Dropdown.Content align="end" sideOffset={4} className="z-50 min-w-[180px] rounded-lg border border-slate-200 bg-white p-1 shadow-lg">
          {visible.map((i) => (
            <Dropdown.Item
              key={i.label}
              onSelect={i.onClick}
              className={cn(
                "flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-1.5 text-sm outline-none data-[highlighted]:bg-slate-100",
                i.danger ? "text-red-600" : "text-slate-700",
              )}
            >
              {i.icon}
              {i.label}
            </Dropdown.Item>
          ))}
        </Dropdown.Content>
      </Dropdown.Portal>
    </Dropdown.Root>
  );
}

export function Tabs({ tabs, defaultValue, value, onValueChange }: { tabs: { value: string; label: string; content: ReactNode; hidden?: boolean }[]; defaultValue?: string; value?: string; onValueChange?: (v: string) => void }) {
  const shown = tabs.filter((t) => !t.hidden);
  return (
    <TabsPrimitive.Root defaultValue={defaultValue ?? shown[0]?.value} value={value} onValueChange={onValueChange}>
      <TabsPrimitive.List className="mb-4 flex gap-1 overflow-x-auto border-b border-slate-200">
        {shown.map((t) => (
          <TabsPrimitive.Trigger
            key={t.value}
            value={t.value}
            className="whitespace-nowrap border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 hover:text-slate-800 data-[state=active]:border-brand-800 data-[state=active]:text-brand-800"
          >
            {t.label}
          </TabsPrimitive.Trigger>
        ))}
      </TabsPrimitive.List>
      {shown.map((t) => (
        <TabsPrimitive.Content key={t.value} value={t.value} className="focus:outline-none">
          {t.content}
        </TabsPrimitive.Content>
      ))}
    </TabsPrimitive.Root>
  );
}

// ----------------------------------------------------------------------------- simple table

export function SimpleTable({ headers, rows, empty }: { headers: ReactNode[]; rows: ReactNode[][]; empty?: string }) {
  if (!rows.length) return <EmptyState title={empty ?? "No records"} />;
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-100">
        <thead className="bg-slate-50">
          <tr>{headers.map((h, i) => <th key={i} className="th">{h}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((r, i) => (
            <tr key={i} className="hover:bg-slate-50/60">
              {r.map((c, j) => <td key={j} className="td">{c}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
