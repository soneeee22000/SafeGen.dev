import { useState } from "react";
import { PromptInput } from "@/components/playground/PromptInput";
import { ResultPanel } from "@/components/playground/ResultPanel";
import { validatePrompt } from "@/services/api";
import type { RulesCategory, ValidateResponse } from "@/types";

/**
 * Interactive playground for testing the compliance validation pipeline.
 * Owns all page state — no shared hooks.
 */
export function PlaygroundPage() {
  const [prompt, setPrompt] = useState("");
  const [categories, setCategories] = useState<Set<RulesCategory>>(
    new Set(["pii", "bias", "safety"]),
  );
  const [result, setResult] = useState<ValidateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Toggle a category in the set. At least one must remain active.
   */
  function handleToggleCategory(category: RulesCategory) {
    setCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        if (next.size > 1) next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  }

  /**
   * Map selected categories to the backend's rules_category field.
   * All 3 selected = "all". Single = that category. Two = "all" (trade-off).
   */
  function resolveCategory(): RulesCategory {
    if (categories.size === 1) {
      return [...categories][0];
    }
    return "all";
  }

  async function handleSubmit() {
    if (!prompt.trim()) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await validatePrompt({
        prompt: prompt.trim(),
        rules_category: resolveCategory(),
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Validation failed");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <PromptInput
        prompt={prompt}
        onPromptChange={setPrompt}
        categories={categories}
        onToggleCategory={handleToggleCategory}
        onSubmit={handleSubmit}
        isLoading={isLoading}
      />
      <ResultPanel result={result} isLoading={isLoading} error={error} />
    </div>
  );
}
