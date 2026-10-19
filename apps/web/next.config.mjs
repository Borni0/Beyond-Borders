/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@beyond-borders/shared-types"],
  typedRoutes: false,
};

export default nextConfig;