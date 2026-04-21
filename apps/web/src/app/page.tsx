"use client";

import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { AnimatedButton } from "@/components/animated-button";

const WebGLGrid = dynamic(() => import("@/components/webgl-grid").then(m => ({ default: m.WebGLGrid })), {
  ssr: false,
});

const logos = [
  "uniswap", "cow-protocol", "1inch", "across", "layerzero", "wormhole",
  "stargate", "dydx", "jupiter", "safe", "flashbots", "debridge",
];

export default function LandingPage() {
  return (
    <div className="fixed inset-0 bg-white overflow-hidden flex flex-col items-center justify-center">
      {/* WebGL interactive grid background */}
      <WebGLGrid />

      {/* Content overlay */}
      <div className="relative z-10 text-center max-w-3xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        >
          {/* Logo */}
          <div className="flex justify-center mb-10">
            <img
              src="/logo-light.svg"
              alt="Intent Tracker"
              className="w-16 h-16 rounded-2xl shadow-lg shadow-gray-200/50"
            />
          </div>

          {/* Headline */}
          <h1 className="text-[3.5rem] sm:text-[4.2rem] font-bold text-gray-900 tracking-tight leading-[1.08] mb-6">
            The intelligence layer for
            <br />
            <span className="text-[#FF6B2C]">intent-based</span> DeFi
          </h1>

          {/* Subtitle */}
          <p className="text-base sm:text-lg text-gray-400 max-w-xl mx-auto mb-10 leading-relaxed">
            Track every protocol, solver, and settlement layer across the intent ecosystem.
            From UniswapX to CoW Protocol — one dashboard for the future of DeFi execution.
          </p>

          {/* CTAs */}
          <div className="flex items-center justify-center gap-4">
            <AnimatedButton href="/overview" variant="primary">
              Access App
              <ArrowRight className="w-4 h-4" />
            </AnimatedButton>
            <AnimatedButton href="https://github.com" variant="secondary" external>
              View on GitHub
            </AnimatedButton>
          </div>
        </motion.div>

        {/* Protocol logos */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.6 }}
          className="flex items-center justify-center gap-5 mt-16"
        >
          {logos.map((slug) => (
            <img
              key={slug}
              src={`/logos/protocols/${slug}.png`}
              alt={slug}
              className="w-9 h-9 rounded-full grayscale opacity-50 hover:grayscale-0 hover:opacity-100 transition-all duration-300"
            />
          ))}
        </motion.div>
      </div>
    </div>
  );
}
