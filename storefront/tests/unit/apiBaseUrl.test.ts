import { afterEach, describe, expect, it, vi } from "vitest";

import { resolveApiBaseUrl } from "@/infrastructure/api/apiBaseUrl";

function setHostname(hostname: string) {
  vi.stubGlobal("location", { ...window.location, hostname });
}

describe("resolveApiBaseUrl", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses an explicit host argument over window.location when given (SSR path)", () => {
    expect(resolveApiBaseUrl("acme.localhost")).toBe("http://acme.localhost:8000");
  });

  it("falls back to window.location.hostname when no host argument is given", () => {
    setHostname("acme.localhost");
    expect(resolveApiBaseUrl()).toBe("http://acme.localhost:8000");
  });

  it("returns the configured API URL unchanged with no tenant subdomain", () => {
    expect(resolveApiBaseUrl("localhost")).toBe("http://localhost:8000");
  });

  it("splices the tenant label through even when the API lives on an unrelated domain (production)", () => {
    expect(resolveApiBaseUrl("acme.yourplatform.com")).toBe("http://acme.localhost:8000");
  });

  it("returns the API URL unchanged in single-tenant mode, even with a tenant-shaped host", async () => {
    vi.resetModules();
    vi.doMock("@/infrastructure/config/env", () => ({
      env: {
        NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000",
        NEXT_PUBLIC_SINGLE_TENANT_MODE: true,
      },
    }));

    const { resolveApiBaseUrl: resolveInSingleTenantMode } = await import(
      "@/infrastructure/api/apiBaseUrl"
    );

    expect(resolveInSingleTenantMode("acme.yourplatform.com")).toBe("http://localhost:8000");

    vi.doUnmock("@/infrastructure/config/env");
    vi.resetModules();
  });
});
