import { useCallback, useRef, useState } from "react";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ingestRuleFile } from "@/services/api";
import { cn } from "@/lib/utils";

interface RuleUploaderProps {
  onUploadComplete: () => void;
}

/**
 * Drag-and-drop file upload zone for rule documents.
 */
export function RuleUploader({ onUploadComplete }: RuleUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState<{
    text: string;
    isError: boolean;
  } | null>(null);

  const handleUpload = useCallback(
    async (file: File) => {
      setIsUploading(true);
      setMessage(null);
      try {
        const result = await ingestRuleFile(file);
        setMessage({ text: result.message, isError: false });
        onUploadComplete();
      } catch (err) {
        setMessage({
          text: err instanceof Error ? err.message : "Upload failed",
          isError: true,
        });
      } finally {
        setIsUploading(false);
      }
    },
    [onUploadComplete],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleUpload(file);
    },
    [handleUpload],
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleUpload(file);
      e.target.value = "";
    },
    [handleUpload],
  );

  return (
    <Card>
      <CardContent className="pt-6">
        <div
          className={cn(
            "flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors",
            isDragging
              ? "border-primary bg-primary/5"
              : "border-muted-foreground/25",
          )}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
        >
          <Upload className="mb-3 h-8 w-8 text-muted-foreground" />
          <p className="mb-2 text-sm text-muted-foreground">
            Drag and drop a rule document, or
          </p>
          <Button
            variant="outline"
            size="sm"
            disabled={isUploading}
            onClick={() => fileInputRef.current?.click()}
          >
            {isUploading ? "Uploading..." : "Browse files"}
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".md,.txt,.pdf,.docx"
            onChange={handleFileChange}
          />
          <p className="mt-2 text-xs text-muted-foreground">
            Supports .md, .txt, .pdf, .docx
          </p>
        </div>
        {message && (
          <p
            className={cn(
              "mt-3 text-sm",
              message.isError ? "text-destructive" : "text-green-600",
            )}
          >
            {message.text}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
