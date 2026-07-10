import { headers } from "next/headers";

import { ApiError } from "@/application/interfaces/ApiClient";
import { resolveApiBaseUrl } from "@/infrastructure/api/apiBaseUrl";

/**
 * Server Component fetch helper — resolves the tenant's API origin from the
 * *incoming* request's Host header (there's no window on the server), then
 * fetches with no caching so each tenant/request always sees fresh data.
 */
export async function serverFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headersList = await headers();
  const host = headersList.get("host")?.split(":")[0] ?? undefined;
  const baseUrl = resolveApiBaseUrl(host);

  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message =
      body && typeof body === "object" && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `Request to ${path} failed with status ${response.status}`;
    throw new ApiError(response.status, message);
  }

  return response.json() as Promise<T>;
}
