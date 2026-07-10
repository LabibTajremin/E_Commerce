/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Every tenant is served from its own subdomain (acme.localhost:3001) in
  // dev; without this the dev server's cross-origin request guard rejects
  // asset/RSC requests from anything but the bare host.
  allowedDevOrigins: ["*.localhost"],
};

module.exports = nextConfig;
