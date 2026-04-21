"use client";

import { useEffect, useState } from "react";
import { Search, ArrowRight } from "lucide-react";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { StatsRow, LeaderboardCard } from "@/components/stats-row";
import { ProjectCard } from "@/components/project-card";
import { ProjectModal } from "@/components/project-modal";
import { ProjectLogo } from "@/components/project-logo";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

type Project = import("@/lib/api").Project & {
  token?: string;
  funding_total?: number | null;
  tvl?: number;
};
type Mention = import("@/lib/api").Mention;
type Stats = import("@/lib/api").Stats;

const CATEGORY_FILTERS = ["All", "Solver", "Bridge", "DEX", "Infrastructure", "Aggregator", "Orderflow"];

const POPULAR_SEARCHES = [
  { label: "UniswapX", color: "bg-violet-400" },
  { label: "1inch Fusion", color: "bg-blue-400" },
  { label: "CoW Protocol", color: "bg-amber-400" },
  { label: "Across Bridge", color: "bg-emerald-400" },
  { label: "deBridge", color: "bg-pink-400" },
];

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 shadow-lg rounded-lg px-3 py-2">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-sm font-semibold text-gray-900">{payload[0].value}</p>
    </div>
  );
};

export default function HomePage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [mentions, setMentions] = useState<Mention[]>([]);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("All");
  const [loading, setLoading] = useState(true);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [activeTab, setActiveTab] = useState("Projects");

  useEffect(() => {
    async function load() {
      try {
        const [s, p, m] = await Promise.all([
          api.stats(),
          api.projects(),
          api.mentions({ limit: "12" }),
        ]);
        setStats(s);
        setProjects(p);
        setMentions(m);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filteredProjects = projects
    .filter(
      (p) =>
        (!search ||
          p.name.toLowerCase().includes(search.toLowerCase()) ||
          (p.description || "").toLowerCase().includes(search.toLowerCase())) &&
        (categoryFilter === "All" || (p.category || "").toLowerCase() === categoryFilter.toLowerCase())
    )
    .sort((a, b) => (b.funding_total || 0) - (a.funding_total || 0))
    .slice(0, 6);

  const tvlData = projects
    .filter((p) => p.tvl && p.tvl > 0)
    .sort((a, b) => (b.tvl || 0) - (a.tvl || 0))
    .slice(0, 8)
    .map((p) => ({ name: p.name, tvl: p.tvl }));

  const topByFunding = projects
    .filter((p) => p.funding_total && p.funding_total > 0)
    .sort((a, b) => (b.funding_total || 0) - (a.funding_total || 0))
    .slice(0, 5)
    .map((p, i) => ({
      rank: i + 1,
      name: p.name,
      ticker: p.token_symbol || p.token,
      value: `$${p.funding_total}M`,
    }));

  const TABS = ["Projects", "By TVL", "By Funding", "By Activity"];

  if (loading) {
    return (
      <div className="space-y-6 pt-4">
        <div className="h-8 w-64 bg-gray-100 rounded-lg animate-pulse" />
        <div className="h-12 w-full bg-gray-100 rounded-xl animate-pulse" />
        <div className="grid grid-cols-5 gap-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 relative">
      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Main column */}
          <div className="lg:col-span-8 space-y-8">
            {/* Market overview section */}
            <div>
              <h2 className="text-xl font-bold text-gray-900 mb-4">Market overview</h2>

              {/* Tab bar */}
              <div className="flex items-center gap-6 border-b border-gray-200 mb-6">
                {TABS.map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`pb-2.5 text-sm font-medium transition-colors relative ${
                      activeTab === tab
                        ? "text-gray-900 border-b-2 border-gray-900"
                        : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {/* Category filter pills */}
              <div className="flex flex-wrap gap-2 mb-4">
                {CATEGORY_FILTERS.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setCategoryFilter(cat)}
                    className={`text-xs px-3 py-1.5 rounded-full transition-colors duration-150 border ${
                      categoryFilter === cat
                        ? "bg-gray-900 text-white border-gray-900 font-medium"
                        : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              {/* Content based on tab */}
              {activeTab === "Projects" && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.2 }}
                  className="grid md:grid-cols-2 gap-3"
                >
                  {filteredProjects.map((p) => (
                    <ProjectCard key={p.id} {...p} onClick={() => setSelectedProject(p)} />
                  ))}
                </motion.div>
              )}

              {activeTab === "By TVL" && tvlData.length > 0 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="bg-white border border-gray-200 rounded-xl p-5"
                >
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart
                      data={tvlData}
                      layout="vertical"
                      margin={{ left: 60, right: 10, top: 5, bottom: 5 }}
                    >
                      <XAxis type="number" hide />
                      <YAxis
                        type="category"
                        dataKey="name"
                        stroke="#E5E7EB"
                        tick={{ fill: '#9CA3AF', fontSize: 11 }}
                        width={55}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="tvl" fill="#10B981" radius={[0, 4, 4, 0]} opacity={0.8} />
                    </BarChart>
                  </ResponsiveContainer>
                </motion.div>
              )}

              {activeTab === "By Funding" && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="bg-white border border-gray-200 rounded-xl p-5"
                >
                  <div className="space-y-0">
                    {topByFunding.map((item, i) => (
                      <div key={i} className="flex items-center gap-3 py-3 border-b border-gray-100 last:border-0">
                        <span className="text-sm text-gray-400 w-5 tabular-nums">{item.rank}</span>
                        <ProjectLogo name={item.name} size="sm" />
                        <span className="text-sm font-medium text-gray-900 flex-1">{item.name}</span>
                        {item.ticker && (
                          <span className="text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-500">{item.ticker}</span>
                        )}
                        <span className="text-sm font-semibold text-gray-900 tabular-nums">{item.value}</span>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}

              {activeTab === "By Activity" && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="bg-white border border-gray-200 rounded-xl p-5"
                >
                  <div className="space-y-0">
                    {projects
                      .filter((p) => p.relevance_score && p.relevance_score > 0)
                      .sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0))
                      .slice(0, 5)
                      .map((p, i) => (
                        <div key={p.id} className="flex items-center gap-3 py-3 border-b border-gray-100 last:border-0 cursor-pointer hover:bg-gray-50 -mx-2 px-2 rounded" onClick={() => setSelectedProject(p)}>
                          <span className="text-sm text-gray-400 w-5 tabular-nums">{i + 1}</span>
                          <ProjectLogo name={p.name} size="sm" />
                          <span className="text-sm font-medium text-gray-900 flex-1">{p.name}</span>
                          <span className="text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-500">{p.category}</span>
                          <span className="text-sm font-semibold text-emerald-600 tabular-nums">{((p.relevance_score || 0) * 100).toFixed(0)}%</span>
                        </div>
                      ))}
                  </div>
                </motion.div>
              )}
            </div>

            {/* Leaderboards section */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-semibold text-gray-900">Leaderboards</h2>
                <a href="/projects" className="text-sm text-gray-500 hover:text-gray-900 flex items-center gap-1 transition-colors">
                  View all <ArrowRight className="w-3.5 h-3.5" />
                </a>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <LeaderboardCard
                  title="Top by Funding"
                  value={stats ? `$${stats.total_raised}M` : "$0"}
                  subtitle="30d sum"
                  items={topByFunding}
                />
                <LeaderboardCard
                  title="Most Mentioned"
                  value={stats ? String(stats.mentions) : "0"}
                  subtitle="Latest"
                  items={mentions.slice(0, 5).map((m, i) => {
                    const t = m.title ?? "";
                    return {
                      rank: i + 1,
                      name: t.length > 30 ? t.slice(0, 30) + "..." : t,
                      value: (m.source ?? "").replace("_", " "),
                    };
                  })}
                />
                <LeaderboardCard
                  title="Most Active"
                  value={stats ? String(stats.active) : "0"}
                  subtitle="Active projects"
                  items={projects
                    .filter((p) => p.status === "active")
                    .slice(0, 5)
                    .map((p, i) => ({
                      rank: i + 1,
                      name: p.name,
                      ticker: p.token_symbol || p.token,
                      value: p.category || "",
                    }))}
                />
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-4 space-y-4">
            {/* Quick stats card */}
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-4">Quick stats</h3>
              <div className="space-y-0">
                {stats && (
                  <>
                    <QuickStatItem label="Total Projects" value={String(stats.projects)} />
                    <QuickStatItem label="Social Mentions" value={String(stats.mentions)} />
                    <QuickStatItem label="Active Projects" value={String(stats.active)} />
                    <QuickStatItem label="Capital Raised" value={`$${stats.total_raised}M`} />
                    <QuickStatItem label="Pending Review" value={String(stats.unreviewed)} />
                  </>
                )}
              </div>
            </div>

            {/* Recently discovered */}
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-4">Recently discovered</h3>
              <div className="space-y-0">
                {projects.slice(0, 5).map((p) => (
                  <div
                    key={p.id}
                    className="flex items-center gap-2.5 py-2 border-b border-gray-100 last:border-0 cursor-pointer hover:bg-gray-50 -mx-2 px-2 rounded transition-colors"
                    onClick={() => setSelectedProject(p)}
                  >
                    <ProjectLogo name={p.name} size="sm" />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900 truncate">{p.name}</div>
                      <div className="text-xs text-gray-500">{p.category}</div>
                    </div>
                    {(p.token_symbol || p.token) && (
                      <span className="text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-500">{p.token_symbol || p.token}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Scan button */}
            <button
              onClick={() => api.scan()}
              className="w-full bg-gray-900 text-white text-sm font-medium py-2.5 rounded-xl hover:bg-gray-800 transition-colors"
            >
              Run scan
            </button>
          </div>
        </div>

      {/* Latest signals - full width */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-gray-900">Latest signals</h2>
            <a href="/social" className="text-sm text-gray-500 hover:text-gray-900 flex items-center gap-1 transition-colors">
              View all <ArrowRight className="w-3.5 h-3.5" />
            </a>
          </div>
          <div className="space-y-0">
            {mentions.map((m, i) => (
              <div key={m.id}>
                <div className="py-2.5 flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <a
                      href={m.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-gray-700 hover:text-gray-900 transition-colors line-clamp-1"
                    >
                      {m.title}
                    </a>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded">
                      {(m.source ?? '').replace('_', ' ')}
                    </span>
                    <span className="text-[11px] text-gray-400 tabular-nums">
                      {m.published_at ? new Date(m.published_at).toLocaleDateString() : ""}
                    </span>
                  </div>
                </div>
                {i < mentions.length - 1 && <div className="border-t border-gray-100" />}
              </div>
            ))}
          </div>
        </div>

      {/* Project Modal */}
      <ProjectModal
        project={selectedProject}
        open={!!selectedProject}
        onClose={() => setSelectedProject(null)}
      />
    </div>
  );
}

function QuickStatItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-gray-100 last:border-0">
      <span className="text-xs text-gray-500">{label}</span>
      <span className="text-sm font-semibold tabular-nums text-gray-900">{value}</span>
    </div>
  );
}
