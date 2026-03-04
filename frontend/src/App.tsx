import { BrowserRouter, Route, Routes } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppLayout } from "@/components/layout/AppLayout";
import { DashboardPage } from "@/pages/DashboardPage";
import { AuditPage } from "@/pages/AuditPage";
import { RulesPage } from "@/pages/RulesPage";
import { PlaygroundPage } from "@/pages/PlaygroundPage";

/**
 * Root application component with routing.
 */
export default function App() {
  return (
    <BrowserRouter>
      <TooltipProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/audit" element={<AuditPage />} />
            <Route path="/rules" element={<RulesPage />} />
            <Route path="/playground" element={<PlaygroundPage />} />
          </Route>
        </Routes>
      </TooltipProvider>
    </BrowserRouter>
  );
}
