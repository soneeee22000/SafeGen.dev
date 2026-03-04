import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { AuditStatus } from "@/types";

interface AuditFiltersProps {
  dateFrom: string;
  dateTo: string;
  status: AuditStatus;
  onDateFromChange: (value: string) => void;
  onDateToChange: (value: string) => void;
  onStatusChange: (value: AuditStatus) => void;
}

/**
 * Filter controls for audit log: date range + status dropdown.
 */
export function AuditFilters({
  dateFrom,
  dateTo,
  status,
  onDateFromChange,
  onDateToChange,
  onStatusChange,
}: AuditFiltersProps) {
  return (
    <div className="flex flex-wrap items-end gap-4">
      <div className="space-y-1">
        <label className="text-sm font-medium text-muted-foreground">
          From
        </label>
        <Input
          type="date"
          value={dateFrom}
          onChange={(e) => onDateFromChange(e.target.value)}
          className="w-40"
        />
      </div>
      <div className="space-y-1">
        <label className="text-sm font-medium text-muted-foreground">To</label>
        <Input
          type="date"
          value={dateTo}
          onChange={(e) => onDateToChange(e.target.value)}
          className="w-40"
        />
      </div>
      <div className="space-y-1">
        <label className="text-sm font-medium text-muted-foreground">
          Status
        </label>
        <Select
          value={status}
          onValueChange={(v) => onStatusChange(v as AuditStatus)}
        >
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="passed">Passed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
