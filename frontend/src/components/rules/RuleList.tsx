import { FileText } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { RuleDocument } from "@/types";

interface RuleListProps {
  rules: RuleDocument[];
}

/**
 * Card grid of ingested rule documents.
 */
export function RuleList({ rules }: RuleListProps) {
  if (rules.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-muted-foreground">
        No rules ingested yet. Upload a document to get started.
      </p>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {rules.map((rule) => (
        <Card key={rule.filename}>
          <CardHeader className="flex flex-row items-center gap-3 pb-2">
            <FileText className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-sm font-medium">
              {rule.filename}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant="secondary">{rule.chunk_count} chunks</Badge>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
