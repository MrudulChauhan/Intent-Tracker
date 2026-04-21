"use client";
import { useState } from "react";

const PROTOCOL_SLUGS: Record<string, string> = {
  "UniswapX": "uniswap",
  "Uniswap": "uniswap",
  "CoW Protocol": "cow-protocol",
  "CoW Swap": "cow-protocol",
  "CoWSwap": "cow-protocol",
  "CowSwap": "cow-protocol",
  "1inch": "1inch",
  "1inch Fusion": "1inch",
  "Across Protocol": "across",
  "Across": "across",
  "Aave": "aave",
  "Lido Finance": "lido",
  "dYdX": "dydx",
  "Jupiter": "jupiter",
  "Safe": "safe",
  "Safe Global": "safe",
  "Stargate": "stargate",
  "LayerZero": "layerzero",
  "Wormhole": "wormhole",
  "Hashflow": "hashflow",
  "Biconomy": "biconomy",
  "Hop Protocol": "hop",
  "Paraswap": "paraswap",
  "ParaSwap": "paraswap",
  "Flashbots": "flashbots",
  "deBridge": "debridge",
  "Particle Network": "particle-network",
  "Socket": "socket",
  "LI.FI": "lifi",
  "0x Protocol": "0x",
  "AirSwap": "airswap",
  "Airswap": "airswap",
  "Solana": "solana",
  "Ethereum": "ethereum",
  "Bitcoin": "bitcoin",
  "BNB": "bnb",
  "Squid Router": "squid",
  "Squid": "squid",
  "Osmosis": "osmosis-dex",
  "Everclear": "everclear",
  "Connext": "everclear",
  "Bebop": "bebop",
  "Enso Finance": "enso-finance",
  "Enso": "enso-finance",
  "Khalani Network": "khalani",
  "Khalani": "khalani",
  "Anoma": "anoma",
  "Namada": "namada",
  "Essential": "essential",
  "SYMMIO": "symmio",
  "Aori": "aori",
  "Mantis": "mantis",
  "MantisSwap": "mantis",
  "Flood Protocol": "flood",
  "Flood": "flood",
};

const COLORS = [
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

export function ProjectLogo({ name, size = "md" }: { name: string; size?: "sm" | "md" | "lg" }) {
  const [imgError, setImgError] = useState(false);
  const slug = PROTOCOL_SLUGS[name] || name.toLowerCase().replace(/\s+/g, "-");
  const src = `/logos/protocols/${slug}.png`;

  const initials = name.split(/[\s-]+/).map(w => w[0]).join("").slice(0, 2).toUpperCase();
  const colorClass = COLORS[hashName(name) % COLORS.length];

  const sizeMap = {
    sm: { cls: "w-5 h-5 text-[8px]", px: 20 },
    md: { cls: "w-7 h-7 text-[10px]", px: 28 },
    lg: { cls: "w-10 h-10 text-xs", px: 40 },
  };
  const s = sizeMap[size];

  if (imgError) {
    return (
      <div className={`${s.cls} rounded-full ${colorClass} flex items-center justify-center font-bold text-white flex-shrink-0 shadow-sm`}>
        {initials}
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={name}
      width={s.px}
      height={s.px}
      className={`${s.cls} rounded-full flex-shrink-0 object-cover shadow-sm`}
      onError={() => setImgError(true)}
    />
  );
}
