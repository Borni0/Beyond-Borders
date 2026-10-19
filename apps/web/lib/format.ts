/**
 * Money/date formatters used across the UI.
 *
 * All amounts in the UI are *display* values produced by
 * `Intl.NumberFormat`. The actual financial math is done with Decimal
 * arithmetic on the backend (per spec §3 rule 6).
 */

/**
 * Currencies with zero decimal places (ISO 4217) — so we don't render
 * trailing ".00".
 */
const ZERO_DECIMAL_CURRENCIES = new Set([
  "JPY", "KRW", "VND", "CLP", "ISK", "UGX", "PYG", "RWF", "BIF",
]);

/** Format a numeric amount in a given ISO 4217 currency. */
export function formatMoney(
  amount: number | string,
  currency: string,
  options: Intl.NumberFormatOptions = {},
): string {
  const value = typeof amount === "string" ? Number(amount) : amount;
  const fractionDigits = ZERO_DECIMAL_CURRENCIES.has(currency.toUpperCase()) ? 0 : 2;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
    ...options,
  }).format(Number.isFinite(value) ? value : 0);
}

/** Format a date string as a short, locale-friendly label. */
export function formatDate(iso: string | Date): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
  }).format(d);
}

/** Format a date as YYYY-MM-DD for <input type="date"> defaults. */
export function toDateInputValue(iso: string | Date | null | undefined): string {
  if (!iso) return "";
  const d = typeof iso === "string" ? new Date(iso) : iso;
  if (Number.isNaN(d.getTime())) return "";
  return d.toISOString().slice(0, 10);
}

/** Format a 0–100 percentage with one decimal place (rounded half-up). */
export function formatPercent(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "n/a";
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return "n/a";
  return `${n.toFixed(1)}%`;
}
