import { SCORE_THRESHOLDS } from "./constants";

/**
 * Format compliance score as percentage string.
 */
export function formatScore(score: number): string {
  return `${(score * 100).toFixed(1)}%`;
}

/**
 * Format duration in ms to human-readable string.
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

/**
 * Format ISO date string to locale display.
 */
export function formatDate(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Format ISO date string to locale display with time.
 */
export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Return how many days ago a date was.
 */
export function daysAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  return `${days}d ago`;
}

/**
 * Return Tailwind text color class based on score threshold.
 */
export function scoreColor(score: number): string {
  if (score >= SCORE_THRESHOLDS.GOOD)
    return "text-green-600 dark:text-green-400";
  if (score >= SCORE_THRESHOLDS.FAIR)
    return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

/**
 * Return Tailwind bg color class based on score threshold.
 */
export function scoreBgColor(score: number): string {
  if (score >= SCORE_THRESHOLDS.GOOD) return "bg-green-600";
  if (score >= SCORE_THRESHOLDS.FAIR) return "bg-amber-500";
  return "bg-red-600";
}
