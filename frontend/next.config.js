/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    // These rewrites run server-side (inside the Next.js server process), so
    // API_URL — the Docker-internal address — takes priority over the
    // browser-facing NEXT_PUBLIC_API_URL.
    const apiHost = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${apiHost}/api/v1/:path*`,
      },
      {
        source: '/health/:path*',
        destination: `${apiHost}/health/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
