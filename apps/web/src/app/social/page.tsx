"use client";

import { useEffect, useState } from "react";
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
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface Mention {
  id: number;
  title: string;
  source: string;
  url: string;
  published_at: string;
}

interface MentionStats {
  total: number;
  by_source: Record<string, number>;
  this_week: number;
}

const SOURCES = ["All", "Reddit", "RSS", "News", "Blog"];
const SOURCE_MAP: Record<string, string> = {
  Reddit: "reddit",
  RSS: "rss",
  News: "google_news",
  Blog: "blog",
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 shadow-lg rounded-lg px-3 py-2">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-sm font-semibold text-gray-900">{payload[0].value}</p>
    </div>
  );
};

export default function SocialPage() {
  const [mentions, setMentions] = useState<Mention[]>([]);
  const [stats, setStats] = useState<MentionStats | null>(null);
  const [activeSource, setActiveSource] = useState("All");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const params: Record<string, string> = { limit: "100" };
        if (activeSource !== "All") {
          params.source = SOURCE_MAP[activeSource] || activeSource.toLowerCase();
        }
        const [m, s] = await Promise.all([
          api.mentions(params),
          api.mentionStats(),
        ]);
        setMentions(m);
        setStats(s);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [activeSource]);

  const timelineData = mentions
    .filter((m) => m.published_at)
    .reduce((acc: Record<string, number>, m) => {
      const day = m.published_at.split("T")[0];
      acc[day] = (acc[day] || 0) + 1;
      return acc;
    }, {});

  const chartData = Object.entries(timelineData)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-30)
    .map(([date, count]) => ({ date, count }));

  const maxSourceCount = stats ? Math.max(...Object.values(stats.by_source), 1) : 1;

  if (loading) {
    return (
      <div className="space-y-6 pt-4">
        <div className="h-8 w-48 bg-gray-100 rounded-lg animate-pulse" />
        <div className="flex gap-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-8 w-16 bg-gray-100 rounded-full animate-pulse" />
          ))}
        </div>
        <div className="h-48 bg-gray-100 rounded-xl animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-gray-900">Social Intelligence</h1>

      {/* Source filter tabs */}
      <div className="flex gap-6 border-b border-gray-200">
        {SOURCES.map((s) => (
          <button
            key={s}
            onClick={() => setActiveSource(s)}
            className={`pb-2.5 text-sm font-medium transition-colors relative ${
              activeSource === s
                ? "text-gray-900 border-b-2 border-gray-900"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Stats row */}
      {stats && (
        <StatsRow
          items={[
            { label: "Total Mentions", value: String(stats.total) },
            { label: "This Week", value: String(stats.this_week) },
          ]}
        />
      )}

      {/* Two panel layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Timeline chart */}
        <div className="lg:col-span-2 bg-white border border-gray-200 rounded-xl p-5">
          <div className="text-sm font-medium text-gray-500 mb-4">Mention Timeline</div>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10B981" stopOpacity={0.1} />
                    <stop offset="100%" stopColor="#10B981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="date"
                  stroke="#F3F4F6"
                  tick={{ fill: '#9CA3AF', fontSize: 11 }}
                  tickFormatter={(v) => v.slice(5)}
                />
                <YAxis stroke="#F3F4F6" tick={{ fill: '#9CA3AF', fontSize: 11 }} width={30} />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="#10B981"
                  strokeWidth={2}
                  fill="url(#areaGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[200px] text-sm text-gray-500">
              No timeline data available.
            </div>
          )}
        </div>

        {/* Source breakdown */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="text-sm font-medium text-gray-500 mb-4">Source Breakdown</div>
          {stats && (
            <div className="space-y-3">
              {Object.entries(stats.by_source).map(([source, count]) => (
                <div key={source} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-600 capitalize">{source.replace('_', ' ')}</span>
                    <span className="text-xs font-semibold text-gray-900 tabular-nums">{count}</span>
                  </div>
                  <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500 bg-emerald-500"
                      style={{ width: `${(count / maxSourceCount) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Mentions table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-gray-200 hover:bg-transparent bg-gray-50">
              <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                Title
              </TableHead>
              <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                Source
              </TableHead>
              <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                Date
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {mentions.length === 0 ? (
              <TableRow className="border-gray-100">
                <TableCell colSpan={3} className="text-center text-sm text-gray-500 py-12">
                  No mentions found for this source.
                </TableCell>
              </TableRow>
            ) : (
              mentions.map((m) => (
                <TableRow
                  key={m.id}
                  className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                >
                  <TableCell className="text-sm px-4 py-3">
                    <a
                      href={m.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-gray-700 hover:text-gray-900 transition-colors"
                    >
                      {m.title}
                    </a>
                  </TableCell>
                  <TableCell className="px-4 py-3">
                    <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded">
                      {m.source.replace('_', ' ')}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs text-gray-400 px-4 py-3 tabular-nums">
                    {m.published_at ? new Date(m.published_at).toLocaleDateString() : "-"}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
