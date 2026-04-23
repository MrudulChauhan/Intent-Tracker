"use client";

import { ArrowRight, Sparkles } from "lucide-react";
import type { Narrative } from "@/lib/api";

interface NarrativesCardProps {
  narratives: Narrative[];
  /** Optional click handler for a protocol badge. No-op by default — wired later. */
  onProtocolClick?: (protocol: string) => void;
}

function formatWeekLabel(isoDate: string | undefined): string {
  if (!isoDate) return "";
  const d = new Date(isoDate);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function NarrativesCard({
  narratives,
  onProtocolClick,
}: NarrativesCardProps) {
  // Nothing to render if we don't have any themes for the current week yet.
  if (!narratives || narratives.length === 0) {
    return null;
  }

  // All rows should share a week_start (the api.narratives(1) contract). Use
  // the first row's value for the subtitle.
  const weekLabel = formatWeekLabel(narratives[0]?.week_start);

  return (
    <section>
      <div className="flex items-end justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[#FF6B2C]" />
            This week&apos;s narratives
          </h2>
          <p className="text-xs text-gray-500 mt-1">
            {weekLabel ? <>Week of {weekLabel} · </> : null}
            {narratives.length} theme{narratives.length === 1 ? "" : "s"} clustered from social mentions
          </p>
        </div>
        <a
          href="/social"
          className="text-sm text-gray-500 hover:text-gray-900 flex items-center gap-1 transition-colors"
        >
          View signals <ArrowRight className="w-3.5 h-3.5" />
        </a>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {narratives.map((n, i) => (
          <div
            key={n.id}
            className={`p-5 ${i < narratives.length - 1 ? "border-b border-gray-100" : ""}`}
          >
            <div className="flex items-start gap-3">
              <span className="text-sm text-gray-400 w-5 tabular-nums pt-0.5">
                {n.rank}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-2 flex-wrap">
                  <h3 className="text-sm font-semibold text-gray-900">
                    {n.theme || "Untitled theme"}
                  </h3>
                </div>
                {n.summary && (
                  <p className="text-sm text-gray-600 mt-1.5 leading-relaxed">
                    {n.summary}
                  </p>
                )}
                {n.protocols_mentioned && n.protocols_mentioned.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {n.protocols_mentioned.map((p) => (
                      <button
                        key={p}
                        type="button"
                        onClick={() => onProtocolClick?.(p)}
                        className="text-[11px] px-2 py-0.5 rounded-full bg-[#FF6B2C]/10 text-[#FF6B2C] font-medium hover:bg-[#FF6B2C]/20 transition-colors"
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                )}
                {n.evidence_mention_ids && n.evidence_mention_ids.length > 0 && (
                  <div className="text-[11px] text-gray-400 mt-2">
                    Evidence: {n.evidence_mention_ids.length} mention{n.evidence_mention_ids.length === 1 ? "" : "s"}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
