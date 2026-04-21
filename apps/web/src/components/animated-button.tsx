"use client";

import { useRef, useEffect, useState } from "react";

interface AnimatedButtonProps {
  children: React.ReactNode;
  variant?: "primary" | "secondary";
  href: string;
  external?: boolean;
}

export function AnimatedButton({ children, variant = "primary", href, external }: AnimatedButtonProps) {
  const btnRef = useRef<HTMLAnchorElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hovering, setHovering] = useState(false);
  const [clicking, setClicking] = useState(false);
  const mousePos = useRef({ x: 0, y: 0 });
  const particles = useRef<Array<{
    x: number; y: number; vx: number; vy: number;
    radius: number; opacity: number; life: number; maxLife: number;
  }>>([]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const btn = btnRef.current;
    if (!canvas || !btn) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animFrame: number;

    const resize = () => {
      const rect = btn.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = rect.width + "px";
      canvas.style.height = rect.height + "px";
      ctx.scale(dpr, dpr);
    };

    const isPrimary = variant === "primary";
    const particleColor = isPrimary
      ? { r: 255, g: 107, b: 44 }   // orange
      : { r: 156, g: 163, b: 175 }; // gray

    const glowColor = isPrimary
      ? "rgba(255, 107, 44, 0.08)"
      : "rgba(156, 163, 175, 0.06)";

    const draw = () => {
      const rect = btn.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;
      ctx.clearRect(0, 0, w, h);

      // Hover glow that follows mouse
      if (hovering) {
        const mx = mousePos.current.x;
        const my = mousePos.current.y;

        const gradient = ctx.createRadialGradient(mx, my, 0, mx, my, 80);
        gradient.addColorStop(0, isPrimary ? "rgba(255, 107, 44, 0.15)" : "rgba(99, 102, 241, 0.08)");
        gradient.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, w, h);

        // Shimmer line across the button following mouse X
        const shimmerWidth = 60;
        const shimmerGrad = ctx.createLinearGradient(mx - shimmerWidth, 0, mx + shimmerWidth, 0);
        shimmerGrad.addColorStop(0, "rgba(255, 255, 255, 0)");
        shimmerGrad.addColorStop(0.5, isPrimary ? "rgba(255, 255, 255, 0.08)" : "rgba(255, 255, 255, 0.04)");
        shimmerGrad.addColorStop(1, "rgba(255, 255, 255, 0)");
        ctx.fillStyle = shimmerGrad;
        ctx.fillRect(0, 0, w, h);

        // Border glow near mouse
        const borderGlow = ctx.createRadialGradient(mx, my, 0, mx, my, 50);
        borderGlow.addColorStop(0, isPrimary ? "rgba(255, 107, 44, 0.3)" : "rgba(99, 102, 241, 0.15)");
        borderGlow.addColorStop(1, "rgba(0, 0, 0, 0)");

        // Top edge
        if (my < 15) {
          ctx.fillStyle = borderGlow;
          ctx.fillRect(0, 0, w, 2);
        }
        // Bottom edge
        if (my > h - 15) {
          ctx.fillStyle = borderGlow;
          ctx.fillRect(0, h - 2, w, 2);
        }
      }

      // Draw and update particles
      for (let i = particles.current.length - 1; i >= 0; i--) {
        const p = particles.current[i];
        p.x += p.vx;
        p.y += p.vy;
        p.vy -= 0.02; // slight upward drift
        p.life--;
        p.opacity = (p.life / p.maxLife) * 0.6;

        if (p.life <= 0) {
          particles.current.splice(i, 1);
          continue;
        }

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${particleColor.r}, ${particleColor.g}, ${particleColor.b}, ${p.opacity})`;
        ctx.fill();
      }

      animFrame = requestAnimationFrame(draw);
    };

    resize();
    draw();

    window.addEventListener("resize", resize);

    return () => {
      cancelAnimationFrame(animFrame);
      window.removeEventListener("resize", resize);
    };
  }, [hovering, variant]);

  const spawnClickParticles = () => {
    const mx = mousePos.current.x;
    const my = mousePos.current.y;
    for (let i = 0; i < 12; i++) {
      const angle = (Math.PI * 2 * i) / 12 + Math.random() * 0.3;
      const speed = 1.5 + Math.random() * 2;
      particles.current.push({
        x: mx,
        y: my,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        radius: 1.5 + Math.random() * 1.5,
        opacity: 0.6,
        life: 20 + Math.random() * 15,
        maxLife: 35,
      });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = btnRef.current?.getBoundingClientRect();
    if (!rect) return;
    mousePos.current.x = e.clientX - rect.left;
    mousePos.current.y = e.clientY - rect.top;
  };

  const baseClasses = variant === "primary"
    ? "relative inline-flex items-center gap-2.5 bg-gray-900 text-white px-7 py-3.5 rounded-xl text-sm font-semibold transition-all duration-200 overflow-hidden shadow-xl shadow-gray-900/10"
    : "relative inline-flex items-center gap-2 bg-white text-gray-600 px-7 py-3.5 rounded-xl text-sm font-semibold border border-gray-200 transition-all duration-200 overflow-hidden";

  const hoverClasses = variant === "primary"
    ? "hover:shadow-2xl hover:shadow-[#FF6B2C]/15"
    : "hover:border-gray-300 hover:shadow-lg hover:shadow-gray-200/50";

  const clickClasses = clicking
    ? "scale-[0.97]"
    : "scale-100";

  const linkProps = external
    ? { target: "_blank" as const, rel: "noopener noreferrer" }
    : {};

  return (
    <a
      ref={btnRef}
      href={href}
      className={`${baseClasses} ${hoverClasses} ${clickClasses}`}
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => { setHovering(false); setClicking(false); }}
      onMouseMove={handleMouseMove}
      onMouseDown={() => { setClicking(true); spawnClickParticles(); }}
      onMouseUp={() => setClicking(false)}
      {...linkProps}
    >
      <canvas
        ref={canvasRef}
        className="absolute inset-0 pointer-events-none"
        style={{ zIndex: 1 }}
      />
      <span className="relative z-10 flex items-center gap-2.5">
        {children}
      </span>
    </a>
  );
}
