"use client";

import { useEffect, useRef } from "react";

export function WebGLGrid() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouseRef = useRef({ x: -1000, y: -1000 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animFrame: number;
    let width = 0;
    let height = 0;

    const spacing = 40;
    const dotBaseRadius = 1;
    const dotHoverRadius = 3;
    const influenceRadius = 120;

    // Colors
    const baseColor = { r: 209, g: 213, b: 219 }; // gray-300
    const accentColor = { r: 255, g: 107, b: 44 }; // #FF6B2C

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = width + "px";
      canvas.style.height = height + "px";
      ctx.scale(dpr, dpr);
    };

    const onMouseMove = (e: MouseEvent) => {
      mouseRef.current.x = e.clientX;
      mouseRef.current.y = e.clientY;
    };

    const onMouseLeave = () => {
      mouseRef.current.x = -1000;
      mouseRef.current.y = -1000;
    };

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      const mx = mouseRef.current.x;
      const my = mouseRef.current.y;

      // Draw grid lines first (very subtle)
      ctx.strokeStyle = "rgba(229, 231, 235, 0.5)"; // gray-200 at 50%
      ctx.lineWidth = 0.5;

      const cols = Math.ceil(width / spacing) + 1;
      const rows = Math.ceil(height / spacing) + 1;
      const offsetX = (width % spacing) / 2;
      const offsetY = (height % spacing) / 2;

      // Vertical lines
      for (let i = 0; i <= cols; i++) {
        const x = offsetX + i * spacing;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }

      // Horizontal lines
      for (let j = 0; j <= rows; j++) {
        const y = offsetY + j * spacing;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Draw dots at intersections
      for (let i = 0; i <= cols; i++) {
        for (let j = 0; j <= rows; j++) {
          const x = offsetX + i * spacing;
          const y = offsetY + j * spacing;

          const dx = x - mx;
          const dy = y - my;
          const dist = Math.sqrt(dx * dx + dy * dy);

          // Influence factor (0 to 1, 1 = closest)
          const t = Math.max(0, 1 - dist / influenceRadius);
          const eased = t * t; // ease-in for smoother falloff

          // Interpolate radius
          const radius = dotBaseRadius + (dotHoverRadius - dotBaseRadius) * eased;

          // Interpolate color
          const r = Math.round(baseColor.r + (accentColor.r - baseColor.r) * eased);
          const g = Math.round(baseColor.g + (accentColor.g - baseColor.g) * eased);
          const b = Math.round(baseColor.b + (accentColor.b - baseColor.b) * eased);

          // Interpolate opacity
          const opacity = 0.3 + 0.7 * eased;

          ctx.beginPath();
          ctx.arc(x, y, radius, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${opacity})`;
          ctx.fill();

          // Subtle glow on highlighted dots
          if (eased > 0.3) {
            ctx.beginPath();
            ctx.arc(x, y, radius + 4, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${accentColor.r}, ${accentColor.g}, ${accentColor.b}, ${eased * 0.1})`;
            ctx.fill();
          }

          // Highlight grid lines near mouse
          if (eased > 0.1) {
            ctx.strokeStyle = `rgba(${accentColor.r}, ${accentColor.g}, ${accentColor.b}, ${eased * 0.15})`;
            ctx.lineWidth = 0.5 + eased;

            // Highlight vertical segment
            if (j < rows) {
              ctx.beginPath();
              ctx.moveTo(x, y);
              ctx.lineTo(x, y + spacing);
              ctx.stroke();
            }
            // Highlight horizontal segment
            if (i < cols) {
              ctx.beginPath();
              ctx.moveTo(x, y);
              ctx.lineTo(x + spacing, y);
              ctx.stroke();
            }
          }
        }
      }

      animFrame = requestAnimationFrame(draw);
    };

    resize();
    draw();

    window.addEventListener("resize", resize);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseleave", onMouseLeave);

    return () => {
      cancelAnimationFrame(animFrame);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseleave", onMouseLeave);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 pointer-events-auto"
      style={{ zIndex: 0 }}
    />
  );
}
