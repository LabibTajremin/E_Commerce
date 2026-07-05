import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ApiClient } from "@/application/interfaces/ApiClient";
import { useHealthCheck } from "@/application/use-cases/useHealthCheck";

function fakeClient(response: unknown, shouldFail = false): ApiClient {
  return {
    get: async () => {
      if (shouldFail) throw new Error("boom");
      return response as never;
    },
    post: async () => response as never,
  };
}

describe("useHealthCheck", () => {
  it("returns ok when the API reports healthy", async () => {
    const { result } = renderHook(() => useHealthCheck(fakeClient({ status: "ok" })));
    await waitFor(() => expect(result.current).toBe("ok"));
  });

  it("returns error when the request fails", async () => {
    const { result } = renderHook(() => useHealthCheck(fakeClient(null, true)));
    await waitFor(() => expect(result.current).toBe("error"));
  });
});
