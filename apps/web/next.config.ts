import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Transpile the workspace-local brand package (ships .ts sources directly)
  transpilePackages: ["@intent-tracker/brand"],
};

export default nextConfig;
