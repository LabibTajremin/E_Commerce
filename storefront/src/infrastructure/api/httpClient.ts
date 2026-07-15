import { ApiError, type ApiClient } from "@/application/interfaces/ApiClient";
import { resolveApiBaseUrl } from "@/infrastructure/api/apiBaseUrl";
import { tokenStore } from "@/infrastructure/api/tokenStore";
import { cartSession } from "@/infrastructure/api/cartSession";

const AUTH_EXPIRED_EVENT = "auth:expired";

function notifyAuthExpired(): void {
  tokenStore.clear();
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const accessToken = tokenStore.getAccessToken();
  const sessionId = cartSession.getOrCreate();

  const response = await fetch(`${resolveApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...(sessionId ? { "x-cart-session-id": sessionId } : {}),
      ...init?.headers,
    },
  });

  if (response.status === 401 && accessToken) {
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
  delete: <T = void>(path: string) => request<T>(path, { method: "DELETE" }),
};

export { AUTH_EXPIRED_EVENT };
