import type {
  AnalysisRecord,
  ApiHealth,
  DashboardData,
  DashboardResultsResponse,
} from "@/lib/types";

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

export async function fetchDashboardResults(): Promise<AnalysisRecord[]> {
  const data = await fetchJson<DashboardResultsResponse>("/api/v1/dashboard/results");
  if (!data || !Array.isArray(data.items)) {
    throw new Error("Unexpected dashboard result shape");
  }

  return data.items.map((result) => ({
    id: result.id || result.analysis_id,
    result,
  }));
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
    analyses = await fetchDashboardResults();
  } catch (error) {
    errors.push(error instanceof Error ? error.message : "Analysis result fetch failed");
  }

  return { health, analyses, errors };
}
