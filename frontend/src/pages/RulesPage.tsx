import { RuleUploader } from "@/components/rules/RuleUploader";
import { RuleList } from "@/components/rules/RuleList";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/use-api";
import { fetchRules } from "@/services/api";

/**
 * Rules page with upload zone and ingested rules list.
 */
export function RulesPage() {
  const { data: rules, isLoading, error, refetch } = useApi(() => fetchRules());

  return (
    <div className="space-y-6">
      <RuleUploader onUploadComplete={refetch} />

      {error && (
        <p className="text-destructive">
          Failed to load rules: {error.message}
        </p>
      )}

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : rules ? (
        <RuleList rules={rules} />
      ) : null}
    </div>
  );
}
