export const currency = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

export const compactCurrency = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  notation: 'compact',
  maximumFractionDigits: 1,
});

export function formatCurrency(value?: number | null) {
  return currency.format(value ?? 0);
}

export function formatCompactCurrency(value?: number | null) {
  return compactCurrency.format(value ?? 0);
}

export function formatPercent(value?: number | null) {
  return `${(value ?? 0).toFixed(1)}%`;
}

export function monthLabel(value: string) {
  return new Intl.DateTimeFormat('en-IN', { month: 'short', year: '2-digit' }).format(new Date(value));
}

