import type { Config } from "tailwindcss";

const token = (name: string) => `hsl(var(--${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./dashboard/**/*.{ts,tsx}", "./hooks/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: token("canvas"),
        surface: token("surface"),
        subtle: token("subtle"),
        line: token("line"),
        "line-strong": token("line-strong"),
        fg: token("fg"),
        muted: token("muted"),
        faint: token("faint"),
        accent: { DEFAULT: token("accent"), soft: token("accent-soft"), fg: token("accent-fg") },
        positive: { DEFAULT: token("positive"), soft: token("positive-soft") },
        warning: { DEFAULT: token("warning"), soft: token("warning-soft") },
        negative: { DEFAULT: token("negative"), soft: token("negative-soft") },
        sidebar: { DEFAULT: token("sidebar"), fg: token("sidebar-fg"), muted: token("sidebar-muted"), hover: token("sidebar-hover"), line: token("sidebar-line") },
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
        xs: ["0.75rem", { lineHeight: "1.05rem" }],
        sm: ["0.8125rem", { lineHeight: "1.25rem" }],
        base: ["0.875rem", { lineHeight: "1.375rem" }],
      },
      borderRadius: { sm: "4px", DEFAULT: "6px", md: "6px", lg: "8px" },
      boxShadow: {
        panel: "0 1px 0 0 hsl(var(--line) / 0.6)",
        pop: "0 8px 24px -8px rgb(15 23 42 / 0.18), 0 2px 6px -2px rgb(15 23 42 / 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
