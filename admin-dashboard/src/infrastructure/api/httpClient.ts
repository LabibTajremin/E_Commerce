import type { ApiClient } from "@/application/interfaces/ApiClient";
import { env } from "@/infrastructure/config/env";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${env.NEXT_PUBLIC_API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    throw new Error(`Request to ${path} failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const httpClient: ApiClient = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
};
