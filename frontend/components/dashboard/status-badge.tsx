import { Badge } from "@/components/ui/badge";
import type { ApiHealth } from "@/lib/types";

export function StatusBadge({ health }: { health: ApiHealth | null }) {
  const isHealthy = health?.status === "healthy";

  return (
    <Badge tone={isHealthy ? "success" : "danger"}>
      {isHealthy ? "API connected" : "API unavailable"}
    </Badge>
  );
}
