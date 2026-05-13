import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

export function AnalysisTable({ rows }: { rows: AnalysisTableRow[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="serif-heading text-2xl">Analysis ledger</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Domain</TableHead>
              <TableHead>Mode</TableHead>
              <TableHead>Metric</TableHead>
              <TableHead>Dimension</TableHead>
              <TableHead>Dimension value</TableHead>
              <TableHead>Anomalies</TableHead>
              <TableHead>Last anomaly</TableHead>
              <TableHead>Latest y</TableHead>
              <TableHead>Latest yhat</TableHead>
              <TableHead>Deviation</TableHead>
              <TableHead>Direction</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.id}>
                <TableCell className="font-medium">{row.domain}</TableCell>
                <TableCell className="text-muted-foreground">{row.mode}</TableCell>
                <TableCell className="text-muted-foreground">{row.metricName}</TableCell>
                <TableCell className="font-medium">{row.dimension}</TableCell>
                <TableCell className="text-muted-foreground">{row.dimensionValue}</TableCell>
                <TableCell>{formatNumber(row.anomalyCount)}</TableCell>
                <TableCell>{row.lastAnomalyDate}</TableCell>
                <TableCell>{formatNumber(row.latestY)}</TableCell>
                <TableCell>{formatNumber(row.latestYhat)}</TableCell>
                <TableCell>{formatPercent(row.latestDeviation)}</TableCell>
                <TableCell>
                  <Badge tone={row.direction === "unknown" ? "neutral" : row.direction === "flat" ? "success" : "warning"}>
                    {row.direction}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
