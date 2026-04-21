"use client";

import { useEffect, useState } from "react";
import { CheckCircle, Eye } from "lucide-react";
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

interface Discovery {
  id: number;
  name: string;
  type: string;
  entity_type?: string;
  discovered_at: string;
  reviewed: number;
}

function TypeBadge({ type }: { type: string }) {
  const normalized = (type || "unknown").toLowerCase().replace("_", " ");
  let classes = "bg-gray-50 text-gray-600 border-gray-200";

  if (normalized.includes("project")) {
    classes = "bg-blue-50 text-blue-700 border-blue-200";
  } else if (normalized.includes("mention")) {
    classes = "bg-emerald-50 text-emerald-700 border-emerald-200";
  } else if (normalized.includes("funding") || normalized.includes("raise")) {
    classes = "bg-amber-50 text-amber-700 border-amber-200";
  }

  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded-full border font-medium ${classes}`}>
      {normalized}
    </span>
  );
}

export default function DiscoveriesPage() {
  const [unreviewed, setUnreviewed] = useState<Discovery[]>([]);
  const [reviewed, setReviewed] = useState<Discovery[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const [u, r] = await Promise.all([
        api.discoveries({ reviewed: "0" }),
        api.discoveries({ reviewed: "1" }),
      ]);
      setUnreviewed(u);
      setReviewed(r);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function markReviewed(id: number) {
    try {
      await api.reviewDiscovery(id);
      setUnreviewed((prev) => prev.filter((d) => d.id !== id));
      const item = unreviewed.find((d) => d.id === id);
      if (item) setReviewed((prev) => [{ ...item, reviewed: 1 }, ...prev]);
    } catch (e) {
      console.error(e);
    }
  }

  async function markAllReviewed() {
    try {
      await Promise.all(unreviewed.map((d) => api.reviewDiscovery(d.id)));
      setReviewed((prev) => [
        ...unreviewed.map((d) => ({ ...d, reviewed: 1 })),
        ...prev,
      ]);
      setUnreviewed([]);
    } catch (e) {
      console.error(e);
    }
  }

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
      <h1 className="text-xl font-bold text-gray-900">Discoveries</h1>

      <StatsRow
        items={[
          { label: "Unreviewed", value: String(unreviewed.length) },
          { label: "Reviewed", value: String(reviewed.length) },
          { label: "Total", value: String(unreviewed.length + reviewed.length) },
        ]}
      />

      {/* Mark all button */}
      {unreviewed.length > 0 && (
        <button
          onClick={markAllReviewed}
          className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 hover:bg-gray-800 text-white text-sm font-medium rounded-lg active:scale-[0.98] transition-all duration-150"
        >
          <CheckCircle className="w-4 h-4" />
          Mark All Reviewed
        </button>
      )}

      {/* Unreviewed table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-gray-200 hover:bg-transparent bg-gray-50">
              <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                Name
              </TableHead>
              <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                Type
              </TableHead>
              <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                Date
              </TableHead>
              <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                Action
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {unreviewed.length === 0 ? (
              <TableRow className="border-gray-100">
                <TableCell
                  colSpan={4}
                  className="text-center text-sm text-gray-500 py-12"
                >
                  No unreviewed discoveries. You are all caught up.
                </TableCell>
              </TableRow>
            ) : (
              unreviewed.map((d) => (
                <TableRow
                  key={d.id}
                  className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                >
                  <TableCell className="text-sm font-medium text-gray-900 px-4 py-3">
                    {d.name}
                  </TableCell>
                  <TableCell className="px-4 py-3">
                    <TypeBadge type={d.entity_type || d.type || "unknown"} />
                  </TableCell>
                  <TableCell className="text-xs text-gray-400 px-4 py-3 tabular-nums">
                    {d.discovered_at
                      ? new Date(d.discovered_at).toLocaleDateString()
                      : "-"}
                  </TableCell>
                  <TableCell className="px-4 py-3">
                    <button
                      onClick={() => markReviewed(d.id)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 rounded-md transition-colors duration-150"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      Review
                    </button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Reviewed section - collapsible */}
      {reviewed.length > 0 && (
        <details className="group">
          <summary className="cursor-pointer text-xs uppercase tracking-[2px] text-gray-500 font-medium hover:text-gray-700 transition-colors select-none list-none flex items-center gap-2">
            <span className="group-open:rotate-90 transition-transform duration-200 text-gray-400">&#9654;</span>
            Reviewed ({reviewed.length})
          </summary>

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mt-3">
            <Table>
              <TableHeader>
                <TableRow className="border-gray-200 hover:bg-transparent bg-gray-50">
                  <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                    Name
                  </TableHead>
                  <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                    Type
                  </TableHead>
                  <TableHead className="text-xs uppercase tracking-wider text-gray-500 font-medium px-4 py-3">
                    Date
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reviewed.map((d) => (
                  <TableRow
                    key={d.id}
                    className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                  >
                    <TableCell className="text-sm text-gray-700 px-4 py-3">
                      {d.name}
                    </TableCell>
                    <TableCell className="px-4 py-3">
                      <TypeBadge type={d.entity_type || d.type || "unknown"} />
                    </TableCell>
                    <TableCell className="text-xs text-gray-400 px-4 py-3 tabular-nums">
                      {d.discovered_at
                        ? new Date(d.discovered_at).toLocaleDateString()
                        : "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </details>
      )}
    </div>
  );
}
