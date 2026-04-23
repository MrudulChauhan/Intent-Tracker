"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { api, type GraphNode, type GraphEdge, type Project } from "@/lib/api";
import { ProjectModal } from "@/components/project-modal";

// react-force-graph-2d uses <canvas> so we must disable SSR.
// Cast through `any` because the library's default node generic lacks our
// custom fields (entity_type, name) and typing the generics here adds noise
// without catching real bugs — this page is the only consumer.
const ForceGraph2D: any = dynamic(
  () => import("react-force-graph-2d").then((m) => m.default),
  { ssr: false }
);

// Entity-type → color + legend label
const TYPE_STYLE: Record<string, { color: string; label: string }> = {
  project:     { color: "#FF6B2C", label: "Project" },
  investor:    { color: "#3B82F6", label: "Investor" },
  integration: { color: "#10B981", label: "Integration" },
  person:      { color: "#9CA3AF", label: "Person" },
};

const DEFAULT_COLOR = "#9CA3AF";

type ForceNode = GraphNode & {
  degree: number;
  x?: number;
  y?: number;
};

type ForceLink = {
  source: number | ForceNode;
  target: number | ForceNode;
  relationship_type: string;
  confidence: number;
  id: number;
};

export default function GraphPage() {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [enabledTypes, setEnabledTypes] = useState<Record<string, boolean>>({
    project: true,
    investor: true,
    integration: true,
    person: true,
  });

  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await api.graph();
        if (cancelled) return;
        setNodes(res.nodes);
        setEdges(res.edges);
      } catch (e) {
        console.error(e);
        if (!cancelled) setError("Failed to load graph data.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const resize = () => {
      const rect = el.getBoundingClientRect();
      setSize({
        width: Math.max(320, Math.floor(rect.width)),
        height: Math.max(400, Math.floor(window.innerHeight - rect.top - 40)),
      });
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    window.addEventListener("resize", resize);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", resize);
    };
  }, []);

  // Compute degree once per edge set, then bake it into the node payload so
  // force-graph can size by it.
  const degreeById = useMemo(() => {
    const d = new Map<number, number>();
    for (const e of edges) {
      d.set(e.from_id, (d.get(e.from_id) ?? 0) + 1);
      d.set(e.to_id, (d.get(e.to_id) ?? 0) + 1);
    }
    return d;
  }, [edges]);

  const graphData = useMemo(() => {
    const activeNodes: ForceNode[] = nodes
      .filter((n) => enabledTypes[n.entity_type] !== false)
      .map((n) => ({ ...n, degree: degreeById.get(n.id) ?? 0 }));
    const activeIds = new Set(activeNodes.map((n) => n.id));
    const activeLinks: ForceLink[] = edges
      .filter((e) => activeIds.has(e.from_id) && activeIds.has(e.to_id))
      .map((e) => ({
        source: e.from_id,
        target: e.to_id,
        relationship_type: e.relationship_type,
        confidence: e.confidence,
        id: e.id,
      }));
    return { nodes: activeNodes, links: activeLinks };
  }, [nodes, edges, enabledTypes, degreeById]);

  async function handleNodeClick(node: ForceNode) {
    if (node.entity_type === "project" && node.external_id != null) {
      try {
        const p = await api.project(node.external_id);
        if (p) setSelectedProject(p);
      } catch (e) {
        console.error(e);
      }
    }
  }

  const counts = useMemo(() => {
    const out: Record<string, number> = {
      project: 0, investor: 0, integration: 0, person: 0,
    };
    for (const n of nodes) {
      if (n.entity_type in out) out[n.entity_type] += 1;
    }
    return out;
  }, [nodes]);

  return (
    <div className="space-y-4 pt-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Relationship graph</h1>
          <p className="text-xs text-gray-500 mt-1">
            Top {nodes.length} entities by degree ·{" "}
            {edges.length} relationships
          </p>
        </div>
      </div>

      {/* Filter strip */}
      <div className="flex flex-wrap items-center gap-2">
        {Object.entries(TYPE_STYLE).map(([key, style]) => {
          const active = enabledTypes[key] !== false;
          return (
            <button
              key={key}
              onClick={() =>
                setEnabledTypes((prev) => ({ ...prev, [key]: !active }))
              }
              className={`text-xs px-3 py-1.5 rounded-full transition-colors duration-150 border flex items-center gap-2 ${
                active
                  ? "bg-white text-gray-900 border-gray-300"
                  : "bg-gray-50 text-gray-400 border-gray-200"
              }`}
              aria-pressed={active}
            >
              <span
                className="inline-block w-2.5 h-2.5 rounded-full"
                style={{
                  backgroundColor: active ? style.color : "#D1D5DB",
                }}
              />
              {style.label}
              <span className="text-gray-400 tabular-nums">
                {counts[key] ?? 0}
              </span>
            </button>
          );
        })}
      </div>

      <div
        ref={containerRef}
        className="relative bg-white border border-gray-200 rounded-xl overflow-hidden"
        style={{ height: size.height }}
      >
        {/* Legend — absolutely positioned over the canvas */}
        <div className="absolute top-3 right-3 z-10 bg-white/90 backdrop-blur rounded-lg border border-gray-200 px-3 py-2 text-xs space-y-1 shadow-sm">
          <div className="font-semibold text-gray-700 mb-1">Legend</div>
          {Object.entries(TYPE_STYLE).map(([key, style]) => (
            <div key={key} className="flex items-center gap-2 text-gray-600">
              <span
                className="inline-block w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: style.color }}
              />
              {style.label}
            </div>
          ))}
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-full text-sm text-gray-400">
            Loading graph…
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full text-sm text-red-500">
            {error}
          </div>
        ) : graphData.nodes.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-sm text-gray-400 gap-2">
            <div className="font-medium text-gray-600">No relationships yet</div>
            <div className="text-xs">
              Run the migration and let the funding_rounds backfill populate edges.
            </div>
          </div>
        ) : (
          <ForceGraph2D
            graphData={graphData}
            width={size.width}
            height={size.height}
            backgroundColor="#FFFFFF"
            nodeRelSize={4}
            nodeVal={(n: ForceNode) => 1 + Math.sqrt(n.degree || 0) * 2}
            nodeLabel={(n: ForceNode) =>
              `${n.name} · ${n.entity_type}${
                n.degree ? ` (${n.degree})` : ""
              }`
            }
            nodeColor={(n: ForceNode) =>
              TYPE_STYLE[n.entity_type]?.color ?? DEFAULT_COLOR
            }
            linkColor={() => "rgba(156, 163, 175, 0.4)"}
            linkWidth={(l: ForceLink) => 0.5 + (l.confidence || 0) * 1.0}
            linkDirectionalParticles={0}
            cooldownTicks={100}
            onNodeClick={(n: ForceNode) => handleNodeClick(n)}
            nodeCanvasObjectMode={() => "after"}
            nodeCanvasObject={(n: ForceNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
              // Draw the label only when zoomed in enough to keep it readable.
              if (globalScale < 1.2) return;
              const label = n.name;
              const fontSize = 11 / globalScale;
              ctx.font = `${fontSize}px -apple-system, sans-serif`;
              ctx.fillStyle = "#111827";
              ctx.textAlign = "center";
              ctx.textBaseline = "top";
              const radius =
                1 + Math.sqrt(n.degree || 0) * 2 + 4 / globalScale;
              ctx.fillText(label, n.x ?? 0, (n.y ?? 0) + radius);
            }}
          />
        )}
      </div>

      <ProjectModal
        project={selectedProject}
        open={!!selectedProject}
        onClose={() => setSelectedProject(null)}
      />
    </div>
  );
}
