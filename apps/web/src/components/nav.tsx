"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Layers, Zap, MessageSquare, GitBranch, Sparkles, Search } from "lucide-react";

const links = [
  { href: "/overview", label: "Overview", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: Layers },
  { href: "/solvers", label: "Solvers", icon: Zap },
  { href: "/social", label: "Social", icon: MessageSquare },
  { href: "/github", label: "GitHub", icon: GitBranch },
  { href: "/discoveries", label: "Discoveries", icon: Sparkles },
];

export function Nav() {
  const pathname = usePathname();

  // Hide nav on landing page
  if (pathname === "/") return null;

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200 h-14">
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Brand */}
          <Link href="/" className="flex items-center">
            <img src="/logo-light.svg" alt="Intent Tracker" className="w-8 h-8 rounded-lg" />
          </Link>

          {/* Nav links */}
          <div className="flex items-center gap-1">
            {links.map(link => {
              const active = pathname === link.href ||
                (link.href !== "/overview" && pathname.startsWith(link.href));
              const Icon = link.icon;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-sm transition-colors duration-150 ${
                    active
                      ? "text-gray-900 font-semibold"
                      : "text-gray-500 hover:text-gray-900"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5 text-gray-400" />
                  {link.label}
                </Link>
              );
            })}
          </div>

          {/* Search */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 bg-gray-100 rounded-lg px-3 py-1.5 cursor-pointer hover:bg-gray-200 transition-colors">
              <Search className="w-3.5 h-3.5 text-gray-400" />
              <span className="text-sm text-gray-400">Search</span>
              <kbd className="text-[10px] font-mono bg-white border border-gray-200 rounded px-1.5 py-0.5 text-gray-400">&#8984;K</kbd>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
