import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ExamplePrompts } from "./ExamplePrompts";
import type { RulesCategory } from "@/types";
import { Loader2 } from "lucide-react";

const CATEGORY_OPTIONS: { value: RulesCategory; label: string }[] = [
  { value: "pii", label: "PII" },
  { value: "bias", label: "Bias" },
  { value: "safety", label: "Safety" },
];

interface PromptInputProps {
  prompt: string;
  onPromptChange: (value: string) => void;
  categories: Set<RulesCategory>;
  onToggleCategory: (category: RulesCategory) => void;
  onSubmit: () => void;
  isLoading: boolean;
}

/**
 * Prompt input area with example chips, category toggles, and submit button.
 */
export function PromptInput({
  prompt,
  onPromptChange,
  categories,
  onToggleCategory,
  onSubmit,
  isLoading,
}: PromptInputProps) {
  return (
    <div className="space-y-3">
      <Textarea
        placeholder="Enter a prompt to validate..."
        value={prompt}
        onChange={(e) => onPromptChange(e.target.value)}
        rows={4}
        className="resize-none"
      />

      <ExamplePrompts onSelect={onPromptChange} />

      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Layers:</span>
          {CATEGORY_OPTIONS.map((cat) => (
            <Button
              key={cat.value}
              variant={categories.has(cat.value) ? "default" : "outline"}
              size="xs"
              onClick={() => onToggleCategory(cat.value)}
              type="button"
              aria-label={`Toggle ${cat.label}`}
            >
              {cat.label}
            </Button>
          ))}
        </div>

        <Button onClick={onSubmit} disabled={!prompt.trim() || isLoading}>
          {isLoading && <Loader2 className="animate-spin" />}
          Validate
        </Button>
      </div>
    </div>
  );
}
