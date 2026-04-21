"use client";

import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { ProjectLogo } from "@/components/project-logo";
import { ProjectModal } from "@/components/project-modal";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type Project = import("@/lib/api").Project & {
  token?: string;
  funding_total?: number | null;
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const params: Record<string, string> = {};
        if (search) params.search = search;
        if (category) params.category = category;
        if (status) params.status = status;
        const data = await api.projects(
          Object.keys(params).length > 0 ? params : undefined
        );
        setProjects(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [search, category, status]);

  const categories = [...new Set(projects.map((p) => p.category).filter(Boolean))];
  const statuses = [...new Set(projects.map((p) => p.status).filter(Boolean))];

  return (
    <div className="space-y-6">
      <motion.h1
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.2 }}
        className="text-xl font-bold text-gray-900"
      >
        Projects
      </motion.h1>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search projects..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9 bg-white border border-gray-200 rounded-lg pl-9 pr-3 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-gray-300 focus:ring-1 focus:ring-gray-200 transition-all w-56"
          />
        </div>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="h-9 bg-white border border-gray-200 rounded-lg px-3 text-sm text-gray-700 focus:outline-none focus:border-gray-300 appearance-none cursor-pointer"
        >
          <option value="">All Categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="h-9 bg-white border border-gray-200 rounded-lg px-3 text-sm text-gray-700 focus:outline-none focus:border-gray-300 appearance-none cursor-pointer"
        >
          <option value="">All Statuses</option>
          {statuses.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-12 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <div className="text-center py-16 text-gray-500 text-sm">
          No projects found matching your filters.
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="border-gray-200 hover:bg-transparent bg-gray-50">
                <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                  Name
                </TableHead>
                <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                  Category
                </TableHead>
                <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                  Token
                </TableHead>
                <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                  Raised
                </TableHead>
                <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                  Status
                </TableHead>
                <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                  Relevance
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {projects.map((p) => (
                <TableRow
                  key={p.id}
                  className="border-b border-gray-100 hover:bg-gray-50 transition-colors cursor-pointer"
                  onClick={() => setSelectedProject(p)}
                >
                  <TableCell className="text-sm font-medium text-gray-900 px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <ProjectLogo name={p.name} size="sm" />
                      <span>{p.name}</span>
                      {(p.token_symbol || p.token) && (
                        <span className="text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-500">
                          {p.token_symbol || p.token}
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-gray-600 px-4 py-3">
                    {p.category}
                  </TableCell>
                  <TableCell className="px-4 py-3">
                    {(p.token_symbol || p.token) ? (
                      <span className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-500">
                        {p.token_symbol || p.token}
                      </span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </TableCell>
                  <TableCell className="px-4 py-3">
                    {p.funding_total != null && p.funding_total > 0 ? (
                      <span className="text-sm text-gray-900 font-semibold tabular-nums">${p.funding_total}M</span>
                    ) : (
                      <span className="text-sm text-gray-400">-</span>
                    )}
                  </TableCell>
                  <TableCell className="px-4 py-3">
                    <StatusBadge status={p.status} />
                  </TableCell>
                  <TableCell className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-emerald-500 rounded-full"
                          style={{ width: `${Math.min((p.relevance_score || 0) * 10, 100)}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-gray-500 tabular-nums">{p.relevance_score || 0}</span>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Project Modal */}
      <ProjectModal
        project={selectedProject}
        open={!!selectedProject}
        onClose={() => setSelectedProject(null)}
      />
    </div>
  );
}

function StatusBadge({ status }: { status?: string }) {
  const isActive = status === "active";
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full border ${
      isActive
        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
        : "bg-gray-50 text-gray-600 border-gray-200"
    }`}>
      <span className={`w-1.5 h-1.5 rounded-full ${isActive ? "bg-emerald-500" : "bg-gray-400"}`} />
      {status || "unknown"}
    </span>
  );
}
