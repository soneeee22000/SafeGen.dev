# SafeGen — Frontend Dashboard

React/TypeScript monitoring dashboard for the SafeGen compliance API.

## Stack

- **Vite** — build tooling + dev server with API proxy
- **React 19** + **TypeScript** (strict mode)
- **Tailwind CSS v4** + **shadcn/ui** (Radix + Tailwind components)
- **Recharts** — area/bar charts for metrics visualization
- **lucide-react** — icon library
- **vitest** + **@testing-library/react** — 41 tests

## Pages

| Route    | Page          | Description                                           |
| -------- | ------------- | ----------------------------------------------------- |
| `/`      | DashboardPage | 4 KPI cards, trend chart, flag breakdown, score gauge |
| `/audit` | AuditPage     | Filterable table, pagination, detail modal            |
| `/rules` | RulesPage     | Drag-and-drop upload, ingested rule cards             |

## Development

```bash
npm install
npm run dev          # http://localhost:5173 (proxies /api to localhost:7071)
npm run test:run     # Run tests once
npm run test         # Watch mode
npm run build        # Production build
npm run lint         # ESLint
```

The dev server proxies `/api/*` requests to `http://localhost:7071` (Azure Functions local runtime). Start the backend first:

```bash
cd ../backend && func start
```

## Project Structure

```
src/
├── types/index.ts              # TypeScript interfaces (1:1 backend Pydantic mirror)
├── services/api.ts             # Typed API client (fetchMetrics, fetchAuditRecords, etc.)
├── hooks/
│   ├── use-api.ts              # Generic useApi<T> data-fetching hook
│   └── use-theme.ts            # Dark mode toggle (localStorage + class strategy)
├── lib/
│   ├── utils.ts                # cn() class merge helper (shadcn)
│   ├── constants.ts            # Page sizes, thresholds, chart colors, nav items
│   └── format.ts               # formatScore, formatDuration, formatDate, scoreColor
├── components/
│   ├── ui/                     # shadcn: button, card, badge, table, dialog, etc.
│   ├── layout/                 # Sidebar, Header, AppLayout (responsive)
│   ├── dashboard/              # KpiCard, TrendChart, FlagBreakdownChart, ScoreGauge
│   ├── audit/                  # AuditFilters, AuditTable, AuditPagination, AuditDetailModal
│   └── rules/                  # RuleUploader, RuleList
├── pages/                      # DashboardPage, AuditPage, RulesPage
├── test/
│   ├── setup.ts                # jest-dom matchers
│   └── mocks.ts                # Factory functions for test data
├── App.tsx                     # Router + route definitions
├── main.tsx                    # ReactDOM entry
└── index.css                   # Tailwind v4 + light/dark design tokens
```
