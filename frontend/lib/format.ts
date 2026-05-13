export function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }

  return new Intl.NumberFormat("en", {
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }

  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

export function formatRatio(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }

  return `${(value * 100).toFixed(1)}%`;
}

export function formatDisplayValue(
  value: number | null | undefined,
  valueFormat: "number" | "percentage" = "number",
) {
  return valueFormat === "percentage" ? formatRatio(value) : formatNumber(value);
}
