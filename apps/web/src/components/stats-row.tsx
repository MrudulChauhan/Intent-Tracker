import { TrendingUp, TrendingDown } from "lucide-react";

interface LeaderboardItem {
  rank: number;
  name: string;
  ticker?: string;
  value: string;
  change?: string;
  changeType?: "positive" | "negative";
}

interface LeaderboardCardProps {
  title: string;
  value: string;
  change?: string;
  changeType?: "positive" | "negative";
  subtitle?: string;
  items?: LeaderboardItem[];
}

export function LeaderboardCard({ title, value, change, changeType, subtitle, items }: LeaderboardCardProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md transition-all">
      <div className="text-sm text-gray-500 font-medium">{title}</div>
      <div className="flex items-baseline gap-2 mt-1">
        <span className="text-2xl font-bold text-gray-900 tabular-nums">{value}</span>
        {change && (
          <span className={`text-sm font-medium flex items-center gap-0.5 ${
            changeType === "negative" ? "text-red-500" : "text-emerald-500"
          }`}>
            {changeType === "negative" ? (
              <TrendingDown className="w-3.5 h-3.5" />
            ) : (
              <TrendingUp className="w-3.5 h-3.5" />
            )}
            {change}
          </span>
        )}
      </div>
      {subtitle && <div className="text-xs text-gray-400 mt-0.5">{subtitle}</div>}

      {/* Mini sparkline placeholder */}
      <div className="mt-3 h-10 w-full rounded overflow-hidden">
        <svg viewBox="0 0 200 40" className="w-full h-full" preserveAspectRatio="none">
          <defs>
            <linearGradient id={`spark-${title.replace(/\s/g, '')}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10B981" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#10B981" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path
            d="M0,30 Q25,28 50,22 T100,18 T150,12 T200,8 V40 H0 Z"
            fill={`url(#spark-${title.replace(/\s/g, '')})`}
          />
          <path
            d="M0,30 Q25,28 50,22 T100,18 T150,12 T200,8"
            fill="none"
            stroke="#10B981"
            strokeWidth="1.5"
          />
        </svg>
      </div>

      {/* Items list */}
      {items && items.length > 0 && (
        <div className="mt-3 space-y-0">
          {items.map((item) => (
            <div key={item.rank} className="flex items-center gap-2.5 py-1.5">
              <span className="text-sm text-gray-400 w-4 tabular-nums">{item.rank}</span>
              <div className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center text-white text-[9px] font-semibold flex-shrink-0">
                {item.name.charAt(0).toUpperCase()}
              </div>
              <span className="text-sm font-medium text-gray-900 flex-1 truncate">{item.name}</span>
              {item.ticker && (
                <span className="text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-500">{item.ticker}</span>
              )}
              <span className="text-sm text-gray-900 tabular-nums">{item.value}</span>
              {item.change && (
                <span className={`text-xs ${item.changeType === "negative" ? "text-red-500" : "text-emerald-500"}`}>
                  {item.change}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* Legacy StatsRow for backward compatibility */
interface StatItem {
  label: string;
  value: string;
  change?: string;
  accent?: boolean;
}

export function StatsRow({ items }: { items: StatItem[] }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-5 gap-3 mb-6">
      {items.map((item, i) => (
        <div
          key={i}
          className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md transition-all"
        >
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-bold tabular-nums text-gray-900">
              {item.value}
            </span>
            {item.change && (
              <span className={`text-xs font-medium ${
                item.change.startsWith('+') ? 'text-emerald-500' : 'text-red-500'
              }`}>
                {item.change}
              </span>
            )}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {item.label}
          </div>
        </div>
      ))}
    </div>
  );
}
