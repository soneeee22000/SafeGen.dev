import { useCallback, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { AuditFilters } from "@/components/audit/AuditFilters";
import { AuditTable } from "@/components/audit/AuditTable";
import { AuditPagination } from "@/components/audit/AuditPagination";
import { AuditDetailModal } from "@/components/audit/AuditDetailModal";
import { useApi } from "@/hooks/use-api";
import { fetchAuditRecords } from "@/services/api";
import { AUDIT_PAGE_SIZE } from "@/lib/constants";
import type { AuditRecord, AuditStatus } from "@/types";

/**
 * Audit log page with filters, table, pagination, and detail modal.
 */
export function AuditPage() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [status, setStatus] = useState<AuditStatus>("all");
  const [offset, setOffset] = useState(0);
  const [selectedRecord, setSelectedRecord] = useState<AuditRecord | null>(
    null,
  );

  const { data, isLoading, error } = useApi(
    () =>
      fetchAuditRecords({
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        status,
        limit: AUDIT_PAGE_SIZE,
        offset,
      }),
    [dateFrom, dateTo, status, offset],
  );

  const handleStatusChange = useCallback((value: AuditStatus) => {
    setStatus(value);
    setOffset(0);
  }, []);

  const handleDateFromChange = useCallback((value: string) => {
    setDateFrom(value);
    setOffset(0);
  }, []);

  const handleDateToChange = useCallback((value: string) => {
    setDateTo(value);
    setOffset(0);
  }, []);

  return (
    <div className="space-y-6">
      <AuditFilters
        dateFrom={dateFrom}
        dateTo={dateTo}
        status={status}
        onDateFromChange={handleDateFromChange}
        onDateToChange={handleDateToChange}
        onStatusChange={handleStatusChange}
      />

      {error && (
        <p className="text-destructive">
          Failed to load audit records: {error.message}
        </p>
      )}

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : data ? (
        <>
          <AuditTable records={data.records} onRowClick={setSelectedRecord} />
          <AuditPagination
            offset={offset}
            limit={data.limit}
            total={data.total}
            onPrev={() => setOffset((o) => Math.max(0, o - AUDIT_PAGE_SIZE))}
            onNext={() => setOffset((o) => o + AUDIT_PAGE_SIZE)}
          />
        </>
      ) : null}

      <AuditDetailModal
        record={selectedRecord}
        onClose={() => setSelectedRecord(null)}
      />
    </div>
  );
}
