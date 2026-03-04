import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { FlagList } from "./FlagList";
import { formatScore, scoreColor } from "@/lib/format";
import type { ValidateResponse } from "@/types";

interface ResultPanelProps {
  result: ValidateResponse | null;
  isLoading: boolean;
  error: string | null;
}

/**
 * Displays validation results: score summary, LLM response, and flags.
 */
export function ResultPanel({ result, isLoading, error }: ResultPanelProps) {
  if (isLoading) {
    return (
      <div className="space-y-4" data-testid="result-skeleton">
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-32 rounded-xl" />
      </div>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive">
        <CardContent>
          <p className="text-sm text-destructive">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!result) {
    return (
      <div className="flex items-center justify-center rounded-xl border border-dashed p-12 text-muted-foreground">
        Enter a prompt and click Validate to test compliance.
      </div>
    );
  }

  const compliance = result.compliance;
  const passed = compliance?.passed ?? true;
  const score = compliance?.score ?? 1;
  const flags = compliance?.flags ?? [];
  const layersRun = compliance?.layers_run ?? [];

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-xs text-muted-foreground">
              Score
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold ${scoreColor(score)}`}>
              {formatScore(score)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-xs text-muted-foreground">
              Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant={passed ? "secondary" : "destructive"}>
              {passed ? "Passed" : "Failed"}
            </Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-xs text-muted-foreground">
              Flags
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{flags.length}</p>
          </CardContent>
        </Card>
      </div>

      {/* Response */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Response</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="whitespace-pre-wrap text-sm">{result.response}</p>
        </CardContent>
      </Card>

      {/* Flags */}
      {flags.length > 0 && (
        <Card>
          <CardContent>
            <FlagList flags={flags} />
          </CardContent>
        </Card>
      )}

      {/* Layers run */}
      {layersRun.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Layers run: {layersRun.join(", ")}
        </p>
      )}
    </div>
  );
}
