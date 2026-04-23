import { supabase } from "./supabase";

// Replaces the old FastAPI client. All reads come directly from Supabase
// (public tables protected by RLS — anon key only allows SELECT). Writes that
// the old API supported (trigger scan, mark discovery reviewed) are either
// dropped or routed through server-side Supabase calls.

export interface Stats {
  projects: number;
  mentions: number;
  active: number;
  total_raised: number;
  unreviewed: number;
}

export interface Project {
  id: number;
  name: string;
  slug?: string;
  description?: string;
  website?: string;
  chains?: string[] | string | null;
  category?: string;
  status?: string;
  token_symbol?: string;
  coingecko_id?: string;
  defillama_slug?: string;
  github_org?: string;
  twitter_handle?: string;
  first_seen?: string;
  last_updated?: string;
  relevance_score?: number;
  is_manually_tracked?: number;
  funding_total?: number;
}

export interface Mention {
  id: number;
  project_id?: number;
  source?: string;
  title?: string;
  url?: string;
  author?: string;
  content_snippet?: string;
  sentiment_score?: number;
  upvotes?: number;
  published_at?: string;
  discovered_at?: string;
}

export interface GithubMetric {
  id: number;
  project_id?: number;
  repo_url?: string;
  stars?: number;
  forks?: number;
  open_issues?: number;
  contributors_count?: number;
  last_commit_at?: string;
  commits_30d?: number;
  snapshot_date?: string;
}

export interface Discovery {
  id: number;
  entity_type?: string;
  entity_id?: number;
  discovered_at?: string;
  reviewed?: number;
  name?: string;
  detail?: string;
}

export interface ScanLogEntry {
  id: number;
  scanner_name?: string;
  started_at?: string;
  finished_at?: string;
  status?: string;
  items_found?: number;
  error_message?: string;
}

// ---- Stats -----------------------------------------------------------------

async function overviewStats(): Promise<Stats> {
  const [
    { count: projects },
    { count: mentions },
    { count: active },
    { count: unreviewed },
    { data: fundingRows },
  ] = await Promise.all([
    supabase.from("projects").select("*", { count: "exact", head: true }),
    supabase.from("social_mentions").select("*", { count: "exact", head: true }),
    supabase
      .from("projects")
      .select("*", { count: "exact", head: true })
      .eq("status", "active"),
    supabase
      .from("discoveries")
      .select("*", { count: "exact", head: true })
      .eq("reviewed", 0),
    supabase.from("funding_rounds").select("amount_usd"),
  ]);

  const total_raised = (fundingRows ?? []).reduce(
    (s: number, r: { amount_usd: number | null }) => s + (r.amount_usd ?? 0),
    0
  );

  return {
    projects: projects ?? 0,
    mentions: mentions ?? 0,
    active: active ?? 0,
    total_raised,
    unreviewed: unreviewed ?? 0,
  };
}

// ---- Projects --------------------------------------------------------------

async function projects(filters?: Record<string, string>): Promise<Project[]> {
  let q = supabase.from("projects").select("*").order("relevance_score", { ascending: false });
  if (filters?.category) q = q.eq("category", filters.category);
  if (filters?.status) q = q.eq("status", filters.status);
  if (filters?.search) {
    const s = `%${filters.search}%`;
    q = q.or(`name.ilike.${s},description.ilike.${s},category.ilike.${s}`);
  }
  if (filters?.chain) {
    // chains is jsonb — cs = contains
    q = q.contains("chains", [filters.chain]);
  }
  const { data, error } = await q;
  if (error) throw error;
  return (data ?? []) as Project[];
}

async function project(id: number): Promise<Project | null> {
  const { data, error } = await supabase
    .from("projects")
    .select("*")
    .eq("id", id)
    .maybeSingle();
  if (error) throw error;
  return data as Project | null;
}

// ---- Mentions --------------------------------------------------------------

