"use client";

import { useEffect, useState } from "react";
import { Star, GitFork, Activity } from "lucide-react";
import { api } from "@/lib/api";
import { StatsRow } from "@/components/stats-row";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface GithubRepo {
  id: number;
  repo_url: string;
  repo_name?: string;
  stars: number;
  forks: number;
  open_issues: number;
  contributors: number;
  commits_30d: number;
  last_commit?: string;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 shadow-lg rounded-lg px-3 py-2">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-sm font-semibold text-gray-900">{payload[0].value} stars</p>
    </div>
  );
};

export default function GithubPage() {
  const [repos, setRepos] = useState<GithubRepo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.github();
        setRepos(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const totalStars = repos.reduce((s, r) => s + (r.stars || 0), 0);
  const mostStarred = repos.length > 0
    ? repos.reduce((best, r) => (r.stars > best.stars ? r : best), repos[0])
    : null;
  const chartData = repos
    .filter((r) => r.stars > 0)
    .sort((a, b) => b.stars - a.stars)
    .slice(0, 10)
    .map((r) => ({
      name: r.repo_name || r.repo_url.split("/").pop() || "repo",
      stars: r.stars,
    }));

  if (loading) {
    return (
      <div className="space-y-6 pt-4">
        <div className="h-8 w-48 bg-gray-100 rounded-lg animate-pulse" />
        <div className="grid grid-cols-3 gap-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
        <div className="h-64 bg-gray-100 rounded-xl animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-gray-900">GitHub Activity</h1>

      <StatsRow
        items={[
          { label: "Repos Tracked", value: String(repos.length) },
          { label: "Total Stars", value: String(totalStars) },
          { label: "Most Starred", value: mostStarred ? (mostStarred.repo_name || mostStarred.repo_url.split("/").pop() || "") : "-" },
        ]}
      />

      {/* Stars chart */}
      {chartData.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="text-sm font-medium text-gray-500 mb-4">Stars by Repository</div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ left: 80, right: 20, top: 5, bottom: 5 }}
            >
              <XAxis type="number" stroke="#F3F4F6" tick={{ fill: '#9CA3AF', fontSize: 11 }} />
              <YAxis
                type="category"
                dataKey="name"
                stroke="#F3F4F6"
                tick={{ fill: '#9CA3AF', fontSize: 11 }}
                width={75}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="stars" fill="#10B981" radius={[0, 4, 4, 0]} opacity={0.8} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Repos table */}
      {repos.length === 0 ? (
        <div className="text-center py-16 text-gray-500 text-sm">
          No GitHub repositories tracked yet.
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="border-gray-200 hover:bg-transparent bg-gray-50">
                <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                  Repository
                </TableHead>
                <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                  Stars
                </TableHead>
                <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                  Forks
                </TableHead>
                <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                  Issues
                </TableHead>
                <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                  Contributors
                </TableHead>
                <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                  Commits (30d)
                </TableHead>
                <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                  Last Commit
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {repos.map((r) => {
                const name = r.repo_name || r.repo_url.split("/").pop() || "repo";
                return (
                  <TableRow
                    key={r.id}
                    className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                  >
                    <TableCell className="text-sm px-4 py-3">
                      <a
                        href={r.repo_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-gray-900 hover:text-emerald-600 transition-colors font-medium"
                      >
                        {name}
                      </a>
                    </TableCell>
                    <TableCell className="px-4 py-3">
                      <span className="inline-flex items-center gap-1 text-sm text-gray-900 font-semibold tabular-nums">
                        <Star className="w-3.5 h-3.5 text-amber-400" />
                        {r.stars}
                      </span>
                    </TableCell>
                    <TableCell className="px-4 py-3">
                      <span className="inline-flex items-center gap-1 text-sm text-gray-600 tabular-nums">
                        <GitFork className="w-3.5 h-3.5 text-gray-400" />
                        {r.forks}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm text-gray-600 tabular-nums px-4 py-3">
                      {r.open_issues}
                    </TableCell>
                    <TableCell className="text-sm text-gray-600 tabular-nums px-4 py-3">
                      {r.contributors}
                    </TableCell>
                    <TableCell className="px-4 py-3">
                      <span className="inline-flex items-center gap-1 text-sm text-gray-600 tabular-nums">
                        <Activity className="w-3.5 h-3.5 text-emerald-500" />
                        {r.commits_30d}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-gray-400 px-4 py-3 tabular-nums">
                      {r.last_commit ? new Date(r.last_commit).toLocaleDateString() : "-"}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
