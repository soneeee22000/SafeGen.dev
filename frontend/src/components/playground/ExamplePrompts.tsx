import { Button } from "@/components/ui/button";
import { EXAMPLE_PROMPTS } from "@/lib/constants";

interface ExamplePromptsProps {
  onSelect: (prompt: string) => void;
}

/**
 * Clickable chips that fill the textarea with curated example prompts.
 */
export function ExamplePrompts({ onSelect }: ExamplePromptsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <span className="text-xs text-muted-foreground self-center">Try:</span>
      {EXAMPLE_PROMPTS.map((example) => (
        <Button
          key={example.label}
          variant="outline"
          size="xs"
          onClick={() => onSelect(example.prompt)}
          type="button"
        >
          {example.label}
        </Button>
      ))}
    </div>
  );
}
