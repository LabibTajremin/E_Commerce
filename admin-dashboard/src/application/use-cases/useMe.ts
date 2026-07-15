"use client";

import type { ApiClient } from "@/application/interfaces/ApiClient";
import { useAsync } from "@/application/use-cases/useAsync";
import type { CurrentAdmin } from "@/domain/types";

export function useMe(client: ApiClient) {
  return useAsync<CurrentAdmin>(() => client.get<CurrentAdmin>("/api/v1/admin/me"), [client]);
}
