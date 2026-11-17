import { forwardRef, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";

import { cn } from "@/services/cn";

const control =
  "w-full rounded border border-line-strong/70 bg-surface text-sm text-fg placeholder:text-faint transition-colors hover:border-line-strong focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 disabled:cursor-not-allowed disabled:opacity-60";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & { compact?: boolean }>(function Input(
  { className, compact, ...props },
  ref,
) {
  return <input ref={ref} className={cn(control, compact ? "h-7 px-2 text-xs" : "h-8 px-2.5", className)} {...props} />;
});

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea({ className, ...props }, ref) {
  return <textarea ref={ref} className={cn(control, "min-h-[72px] px-2.5 py-1.5 leading-5", className)} {...props} />;
});

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement> & { compact?: boolean }>(function Select(
  { className, compact, children, ...props },
  ref,
) {
  return (
    <div className={cn("relative", className)}>
      <select ref={ref} className={cn(control, "appearance-none pr-7", compact ? "h-7 pl-2 text-xs" : "h-8 pl-2.5")} {...props}>
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" aria-hidden />
    </div>
  );
});

export function Label({ children, htmlFor, className }: { children: ReactNode; htmlFor?: string; className?: string }) {
  return (
    <label htmlFor={htmlFor} className={cn("mb-1 block text-xs font-medium text-muted", className)}>
      {children}
    </label>
  );
}

export function Field({ label, hint, error, htmlFor, children, className }: { label: string; hint?: ReactNode; error?: string | null; htmlFor?: string; children: ReactNode; className?: string }) {
  return (
    <div className={className}>
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {error ? <p className="mt-1 text-2xs text-negative">{error}</p> : hint ? <p className="mt-1 text-2xs text-faint">{hint}</p> : null}
    </div>
  );
}

export function Switch({ checked, onChange, label, disabled, id }: { checked: boolean; onChange: (v: boolean) => void; label?: string; disabled?: boolean; id?: string }) {
  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-[18px] w-8 shrink-0 items-center rounded-full border transition-colors disabled:opacity-50",
        checked ? "border-accent bg-accent" : "border-line-strong bg-subtle",
      )}
    >
      <span className={cn("inline-block h-3 w-3 rounded-full bg-surface shadow transition-transform", checked ? "translate-x-[15px]" : "translate-x-[2px]")} />
    </button>
  );
}

export function Checkbox({ checked, indeterminate, onChange, label, disabled }: { checked: boolean; indeterminate?: boolean; onChange: (v: boolean) => void; label?: string; disabled?: boolean }) {
  return (
    <input
      type="checkbox"
      aria-label={label}
      disabled={disabled}
      checked={checked}
      ref={(el) => {
        if (el) el.indeterminate = Boolean(indeterminate) && !checked;
      }}
      onChange={(e) => onChange(e.target.checked)}
      onClick={(e) => e.stopPropagation()}
      className="h-3.5 w-3.5 cursor-pointer rounded-sm border-line-strong accent-[hsl(var(--accent))] disabled:cursor-not-allowed"
    />
  );
}
