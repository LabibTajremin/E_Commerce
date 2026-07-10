import type { ApiClient } from "@/application/interfaces/ApiClient";

export function fakeApiClient(overrides: Partial<ApiClient> = {}): ApiClient {
  return {
    get: async () => {
      throw new Error("get not implemented in fake");
    },
    post: async () => {
      throw new Error("post not implemented in fake");
    },
    patch: async () => {
      throw new Error("patch not implemented in fake");
    },
    put: async () => {
      throw new Error("put not implemented in fake");
    },
    delete: async () => {
      throw new Error("delete not implemented in fake");
    },
    ...overrides,
  };
}
