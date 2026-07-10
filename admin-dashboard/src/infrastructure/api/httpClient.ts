import { ApiError, type ApiClient } from "@/application/interfaces/ApiClient";
import { resolveApiBaseUrl } from "@/infrastructure/api/apiBaseUrl";
import { tokenStore } from "@/infrastructure/api/tokenStore";

const AUTH_EXPIRED_EVENT = "auth:expired";

let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = tokenStore.getRefreshToken();
  if (!refreshToken) return false;

  const response = await fetch(`${resolveApiBaseUrl()}/api/v1/admin/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) return false;

  const tokens = (await response.json()) as { access_token: string; refresh_token: string };
  tokenStore.setTokens(tokens.access_token, tokens.refresh_token);
  return true;
}

function notifyAuthExpired(): void {
  tokenStore.clear();
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
  }
}

async function request<T>(path: string, init?: RequestInit, isRetry = false): Promise<T> {
  const accessToken = tokenStore.getAccessToken();
  const response = await fetch(`${resolveApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...init?.headers,
    },
  });

  if (response.status === 401 && !isRetry && tokenStore.getRefreshToken()) {
    refreshPromise ??= refreshAccessToken().finally(() => {
      refreshPromise = null;
    });
    const refreshed = await refreshPromise;
    if (refreshed) return request<T>(path, init, true);
    notifyAuthExpired();
    throw new ApiError(401, "Session expired");
  }

  if (response.status === 401) {
    notifyAuthExpired();
  }

  if (response.status === 204) {
    return undefined as T;
  }

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

export const httpClient: ApiClient = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body !== undefined ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: body !== undefined ? JSON.stringify(body) : undefined }),
  delete: (path: string) => request<void>(path, { method: "DELETE" }),
};

export { AUTH_EXPIRED_EVENT };
