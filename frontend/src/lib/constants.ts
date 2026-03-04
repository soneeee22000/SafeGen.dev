import type { LucideIcon } from "lucide-react";
import { LayoutDashboard, ScrollText, BookOpen } from "lucide-react";

/** Default page size for audit records. */
export const AUDIT_PAGE_SIZE = 20;

/** Auto-refresh interval for dashboard (ms). */
export const DASHBOARD_REFRESH_MS = 60_000;

/** Compliance score thresholds for color coding. */
export const SCORE_THRESHOLDS = {
  GOOD: 0.8,
  FAIR: 0.5,
} as const;

/** Chart color palette (no gradients). */
export const CHART_COLORS = {
  passed: "var(--chart-2)",
  failed: "var(--chart-1)",
  total: "var(--chart-3)",
  pii: "var(--chart-1)",
  bias: "var(--chart-4)",
  safety: "var(--chart-5)",
  compliance: "var(--chart-2)",
} as const;

/** Severity badge variants. */
export const SEVERITY_VARIANT: Record<
  string,
  "default" | "secondary" | "destructive" | "outline"
> = {
  critical: "destructive",
  warning: "secondary",
  info: "outline",
};

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

/** Sidebar navigation items. */
export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Audit Log", href: "/audit", icon: ScrollText },
  { label: "Rules", href: "/rules", icon: BookOpen },
];
