"use client";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ProjectLogo } from "./project-logo";
import { ExternalLink, GitBranch, Globe, ArrowUpRight } from "lucide-react";
import { ChainTag } from "./chain-logo";

interface ProjectModalProps {
  project: any;
  open: boolean;
  onClose: () => void;
}

export function ProjectModal({ project, open, onClose }: ProjectModalProps) {
  if (!project) return null;
  const p = project;

  let chains: string[] = [];
  try {
    chains = typeof p.chains === "string" ? JSON.parse(p.chains) : p.chains || [];
  } catch {
    chains = [];
  }

  const statusStyles: Record<string, string> = {
    active: "bg-emerald-50 text-emerald-700 border-emerald-200",
    building: "bg-amber-50 text-amber-700 border-amber-200",
    testnet: "bg-violet-50 text-violet-700 border-violet-200",
    mainnet: "bg-emerald-50 text-emerald-700 border-emerald-200",
  };
  const statusCls =
    statusStyles[(p.status || "active").toLowerCase()] || statusStyles.active;

  const links = [
    { label: "Website", url: p.website, icon: Globe },
    {
      label: "Twitter / X",
      url: p.twitter_handle
        ? `https://x.com/${String(p.twitter_handle).replace("@", "")}`
        : null,
      icon: ArrowUpRight,
    },
    {
      label: "GitHub",
      url: p.github_org ? `https://github.com/${p.github_org}` : null,
      icon: GitBranch,
    },
    {
      label: "CoinGecko",
      url: p.coingecko_id
        ? `https://coingecko.com/en/coins/${p.coingecko_id}`
        : null,
      icon: ExternalLink,
    },
    {
      label: "DefiLlama",
      url: p.defillama_slug
        ? `https://defillama.com/protocol/${p.defillama_slug}`
        : null,
      icon: ExternalLink,
    },
  ].filter((l) => l.url);

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-white border border-gray-200 text-gray-900 sm:max-w-[680px] max-h-[90vh] overflow-y-auto shadow-2xl rounded-2xl p-0">
        {/* Header with accent bar */}
        <div className="h-1.5 w-full bg-gradient-to-r from-[#FF6B2C] via-[#FF8F5C] to-[#FF6B2C] rounded-t-2xl" />

        <div className="px-6 pt-5 pb-6">
          <DialogHeader>
            <div className="flex items-start gap-4">
              <ProjectLogo name={p.name} size="lg" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  <DialogTitle className="text-xl font-bold text-gray-900 truncate">
                    {p.name}
                  </DialogTitle>
                  {p.status && (
                    <span
                      className={`text-[10px] font-semibold px-2.5 py-1 rounded-full border capitalize flex-shrink-0 ${statusCls}`}
                    >
                      {p.status}
                    </span>
                  )}
                </div>
                {p.category && (
                  <span className="text-xs text-gray-500 uppercase tracking-wider font-medium">
                    {p.category}
                  </span>
                )}
              </div>
            </div>
          </DialogHeader>

          {/* Description */}
          {p.description && (
            <p className="text-sm text-gray-600 leading-relaxed mt-4">
              {p.description}
            </p>
          )}

          {/* Stats grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5">
            {(p.token_symbol || p.token) && (
              <div className="bg-gray-50 border border-gray-100 rounded-xl p-3.5">
                <div className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold mb-1">
                  Token
                </div>
                <div className="text-base font-bold text-gray-900 font-mono">
                  {p.token_symbol || p.token}
                </div>
              </div>
            )}
            {p.funding_total != null && p.funding_total > 0 && (
              <div className="bg-gray-50 border border-gray-100 rounded-xl p-3.5">
                <div className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold mb-1">
                  Total Raised
                </div>
                <div className="text-base font-bold text-gray-900">
                  ${p.funding_total}M
                </div>
              </div>
            )}
            {p.relevance_score != null && p.relevance_score > 0 && (
              <div className="bg-gray-50 border border-gray-100 rounded-xl p-3.5">
                <div className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold mb-1">
                  Relevance
                </div>
                <div className="flex items-center gap-2">
                  <div className="text-base font-bold text-gray-900">
                    {(p.relevance_score * 100).toFixed(0)}%
                  </div>
                  <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#FF6B2C] rounded-full"
                      style={{ width: `${p.relevance_score * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            )}
            {chains.length > 0 && (
              <div className="bg-gray-50 border border-gray-100 rounded-xl p-3.5">
                <div className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold mb-1">
                  Chains
                </div>
                <div className="text-base font-bold text-gray-900">
                  {chains.length}
                </div>
              </div>
            )}
          </div>

          {/* Chains */}
          {chains.length > 0 && (
            <div className="mt-5">
              <div className="text-[11px] uppercase tracking-wider text-gray-400 font-semibold mb-2">
                Supported Chains
              </div>
              <div className="flex flex-wrap gap-1.5">
                {chains.map((c: string, i: number) => (
                  <span
                    key={i}
                    className="text-xs px-2.5 py-1 rounded-full bg-gray-100 text-gray-600 font-medium border border-gray-200"
                  >
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Links */}
          {links.length > 0 && (
            <div className="mt-5 pt-5 border-t border-gray-100">
              <div className="text-[11px] uppercase tracking-wider text-gray-400 font-semibold mb-3">
                Links
              </div>
              <div className="flex flex-wrap gap-2">
                {links.map((link, i) => {
                  const Icon = link.icon;
                  return (
                    <a
                      key={i}
                      href={link.url!}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 hover:border-gray-300 transition-all duration-150"
                    >
                      <Icon className="w-3.5 h-3.5 text-gray-400" />
                      {link.label}
                    </a>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