async function mentions(filters?: Record<string, string>): Promise<Mention[]> {
  let q = supabase
    .from("social_mentions")
    .select("*")
    .order("discovered_at", { ascending: false })
    .limit(Number(filters?.limit ?? 200));
  if (filters?.source) q = q.eq("source", filters.source);
  if (filters?.search) {
    const s = `%${filters.search}%`;
    q = q.or(`title.ilike.${s},content_snippet.ilike.${s}`);
  }
  const { data, error } = await q;
  if (error) throw error;
  return (data ?? []) as Mention[];
}

async function mentionStats() {
  const [{ count: total }, { data: bySourceRows }] = await Promise.all([
    supabase.from("social_mentions").select("*", { count: "exact", head: true }),
    supabase.from("social_mentions").select("source"),
  ]);
  const by_source: Record<string, number> = {};
  for (const r of bySourceRows ?? []) {
    if (r.source) by_source[r.source] = (by_source[r.source] ?? 0) + 1;
  }
  return { total: total ?? 0, by_source, this_week: 0 };
}

// ---- GitHub metrics --------------------------------------------------------

async function github(): Promise<GithubMetric[]> {
  const { data, error } = await supabase
    .from("github_metrics")
    .select("*")
    .order("snapshot_date", { ascending: false });
  if (error) throw error;
  return (data ?? []) as GithubMetric[];
}

// ---- Discoveries -----------------------------------------------------------

async function discoveries(filters?: Record<string, string>): Promise<Discovery[]> {
  let q = supabase
    .from("discoveries_enriched")
    .select("*")
    .order("discovered_at", { ascending: false })
    .limit(Number(filters?.limit ?? 500));
  if (filters?.reviewed !== undefined) {
    q = q.eq("reviewed", Number(filters.reviewed));
  }
  if (filters?.type) q = q.eq("entity_type", filters.type);
  const { data, error } = await q;
  if (error) throw error;
  return (data ?? []) as Discovery[];
}

async function reviewDiscovery(_id: number) {
  // anon key cannot write — surface a clear no-op. If/when we need a writable
  // review flow, add a Next.js route handler that uses the service_role key.
  if (typeof window !== "undefined") {
    console.warn("reviewDiscovery: read-only in this deploy.");
  }
}

// ---- Solvers (static fixture) ---------------------------------------------

async function solvers(filters?: Record<string, string>) {
  // The old /api/solvers served a hand-maintained list out of
  // apps/api/solvers_data.py. Ship the same list as a static JSON import so
  // the Vercel build has no backend dependency for it.
  const raw = (await import("../data/solvers.json")).default as Array<
    Record<string, unknown> & {
      name: string;
      type: string;
      description: string;
      protocols: string[];
      chains: string[];
    }
  >;
  let results = raw;
  if (filters?.type) results = results.filter((s) => s.type === filters.type.toLowerCase());
  if (filters?.search) {
    const q = filters.search.toLowerCase();
    results = results.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.protocols.some((p) => p.toLowerCase().includes(q))
    );
  }
  if (filters?.chain) {
    const c = filters.chain.toLowerCase();
    results = results.filter((s) => s.chains.some((x) => x.toLowerCase().includes(c)));
  }
  if (filters?.protocol) {
    const p = filters.protocol.toLowerCase();
    results = results.filter((s) => s.protocols.some((x) => x.toLowerCase().includes(p)));
  }
  return results;
}

// ---- Scan log --------------------------------------------------------------

async function scanLog(): Promise<ScanLogEntry[]> {
  const { data, error } = await supabase
    .from("scan_log")
    .select("*")
    .order("started_at", { ascending: false })
    .limit(20);
  if (error) throw error;
  return (data ?? []) as ScanLogEntry[];
}

// ---- Last scan summary -----------------------------------------------------
// Returns the most recent scan_log entry (any scanner) plus a bucketed count of
// discoveries added since that scan started. Powers the "What's new" grid.

export interface LastScanSummary {
  latestScanAt: string | null;
  newProjects: Discovery[];
  newMentions: Discovery[];
  newFunding: Discovery[];
}

