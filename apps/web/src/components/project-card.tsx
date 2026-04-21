"use client";
import { ExternalLink, GitBranch } from "lucide-react";
import { ProjectLogo } from "./project-logo";
import { ChainTag } from "./chain-logo";

interface ProjectCardProps {
  name: string;
  category?: string;
  description?: string;
  chains?: string;
  token?: string;
  token_symbol?: string;
  funding_total?: number | null;
  website?: string;
  twitter_handle?: string;
  github_org?: string;
  status?: string;
  onClick?: () => void;
}

export function ProjectCard(props: ProjectCardProps) {
  const { name, category, description, chains, token, token_symbol, funding_total, website, twitter_handle, github_org, status, onClick } = props;

  let chainList: string[] = [];
  if (chains) {
    try { chainList = JSON.parse(chains); } catch { chainList = chains ? [chains] : []; }
  }

  const displayToken = token_symbol || token;

  return (
    <div
      onClick={onClick}
      className="group bg-white border border-gray-200 rounded-xl p-4 hover:shadow-md hover:border-gray-300 transition-all cursor-pointer"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="flex items-center gap-2">
            <ProjectLogo name={name} />
            <div>
              <h3 className="font-semibold text-gray-900 text-sm">
                {name}
              </h3>
              {category && (
                <span className="text-xs text-gray-500">{category}</span>
              )}
            </div>
          </div>
        </div>
        {status && (
          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${
            status === "active"
              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
              : "bg-gray-50 text-gray-600 border-gray-200"
          }`}>
            {status}
          </span>
        )}
      </div>

      {/* Description */}
      {description && (
        <p className="text-xs text-gray-500 line-clamp-2 mb-3 leading-relaxed">{description}</p>
      )}

      {/* Chain tags */}
      {chainList.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {chainList.slice(0, 4).map((c, i) => (
            <ChainTag key={i} name={c} />
          ))}
          {chainList.length > 4 && (
            <span className="text-[10px] text-gray-400">+{chainList.length - 4}</span>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-gray-100">
        <div className="flex items-center gap-3">
          {displayToken && (
            <span className="text-xs font-mono text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">{displayToken}</span>
          )}
          {funding_total != null && funding_total > 0 && (
            <span className="text-xs font-medium text-emerald-600">${funding_total}M raised</span>
          )}
        </div>
        <div className="flex items-center gap-2 text-gray-400">
          {website && (
            <a href={website} target="_blank" rel="noopener noreferrer" className="hover:text-gray-700 transition-colors" onClick={(e) => e.stopPropagation()}>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
          {twitter_handle && (
            <a href={`https://x.com/${twitter_handle.replace('@','')}`} target="_blank" rel="noopener noreferrer" className="hover:text-gray-700 transition-colors" onClick={(e) => e.stopPropagation()}>
              <span className="text-[10px] font-bold">X</span>
            </a>
          )}
          {github_org && (
            <a href={`https://github.com/${github_org}`} target="_blank" rel="noopener noreferrer" className="hover:text-gray-700 transition-colors" onClick={(e) => e.stopPropagation()}>
              <GitBranch className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
