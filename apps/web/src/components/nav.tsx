"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  LayoutDashboard,
  Layers,
  Zap,
  MessageSquare,
  GitBranch,
  Sparkles,
  Search,
} from "lucide-react";

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
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");

  // ⌘K / Ctrl+K focuses the search input from anywhere
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
        inputRef.current?.select();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    router.push(`/projects?search=${encodeURIComponent(q)}`);
  }

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
          <form
            onSubmit={submit}
            className="flex items-center gap-2 bg-gray-100 rounded-lg px-3 py-1.5 focus-within:bg-white focus-within:ring-1 focus-within:ring-gray-300 transition-colors"
          >
            <Search className="w-3.5 h-3.5 text-gray-400" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search projects"
              className="bg-transparent outline-none text-sm text-gray-700 placeholder:text-gray-400 w-32 focus:w-48 transition-all"
            />
            <kbd className="text-[10px] font-mono bg-white border border-gray-200 rounded px-1.5 py-0.5 text-gray-400 select-none">
              &#8984;K
            </kbd>
          </form>
        </div>
      </div>
    </nav>
  );
}
