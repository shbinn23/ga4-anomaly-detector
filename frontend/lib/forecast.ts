import type { ForecastData, ForecastPoint } from "@/lib/types";

export function normalizeForecastData(forecastData?: ForecastData): ForecastPoint[] {
  if (!forecastData) {
    return [];
  }

  const required = [
    forecastData.ds,
    forecastData.y,
    forecastData.yhat,
    forecastData.yhat_lower,
    forecastData.yhat_upper,
  ];

  const length = forecastData.ds?.length ?? 0;
  if (!length || required.some((items) => !Array.isArray(items) || items.length !== length)) {
    return [];
  }

  return forecastData.ds.map((ds, index) => {
    const y = Number(forecastData.y[index]);
    const yhat = Number(forecastData.yhat[index]);
    const lower = Number(forecastData.yhat_lower[index]);
    const upper = Number(forecastData.yhat_upper[index]);
    const explicit = forecastData.is_anomaly?.[index];

    return {
      ds,
      y,
      yhat,
      yhat_lower: lower,
      yhat_upper: upper,
      is_anomaly: explicit ?? (y < lower || y > upper),
    };
  });
}

export function latestForecastPoint(forecastData?: ForecastData) {
  const points = normalizeForecastData(forecastData);
  return points.at(-1) ?? null;
}

export function countAnomalyPoints(forecastData?: ForecastData) {
  return normalizeForecastData(forecastData).filter((point) => point.is_anomaly).length;
}

export function lastAnomalyDate(forecastData?: ForecastData) {
  return normalizeForecastData(forecastData)
    .filter((point) => point.is_anomaly)
    .at(-1)?.ds ?? "-";
}
