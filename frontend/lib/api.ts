import type { AnalysisRecord, ApiHealth, DashboardData } from "@/lib/types";

const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function getApiHealth(): Promise<ApiHealth> {
  return fetchJson<ApiHealth>("/api/v1/health");
}

export async function getAnalysisResults(): Promise<AnalysisRecord[]> {
  try {
    const data = await fetchJson<unknown>("/api/v1/analysis-results");
    if (!data || typeof data !== "object" || Array.isArray(data)) {
      throw new Error("Unexpected analysis result shape");
    }

    return Object.entries(data as Record<string, unknown>).map(([id, result]) => ({
      id,
      result: result as AnalysisRecord["result"],
    }));
  } catch (error) {
    if (error instanceof Error && error.message.includes("404")) {
      return [];
    }
    throw error;
  }
}

export async function getDashboardData(): Promise<DashboardData> {
  const errors: string[] = [];
  let health: ApiHealth | null = null;
  let analyses: AnalysisRecord[] = [];

  try {
    health = await getApiHealth();
  } catch (error) {
    errors.push(error instanceof Error ? error.message : "API health check failed");
  }

  try {
    analyses = await getAnalysisResults();
  } catch (error) {
    errors.push(error instanceof Error ? error.message : "Analysis result fetch failed");
  }

  return { health, analyses, errors };
}
