import { Badge } from "@/components/ui/badge";
import { SEVERITY_VARIANT } from "@/lib/constants";
import type { ValidationFlag } from "@/types";

interface FlagListProps {
  flags: ValidationFlag[];
}

/**
 * Renders a list of compliance flags with severity badges.
 */
export function FlagList({ flags }: FlagListProps) {
  if (flags.length === 0) return null;

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium">Flags ({flags.length})</h4>
      {flags.map((flag, i) => (
        <div key={i} className="rounded-md border p-3">
          <div className="flex items-center gap-2">
            <Badge variant={SEVERITY_VARIANT[flag.severity] ?? "outline"}>
              {flag.severity}
            </Badge>
            <span className="text-xs text-muted-foreground">{flag.layer}</span>
          </div>
          <p className="mt-1 text-sm">{flag.message}</p>
        </div>
      ))}
    </div>
  );
}
