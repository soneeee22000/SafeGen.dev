import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TimeSeriesPoint } from "@/types";
import { CHART_COLORS } from "@/lib/constants";

interface TrendChartProps {
  data: TimeSeriesPoint[];
}

/**
 * Area chart showing daily total/passed/failed requests over time.
 */
export function TrendChart({ data }: TrendChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Request Trend</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              dataKey="date"
              tickFormatter={(d: string) => d.slice(5)}
              className="text-xs"
            />
            <YAxis className="text-xs" />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--popover)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius)",
                color: "var(--popover-foreground)",
              }}
            />
            <Area
              type="monotone"
              dataKey="total_requests"
              name="Total"
              stroke={CHART_COLORS.total}
              fill={CHART_COLORS.total}
              fillOpacity={0.1}
            />
            <Area
              type="monotone"
              dataKey="passed"
              name="Passed"
              stroke={CHART_COLORS.passed}
              fill={CHART_COLORS.passed}
              fillOpacity={0.1}
            />
            <Area
              type="monotone"
              dataKey="failed"
              name="Failed"
              stroke={CHART_COLORS.failed}
              fill={CHART_COLORS.failed}
              fillOpacity={0.1}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
