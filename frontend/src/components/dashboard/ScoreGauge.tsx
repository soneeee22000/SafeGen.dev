import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatScore, scoreBgColor, scoreColor } from "@/lib/format";
import { cn } from "@/lib/utils";

interface ScoreGaugeProps {
  score: number;
}

/**
 * Visual average compliance score indicator with color coding.
 */
export function ScoreGauge({ score }: ScoreGaugeProps) {
  const percentage = Math.round(score * 100);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Avg Compliance Score</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-center gap-4">
        <div className="relative h-32 w-32">
          {/* Background ring */}
          <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120">
            <circle
              cx="60"
              cy="60"
              r="50"
              fill="none"
              strokeWidth="10"
              className="stroke-muted"
            />
            <circle
              cx="60"
              cy="60"
              r="50"
              fill="none"
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={`${percentage * 3.14} ${314 - percentage * 3.14}`}
              className={cn("transition-all duration-700", scoreBgColor(score))}
              style={{ stroke: "currentColor" }}
            />
          </svg>
          {/* Center text */}
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={cn("text-2xl font-bold", scoreColor(score))}>
              {formatScore(score)}
            </span>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">
          {score >= 0.8
            ? "Healthy"
            : score >= 0.5
              ? "Needs attention"
              : "Critical"}
        </p>
      </CardContent>
    </Card>
  );
}
