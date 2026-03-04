import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { useTheme } from "@/hooks/use-theme";

const PAGE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/audit": "Audit Log",
  "/rules": "Rules",
};

/**
 * Root layout with sidebar, header, and routed content area.
 */
export function AppLayout() {
  const { theme, toggleTheme } = useTheme();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  const title = PAGE_TITLES[location.pathname] ?? "SafeGen";

  return (
    <div className="flex min-h-screen">
      <Sidebar
        theme={theme}
        onToggleTheme={toggleTheme}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="flex flex-1 flex-col lg:ml-64">
        <Header title={title} onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
