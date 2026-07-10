import { env } from "@/infrastructure/config/env";

/**
 * The backend resolves the tenant on every non-exempt request (including
 * admin login) from the Host header's subdomain — there is no tenant
 * fallback. NEXT_PUBLIC_API_BASE_URL is the platform's bare API origin
 * (e.g. http://localhost:8000); if this dashboard is itself being served
 * from a tenant subdomain (e.g. acme.localhost:3000, sharing the same base
 * domain as the API, differing only by port), that subdomain is spliced
 * onto the configured API host so requests land on the right tenant.
 */
export function resolveApiBaseUrl(): string {
  if (typeof window === "undefined") return env.NEXT_PUBLIC_API_BASE_URL;

  const apiUrl = new URL(env.NEXT_PUBLIC_API_BASE_URL);
  const pageHost = window.location.hostname;
  const apiHost = apiUrl.hostname;

  if (pageHost === apiHost || !pageHost.endsWith(`.${apiHost}`)) {
    return env.NEXT_PUBLIC_API_BASE_URL;
  }

  const subdomain = pageHost.slice(0, -(apiHost.length + 1));
  apiUrl.hostname = `${subdomain}.${apiHost}`;
  return apiUrl.origin;
}
