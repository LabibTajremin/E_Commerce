import { env } from "@/infrastructure/config/env";

/**
 * Same reasoning as the admin dashboard's identically-named helper: the
 * backend's TenantResolverMiddleware resolves the tenant from the Host
 * header on every storefront request, so a single static API origin would
 * only ever serve one hardcoded tenant. This splices the current page's
 * subdomain onto the configured API host (both sharing a base domain,
 * differing only by port in dev).
 */
export function resolveApiBaseUrl(host?: string): string {
  const apiUrl = new URL(env.NEXT_PUBLIC_API_BASE_URL);
  const pageHost = host ?? (typeof window !== "undefined" ? window.location.hostname : null);
  if (!pageHost) return env.NEXT_PUBLIC_API_BASE_URL;

  const apiHost = apiUrl.hostname;
  if (pageHost === apiHost || !pageHost.endsWith(`.${apiHost}`)) {
    return env.NEXT_PUBLIC_API_BASE_URL;
  }

  const subdomain = pageHost.slice(0, -(apiHost.length + 1));
  apiUrl.hostname = `${subdomain}.${apiHost}`;
  return apiUrl.origin;
}
