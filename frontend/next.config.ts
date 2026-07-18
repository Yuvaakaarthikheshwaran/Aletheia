import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable static export for Vercel / Hugging Face Spaces
  output: "standalone",

  // Environment variables exposed to the browser MUST be prefixed with NEXT_PUBLIC_
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "",
  },

  // Disable x-powered-by header for security
  poweredByHeader: false,

  // Enable React strict mode for development best practices
  reactStrictMode: true,
};

export default nextConfig;