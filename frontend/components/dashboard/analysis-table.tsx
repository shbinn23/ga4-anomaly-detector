import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatNumber, formatPercent } from "@/lib/format";
import type { AnalysisTableRow } from "@/lib/types";

export function AnalysisTable({
  rows,
  title = "Analysis ledger",
}: {
  rows: AnalysisTableRow[];
  title?: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl font-semibold tracking-[-0.02em]">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Property</TableHead>
              <TableHead>Domain</TableHead>
              <TableHead>Mode</TableHead>
              <TableHead>Metric</TableHead>
              <TableHead>Dimension</TableHead>
              <TableHead>Dimension value</TableHead>
              <TableHead>Anomalies</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Last anomaly</TableHead>
              <TableHead>Latest y</TableHead>
              <TableHead>Latest yhat</TableHead>
              <TableHead>Deviation</TableHead>
              <TableHead>Direction</TableHead>
              <TableHead>Detail</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow
                className={row.alertStatus === "alert" ? "bg-anomaly-muted/45 hover:bg-anomaly-muted/65" : undefined}
                key={row.id}
              >
                <TableCell className="font-medium">{row.propertyName}</TableCell>
                <TableCell className="font-medium">{row.domain}</TableCell>
                <TableCell className="text-muted-foreground">{row.mode}</TableCell>
                <TableCell className="text-muted-foreground">{row.metricName}</TableCell>
                <TableCell className="font-medium">{row.dimension}</TableCell>
                <TableCell className="text-muted-foreground">{row.dimensionValue}</TableCell>
                <TableCell>{formatNumber(row.anomalyCount)}</TableCell>
                <TableCell>
                  <Badge tone={row.alertStatus === "alert" ? "anomaly" : row.alertStatus === "watch" ? "warning" : "neutral"}>
                    {row.alertStatus}
                  </Badge>
                </TableCell>
                <TableCell>{row.lastAnomalyDate}</TableCell>
                <TableCell>{formatNumber(row.latestY)}</TableCell>
                <TableCell>{formatNumber(row.latestYhat)}</TableCell>
                <TableCell className={row.alertStatus === "alert" ? "font-semibold text-anomaly-foreground" : undefined}>
                  {formatPercent(row.latestDeviation)}
                </TableCell>
                <TableCell>
                  <Badge tone={row.alertStatus === "alert" ? "anomaly" : row.direction === "unknown" ? "neutral" : row.direction === "flat" ? "success" : "warning"}>
                    {row.direction}
                  </Badge>
                </TableCell>
                <TableCell>
                  {row.detailHref ? (
                    <Link className="text-sm font-medium underline-offset-4 hover:underline" href={row.detailHref}>
                      {row.detailLabel ?? "Open"}
                    </Link>
                  ) : (
                    <span className="text-sm text-muted-foreground">
                      {row.detailLabel ?? (row.detailDisabled ? "Unavailable" : "-")}
                    </span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
