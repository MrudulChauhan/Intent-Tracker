"use client";

import { useEffect, useState } from "react";
import { Search, Zap, ExternalLink } from "lucide-react";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { ProjectLogo } from "@/components/project-logo";

interface Solver {
  id: number;
  name: string;
  type: string;
  description?: string;
  protocols?: string;
  chains?: string;
  volume_tier?: string;
  status?: string;
  website?: string;
  twitter_handle?: string;
}

const TYPE_FILTERS = ["All", "Solver", "Filler", "Quoter"];

function TypeBadge({ type }: { type: string }) {
  const normalized = (type || "Solver").toLowerCase();
  let classes = "bg-gray-50 text-gray-600";

  if (normalized === "solver") {
    classes = "bg-indigo-50 text-indigo-700";
  } else if (normalized === "filler") {
    classes = "bg-emerald-50 text-emerald-700";
  } else if (normalized === "quoter") {
    classes = "bg-amber-50 text-amber-700";
  }

  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${classes}`}>
      {type || "Solver"}
    </span>
  );
}

function VolumeBars({ tier }: { tier?: string }) {
  const level = tier === "high" ? 3 : tier === "medium" ? 2 : 1;
  return (
    <div className="flex items-end gap-0.5 h-4">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className={`w-1.5 rounded-sm ${i <= level ? "bg-emerald-500" : "bg-gray-200"}`}
          style={{ height: `${(i / 3) * 100}%` }}
        />
      ))}
    </div>
  );
}

export default function SolversPage() {
  const [solvers, setSolvers] = useState<Solver[]>([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState("All");
  const [search, setSearch] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const data = await api.solvers ? await api.solvers() : [];
        setSolvers(Array.isArray(data) ? data : []);
      } catch (e) {
        console.error(e);
        setSolvers([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filtered = solvers.filter((s) => {
    const matchesType = typeFilter === "All" || (s.type || "").toLowerCase() === typeFilter.toLowerCase();
    const matchesSearch = !search ||
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      (s.description || "").toLowerCase().includes(search.toLowerCase());
    return matchesType && matchesSearch;
  });

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.2 }}
      >
        <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <Zap className="w-4 h-4 text-emerald-500" />
          Solvers and Fillers
        </h1>
        <p className="text-sm text-gray-500 mt-1">Entities competing to fill intents across the ecosystem</p>
      </motion.div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search solvers..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9 bg-white border border-gray-200 rounded-lg pl-9 pr-3 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-gray-300 focus:ring-1 focus:ring-gray-200 transition-all w-56"
          />
        </div>
        <div className="flex gap-1.5">
          {TYPE_FILTERS.map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`text-xs px-3 py-1.5 rounded-full transition-colors duration-150 border ${
                typeFilter === t
                  ? "bg-gray-900 text-white border-gray-900 font-medium"
                  : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-48 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-500 text-sm">
          {solvers.length === 0
            ? "No solver data available yet. The /api/solvers endpoint may not be configured."
            : "No solvers match your filters."}
        </div>
      ) : (
        <>
          {/* Solver Cards Grid */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.2 }}
            className="grid md:grid-cols-2 lg:grid-cols-3 gap-4"
          >
            {filtered.map((s, idx) => {
              let chainList: string[] = [];
              try { chainList = typeof s.chains === 'string' ? JSON.parse(s.chains) : (s.chains || []); } catch { chainList = []; }

              let protocolList: string[] = [];
              try { protocolList = typeof s.protocols === 'string' ? JSON.parse(s.protocols) : (s.protocols || []); } catch { protocolList = []; }

              return (
                <div
                  key={s.id || idx}
                  className="group bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md hover:border-gray-300 transition-all"
                >
                  {/* Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2.5">
                      <ProjectLogo name={s.name} />
                      <div>
                        <h3 className="font-semibold text-gray-900 text-sm">{s.name}</h3>
                        <TypeBadge type={s.type} />
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <VolumeBars tier={s.volume_tier} />
                    </div>
                  </div>

                  {/* Description */}
                  {s.description && (
                    <p className="text-xs text-gray-500 line-clamp-2 mb-3 leading-relaxed">{s.description}</p>
                  )}

                  {/* Protocols (Active on) */}
                  {protocolList.length > 0 && (
                    <div className="mb-3">
                      <div className="text-[10px] uppercase tracking-wider text-gray-400 font-medium mb-1.5">Active on</div>
                      <div className="flex flex-wrap gap-1">
                        {protocolList.slice(0, 4).map((pr, i) => (
                          <span key={i} className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600">
                            {pr}
                          </span>
                        ))}
                        {protocolList.length > 4 && (
                          <span className="text-[10px] text-gray-400">+{protocolList.length - 4}</span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Chains */}
                  {chainList.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {chainList.slice(0, 4).map((c, i) => (
                        <span key={i} className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600">
                          {c}
                        </span>
                      ))}
                      {chainList.length > 4 && (
                        <span className="text-[10px] text-gray-400">+{chainList.length - 4}</span>
                      )}
                    </div>
                  )}

                  {/* Footer */}
                  <div className="flex items-center justify-between pt-2 border-t border-gray-100">
                    {s.status && (
                      <span className="text-[10px] text-gray-500 font-medium capitalize">{s.status}</span>
                    )}
                    <div className="flex items-center gap-2 text-gray-400 ml-auto">
                      {s.website && (
                        <a href={s.website} target="_blank" rel="noopener noreferrer" className="hover:text-gray-700 transition-colors">
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                      {s.twitter_handle && (
                        <a href={`https://x.com/${String(s.twitter_handle).replace('@','')}`} target="_blank" rel="noopener noreferrer" className="hover:text-gray-700 transition-colors">
                          <span className="text-[10px] font-bold">X</span>
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </motion.div>

          {/* Summary table */}
          {filtered.length > 3 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mt-6">
              <div className="px-5 py-3 border-b border-gray-200 bg-gray-50">
                <span className="text-xs font-medium uppercase tracking-wider text-gray-500">All Solvers</span>
              </div>
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 bg-gray-50">
                    <th className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-2.5 text-left">Name</th>
                    <th className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-2.5 text-left">Type</th>
                    <th className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-2.5 text-left">Volume</th>
                    <th className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-2.5 text-left">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((s, idx) => (
                    <tr key={s.id || idx} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          <ProjectLogo name={s.name} size="sm" />
                          <span className="text-sm text-gray-900 font-medium">{s.name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-2.5">
                        <TypeBadge type={s.type} />
                      </td>
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          <VolumeBars tier={s.volume_tier} />
                          <span className="text-[10px] text-gray-500 capitalize">{s.volume_tier || "low"}</span>
                        </div>
                      </td>
                      <td className="px-4 py-2.5">
                        <span className="text-xs text-gray-600 capitalize">{s.status || "active"}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
