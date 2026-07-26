import { createMDX } from 'fumadocs-mdx/next';

const withMDX = createMDX();

/** @type {import('next').NextConfig} */
const config = {
  reactStrictMode: true,
  trailingSlash: true,
  // This app lives inside the integration repo, which has its own package.json.
  // Pin the workspace root so Turbopack does not walk up and pick a sibling lockfile.
  turbopack: { root: process.cwd() },
};

export default withMDX(config);
