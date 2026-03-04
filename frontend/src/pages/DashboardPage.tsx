import { useEffect } from "react";
import { Activity, CheckCircle, Clock, XCircle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { TrendChart } from "@/components/dashboard/TrendChart";
import { FlagBreakdownChart } from "@/components/dashboard/FlagBreakdownChart";
import { ScoreGauge } from "@/components/dashboard/ScoreGauge";
import { useApi } from "@/hooks/use-api";
import { fetchMetrics } from "@/services/api";
import { formatDuration, formatScore } from "@/lib/format";
import { DASHBOARD_REFRESH_MS } from "@/lib/constants";

/**
 * Main dashboard page with KPI cards, trend chart, and flag breakdown.
 * Auto-refreshes every 60 seconds.
 */
export function DashboardPage() {
  const {
    data: metrics,
    isLoading,
    error,
    refetch,
  } = useApi(() => fetchMetrics());

  useEffect(() => {
    const interval = setInterval(refetch, DASHBOARD_REFRESH_MS);
    return () => clearInterval(interval);
  }, [refetch]);

  if (error) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-destructive">
          Failed to load metrics: {error.message}
        </p>
      </div>
    );
  }

  if (isLoading || !metrics) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Total Requests"
          value={metrics.total_requests.toLocaleString()}
          icon={Activity}
          description={`${metrics.date_from} to ${metrics.date_to}`}
        />
        <KpiCard
          title="Passed"
          value={metrics.total_passed.toLocaleString()}
          icon={CheckCircle}
          description={`${formatScore(metrics.compliance_rate)} compliance rate`}
        />
        <KpiCard
          title="Failed"
          value={metrics.total_failed.toLocaleString()}
          icon={XCircle}
        />
        <KpiCard
          title="Avg Duration"
          value={formatDuration(metrics.avg_duration_ms)}
          icon={Clock}
        />
      </div>

      {/* Charts row */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <TrendChart data={metrics.time_series} />
        </div>
        <ScoreGauge score={metrics.avg_score} />
      </div>

      {/* Flag breakdown */}
      <FlagBreakdownChart data={metrics.flags_breakdown} />
    </div>
  );
}
