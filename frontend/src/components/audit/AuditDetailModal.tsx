import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { AuditRecord } from "@/types";
import { formatDateTime, formatDuration, formatScore } from "@/lib/format";
import { SEVERITY_VARIANT } from "@/lib/constants";

interface AuditDetailModalProps {
  record: AuditRecord | null;
  onClose: () => void;
}

/**
 * Modal showing full audit record details including flag list.
 */
export function AuditDetailModal({ record, onClose }: AuditDetailModalProps) {
  if (!record) return null;

  return (
    <Dialog open={!!record} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[80vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Request {record.request_id.slice(0, 8)}
            <Badge
              variant={record.compliance_passed ? "secondary" : "destructive"}
            >
              {record.compliance_passed ? "Passed" : "Failed"}
            </Badge>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Metadata */}
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-muted-foreground">Time: </span>
              {formatDateTime(record.timestamp)}
            </div>
            <div>
              <span className="text-muted-foreground">Duration: </span>
              {formatDuration(record.duration_ms)}
            </div>
            <div>
              <span className="text-muted-foreground">Score: </span>
              {formatScore(record.compliance_score)}
            </div>
            <div>
              <span className="text-muted-foreground">Model: </span>
              {record.model}
            </div>
            <div>
              <span className="text-muted-foreground">Category: </span>
              {record.rules_category}
            </div>
            <div>
              <span className="text-muted-foreground">Layers: </span>
              {record.layers_run.join(", ") || "none"}
            </div>
          </div>

          <Separator />

          {/* Prompt */}
          <div>
            <h4 className="mb-1 text-sm font-medium">Prompt</h4>
            <p className="rounded-md bg-muted p-3 text-sm">{record.prompt}</p>
          </div>

          {/* Response */}
          <div>
            <h4 className="mb-1 text-sm font-medium">Response</h4>
            <p className="rounded-md bg-muted p-3 text-sm">
              {record.response_content}
            </p>
          </div>

          {/* Flags */}
          {record.compliance_flags.length > 0 && (
            <div>
              <h4 className="mb-2 text-sm font-medium">
                Flags ({record.compliance_flags.length})
              </h4>
              <div className="space-y-2">
                {record.compliance_flags.map((flag, i) => (
                  <div key={i} className="rounded-md border p-3">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={
                          SEVERITY_VARIANT[flag.severity as string] ?? "outline"
                        }
                      >
                        {flag.severity as string}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {flag.layer as string}
                      </span>
                    </div>
                    <p className="mt-1 text-sm">{flag.message as string}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
