// Canonical two-level taxonomy — mirrors packages/core/taxonomy.py.
// Keep the two in sync.

export const ROLES = [
  "solver",
  "protocol",
  "aggregator",
  "infra",
  "interface",
  "tool",
] as const;

export const INTENT_TYPES = [
  "swap",
  "bridge",
  "derivatives",
  "lending",
  "yield",
  "liquid_staking",
  "orderflow_auction",
  "account_abstraction",
  "mev",
  "privacy",
  "launchpad",
  "general",
] as const;

export type Role = (typeof ROLES)[number];
export type IntentType = (typeof INTENT_TYPES)[number];

const INTENT_LABEL: Record<string, string> = {
  swap: "DEX",
  bridge: "Bridge",
  derivatives: "Derivatives",
  lending: "Lending",
  yield: "Yield",
  liquid_staking: "Liquid Staking",
  orderflow_auction: "Order Flow",
  account_abstraction: "Account Abstraction",
  mev: "MEV",
  privacy: "Privacy",
  launchpad: "Launchpad",
  general: "",
};

const ROLE_LABEL: Record<string, string> = {
  solver: "Solver",
  protocol: "",
  aggregator: "Aggregator",
  infra: "Infra",
  interface: "Interface",
  tool: "Tool",
};

export function displayLabel(role?: string | null, intentType?: string | null): string {
  const r = role ? ROLE_LABEL[role] ?? role : "";
  const i = intentType ? INTENT_LABEL[intentType] ?? intentType : "";
  if (r && i) return `${i} ${r}`.trim();
  return (i || r || "Other").trim();
}

// Buckets used on the overview page's "Top to check today" grid.
// First-match-wins assignment keeps a project from double-counting.
export const TOP_BUCKETS: { label: string; match: (p: { role?: string; intent_type?: string; category?: string }) => boolean }[] = [
  { label: "Solvers", match: (p) => p.role === "solver" || (p.role === "infra" && p.intent_type === "swap") || /solver/i.test(p.category || "") },
  { label: "Aggregators", match: (p) => p.role === "aggregator" },
  { label: "Bridges", match: (p) => p.intent_type === "bridge" },
  { label: "Derivatives", match: (p) => p.intent_type === "derivatives" },
];
