/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Determine target API URL (use host for external, or internal service name for container communication if needed)
    // Here we use localhost because port 3000 is accessed from client browser which sends request to localhost:8000
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
