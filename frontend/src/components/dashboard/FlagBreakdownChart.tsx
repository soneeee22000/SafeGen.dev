import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { FlagBreakdown } from "@/types";
import { CHART_COLORS } from "@/lib/constants";

interface FlagBreakdownChartProps {
  data: FlagBreakdown[];
}

/**
 * Bar chart of flag counts by layer and severity.
 */
export function FlagBreakdownChart({ data }: FlagBreakdownChartProps) {
  const chartData = data.map((item) => ({
    name: `${item.layer} (${item.severity})`,
    count: item.count,
    fill:
      CHART_COLORS[item.layer as keyof typeof CHART_COLORS] ??
      CHART_COLORS.total,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Flag Breakdown</CardTitle>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <p className="py-12 text-center text-sm text-muted-foreground">
            No flags recorded
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="name" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--popover)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius)",
                  color: "var(--popover-foreground)",
                }}
              />
              <Bar dataKey="count" name="Flags" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