async function lastScanSummary(): Promise<LastScanSummary> {
  const { data: scanRows } = await supabase
    .from("scan_log")
    .select("started_at")
    .order("started_at", { ascending: false })
    .limit(1);
  const latestScanAt = scanRows?.[0]?.started_at ?? null;

  // Fallback: if no scan_log row exists, look at discoveries from the last 24h
  // so the section still shows something useful.
  const cutoff =
    latestScanAt ?? new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();

  const { data, error } = await supabase
    .from("discoveries_enriched")
    .select("*")
    .gte("discovered_at", cutoff)
    .order("discovered_at", { ascending: false })
    .limit(200);
  if (error) throw error;

  const rows = (data ?? []) as Discovery[];
  return {
    latestScanAt,
    newProjects: rows.filter((r) => r.entity_type === "project"),
    newMentions: rows.filter((r) => r.entity_type === "social_mention"),
    newFunding: rows.filter((r) => r.entity_type === "funding_round"),
  };
}

async function scan() {
  // Manual scan trigger is GitHub Actions only — exposed as a no-op here.
  console.warn(
    "scan(): trigger via GitHub Actions → https://github.com/MrudulChauhan/Intent-Tracker/actions/workflows/scan.yml"
  );
}

// ---- Graph -----------------------------------------------------------------

export interface GraphNode {
  id: number;
  entity_type: string;
  name: string;
  external_id?: number;
  slug?: string;
  degree?: number;
}

export interface GraphEdge {
  id: number;
  from_id: number;
  to_id: number;
  relationship_type: string;
  confidence: number;
  source_url?: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

const GRAPH_DEFAULT_LIMIT = 200;

async function graph(limit: number = GRAPH_DEFAULT_LIMIT): Promise<GraphResponse> {
  // Top N nodes by degree, then fetch all edges between those nodes so the
  // rendered sub-graph is self-consistent.
  const { data: topNodes, error: topErr } = await supabase
    .from("entity_degree")
    .select("id,entity_type,external_id,name,slug,degree")
    .order("degree", { ascending: false })
    .limit(limit);
  if (topErr) throw topErr;

  const nodes = (topNodes ?? []) as GraphNode[];
  if (nodes.length === 0) return { nodes: [], edges: [] };

  const ids = nodes.map((n) => n.id);
  const { data: edgeRows, error: edgeErr } = await supabase
    .from("relationships")
    .select("id,from_id,to_id,relationship_type,confidence,source_url")
    .in("from_id", ids)
    .in("to_id", ids);
  if (edgeErr) throw edgeErr;

  return {
    nodes,
    edges: (edgeRows ?? []) as GraphEdge[],
  };
}

async function graphForProject(projectId: number): Promise<GraphResponse> {
  // Find the entity row for this project (entity_type='project').
  const { data: root } = await supabase
    .from("entities")
    .select("id,entity_type,external_id,name,slug")
    .eq("entity_type", "project")
    .eq("external_id", projectId)
    .maybeSingle();
  if (!root) return { nodes: [], edges: [] };

  const rootId = (root as { id: number }).id;
  const { data: edgeRows } = await supabase
    .from("relationships")
    .select("id,from_id,to_id,relationship_type,confidence,source_url")
    .or(`from_id.eq.${rootId},to_id.eq.${rootId}`);

  const edges = (edgeRows ?? []) as GraphEdge[];
  const neighborIds = new Set<number>([rootId]);
  for (const e of edges) {
    neighborIds.add(e.from_id);
    neighborIds.add(e.to_id);
  }

  if (neighborIds.size === 0) return { nodes: [root as GraphNode], edges: [] };
  const { data: nodeRows } = await supabase
    .from("entities")
    .select("id,entity_type,external_id,name,slug")
    .in("id", Array.from(neighborIds));

  return {
    nodes: (nodeRows ?? []) as GraphNode[],
    edges,
  };
}

export const api = {
  stats: overviewStats,
  projects,
  project,
  mentions,
  mentionStats,
  github,
  discoveries,
  reviewDiscovery,
  solvers,
  scanLog,
  lastScanSummary,
  scan,
  graph,
  graphForProject,
};

// Back-compat for callers that used the raw fetchApi helper
export async function fetchApi(_path: string, _opts?: RequestInit) {
  throw new Error(
    "fetchApi is deprecated — use api.* methods backed by Supabase."
  );
}
