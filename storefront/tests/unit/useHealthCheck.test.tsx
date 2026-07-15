import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useHealthCheck } from "@/application/use-cases/useHealthCheck";

import { fakeApiClient } from "./fakeApiClient";

describe("useHealthCheck", () => {
  it("returns ok when the API reports healthy", async () => {
    const client = fakeApiClient({ get: async () => ({ status: "ok" }) as never });
    const { result } = renderHook(() => useHealthCheck(client));
    await waitFor(() => expect(result.current).toBe("ok"));
  });

  it("returns error when the request fails", async () => {
    const client = fakeApiClient({
      get: async () => {
        throw new Error("boom");
      },
    });
    const { result } = renderHook(() => useHealthCheck(client));
    await waitFor(() => expect(result.current).toBe("error"));
  });
});
