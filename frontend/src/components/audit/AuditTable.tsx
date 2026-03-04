import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import type { AuditRecord } from "@/types";
import { formatDateTime, formatDuration, formatScore } from "@/lib/format";
import { scoreColor } from "@/lib/format";
import { cn } from "@/lib/utils";

interface AuditTableProps {
  records: AuditRecord[];
  onRowClick: (record: AuditRecord) => void;
}

/**
 * Table of audit records with clickable rows.
 */
export function AuditTable({ records, onRowClick }: AuditTableProps) {
  if (records.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-muted-foreground">
        No audit records found.
      </p>
    );
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Time</TableHead>
            <TableHead>Prompt</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Score</TableHead>
            <TableHead>Duration</TableHead>
            <TableHead>Flags</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {records.map((record) => (
            <TableRow
              key={record.request_id}
              className="cursor-pointer"
              onClick={() => onRowClick(record)}
            >
              <TableCell className="whitespace-nowrap text-sm">
                {formatDateTime(record.timestamp)}
              </TableCell>
              <TableCell className="max-w-xs truncate text-sm">
                {record.prompt}
              </TableCell>
              <TableCell>
                <Badge
                  variant={
                    record.compliance_passed ? "secondary" : "destructive"
                  }
                >
                  {record.compliance_passed ? "Passed" : "Failed"}
                </Badge>
              </TableCell>
              <TableCell
                className={cn(
                  "font-medium",
                  scoreColor(record.compliance_score),
                )}
              >
                {formatScore(record.compliance_score)}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {formatDuration(record.duration_ms)}
              </TableCell>
              <TableCell className="text-sm">
                {record.compliance_flags.length}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
