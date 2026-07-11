import { env } from "@/infrastructure/config/env";

/**
 * The backend resolves the tenant on every non-exempt request (including
 * admin login) from the Host header's subdomain — there is no tenant
 * fallback. This dashboard is always deployed such that the tenant is the
 * leftmost label of its own hostname (acme.localhost:3000 in dev,
 * acme.admin.yourplatform.com in production), regardless of what domain
 * the API itself lives on — so that label is spliced onto the *configured*
 * API host to build the per-tenant API origin.
 *
 * This deliberately does not require the dashboard's and API's hostnames to
 * share a suffix: production topologies commonly put the API on its own
 * wildcarded domain (e.g. *.api.yourplatform.com) that isn't a suffix of
 * the dashboard's own domain, and a naive suffix check would silently fail
 * to thread the tenant through at all in that case.
 */
export function resolveApiBaseUrl(host?: string): string {
  const apiUrl = new URL(env.NEXT_PUBLIC_API_BASE_URL);
  const pageHost = host ?? (typeof window !== "undefined" ? window.location.hostname : null);

  if (!pageHost || pageHost === apiUrl.hostname) {
    return env.NEXT_PUBLIC_API_BASE_URL;
  }

  const subdomain = pageHost.split(".")[0];
  apiUrl.hostname = `${subdomain}.${apiUrl.hostname}`;
  return apiUrl.origin;
}
