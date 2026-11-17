import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Loader2 } from "lucide-react";

import { cn } from "@/services/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "link";
type Size = "xs" | "sm" | "md" | "icon" | "icon-sm";

const variants: Record<Variant, string> = {
  primary: "bg-accent text-accent-fg hover:bg-accent/90 border border-accent",
  secondary: "bg-surface text-fg border border-line-strong/70 hover:bg-subtle",
  ghost: "text-muted hover:text-fg hover:bg-subtle border border-transparent",
  danger: "bg-surface text-negative border border-negative/40 hover:bg-negative-soft",
  link: "text-accent hover:underline underline-offset-2 border border-transparent px-0",
};
const sizes: Record<Size, string> = {
  xs: "h-6 px-2 text-2xs gap-1",
  sm: "h-7 px-2.5 text-xs gap-1.5",
  md: "h-8 px-3 text-sm gap-2",
  icon: "h-8 w-8 justify-center",
  "icon-sm": "h-7 w-7 justify-center",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", size = "md", loading, disabled, className, children, type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      className={cn(
        "inline-flex shrink-0 items-center rounded font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    >
      {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
      {children}
    </button>
  );
});
