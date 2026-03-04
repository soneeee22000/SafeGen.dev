import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";

interface HeaderProps {
  title: string;
  onMenuClick: () => void;
}

/**
 * Page header with mobile hamburger and page title.
 */
export function Header({ title, onMenuClick }: HeaderProps) {
  return (
    <header className="flex h-16 items-center gap-4 border-b border-border px-6">
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={onMenuClick}
      >
        <Menu className="h-5 w-5" />
      </Button>
      <h1 className="text-xl font-semibold">{title}</h1>
    </header>
  );
}
