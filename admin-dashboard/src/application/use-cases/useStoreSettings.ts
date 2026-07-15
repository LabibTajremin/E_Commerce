"use client";

import type { ApiClient } from "@/application/interfaces/ApiClient";
import { useAsync } from "@/application/use-cases/useAsync";
import { resolveApiBaseUrl } from "@/infrastructure/api/apiBaseUrl";
import { tokenStore } from "@/infrastructure/api/tokenStore";
import type { BrandingInput, StoreSettings, Theme } from "@/domain/types";

export function useStoreSettings(client: ApiClient) {
  return useAsync<StoreSettings>(
    () => client.get<StoreSettings>("/api/v1/admin/store-settings"),
    [client],
  );
}

export function useThemes(client: ApiClient) {
  return useAsync<Theme[]>(() => client.get<Theme[]>("/api/v1/admin/themes"), [client]);
}

export async function updateBranding(
  client: ApiClient,
  input: BrandingInput,
): Promise<StoreSettings> {
  return client.patch<StoreSettings>("/api/v1/admin/store-settings", input);
}

export async function selectTheme(client: ApiClient, themeId: string): Promise<StoreSettings> {
  return client.post<StoreSettings>("/api/v1/admin/store-settings/theme", { theme_id: themeId });
}

export async function toggleSection(
  client: ApiClient,
  section: string,
  enabled: boolean,
): Promise<StoreSettings> {
  return client.patch<StoreSettings>(`/api/v1/admin/store-settings/sections/${section}`, {
    enabled,
  });
}

export async function uploadStoreImage(
  kind: "logo" | "favicon" | "banner",
  file: File,
): Promise<StoreSettings> {
  const formData = new FormData();
  formData.append("kind", kind);
  formData.append("file", file);

  const token = tokenStore.getAccessToken();
  const response = await fetch(`${resolveApiBaseUrl()}/api/v1/admin/store-settings/images`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: formData,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      (body && typeof body === "object" && "detail" in body && String(body.detail)) ||
        `Upload failed with status ${response.status}`,
    );
  }
  return response.json() as Promise<StoreSettings>;
}
