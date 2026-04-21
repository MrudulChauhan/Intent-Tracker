"use client";
import { useState } from "react";

const CHAIN_SLUGS: Record<string, string> = {
  "Ethereum": "ethereum",
  "Arbitrum": "arbitrum",
  "Optimism": "optimism",
  "Base": "base",
  "Polygon": "polygon",
  "BNB Chain": "bnb-chain",
  "Avalanche": "avalanche",
  "Solana": "solana",
  "Cosmos": "cosmos",
  "Celestia": "celestia",
  "Sui": "sui",
  "Near": "near",
  "NEAR": "near",
  "Gnosis Chain": "gnosis-chain",
  "Gnosis": "gnosis-chain",
  "Fantom": "fantom",
  "Scroll": "scroll",
  "zkSync Era": "zksync-era",
  "zkSync": "zksync-era",
  "Mantle": "mantle",
  "Blast": "blast",
  "Linea": "linea",
  "Osmosis": "osmosis",
  "Sei": "sei",
  "Aptos": "aptos",
  "Mode": "base", // Mode uses Base logo as fallback
  "IBC": "cosmos",
  "Multi-chain": "ethereum",
};

const FALLBACK_COLORS = [
  "bg-emerald-500", "bg-blue-500", "bg-violet-500",
  "bg-amber-500", "bg-pink-500", "bg-cyan-500",
  "bg-indigo-500", "bg-rose-500", "bg-teal-500", "bg-orange-500",
];

function hashName(name: string): number {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = ((hash << 5) - hash) + name.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

export function ChainLogo({ name, size = 16 }: { name: string; size?: number }) {
  const [imgError, setImgError] = useState(false);
  const slug = CHAIN_SLUGS[name] || name.toLowerCase().replace(/\s+/g, "-");
  const src = `/logos/chains/${slug}.png`;

  if (imgError) {
    const initial = name.trim().slice(0, 1).toUpperCase() || "?";
    const colorClass = FALLBACK_COLORS[hashName(name) % FALLBACK_COLORS.length];
    const fontSize = Math.max(8, Math.floor(size * 0.55));
    return (
      <span
        role="img"
        aria-label={name}
        className={`inline-flex items-center justify-center rounded-full text-white font-bold flex-shrink-0 ${colorClass}`}
        style={{ width: size, height: size, fontSize }}
      >
        {initial}
      </span>
    );
  }

  return (
    <img
      src={src}
      alt={name}
      width={size}
      height={size}
      className="rounded-full inline-block"
      onError={() => setImgError(true)}
    />
  );
}

export function ChainTag({ name }: { name: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 font-medium border border-gray-200">
      <ChainLogo name={name} size={14} />
      {name}
    </span>
  );
}
